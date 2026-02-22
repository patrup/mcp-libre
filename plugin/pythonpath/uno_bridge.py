"""
LibreOffice MCP Extension - UNO Bridge Module

This module provides a bridge between MCP operations and LibreOffice UNO API,
enabling direct manipulation of LibreOffice documents.
"""

import uno
import unohelper
from com.sun.star.beans import PropertyValue
from com.sun.star.text import XTextDocument
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.sheet import XSpreadsheetDocument
try:
    from com.sun.star.presentation import XPresentationDocument
except ImportError:
    XPresentationDocument = None
from com.sun.star.document import XDocumentEventListener
from com.sun.star.awt import XActionListener
from typing import Any, Optional, Dict, List, Tuple
import logging
import traceback
import uuid
import time as _time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UNOBridge:
    """Bridge between MCP operations and LibreOffice UNO API"""
    
    def __init__(self):
        """Initialize the UNO bridge"""
        try:
            self.ctx = uno.getComponentContext()
            self.smgr = self.ctx.ServiceManager
            self.desktop = self.smgr.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)
            self._toolkit = self.smgr.createInstanceWithContext(
                "com.sun.star.awt.Toolkit", self.ctx)
            logger.info("UNO Bridge initialized successfully")
            self._page_cache = {}  # (doc_url, object_name) -> page number
        except Exception as e:
            logger.error(f"Failed to initialize UNO Bridge: {e}")
            raise

    # ----------------------------------------------------------------
    # Page index — maps paragraphs/images/tables to page numbers
    # ----------------------------------------------------------------

    def _doc_key(self, doc) -> str:
        """Return a stable key for the document (URL or id)."""
        try:
            return doc.getURL() or str(id(doc))
        except Exception:
            return str(id(doc))

    def _resolve_page(self, doc, obj_name: str, anchor) -> Optional[int]:
        """Return cached page number, or resolve via ViewCursor and cache."""
        key = (self._doc_key(doc), obj_name)
        if key in self._page_cache:
            return self._page_cache[key]
        try:
            page = self._get_page_for_range(doc, anchor)
            self._page_cache[key] = page
            return page
        except Exception:
            return None

    def invalidate_page_cache(self, file_path: str = None):
        """Clear page cache (all or for a specific document)."""
        if file_path is None:
            self._page_cache.clear()
        else:
            self._page_cache = {
                k: v for k, v in self._page_cache.items()
                if k[0] != file_path}

    def _store_doc(self, doc):
        """Store document and invalidate page cache."""
        doc.store()
        self._page_cache = {
            k: v for k, v in self._page_cache.items()
            if k[0] != self._doc_key(doc)}

    def _annotate_pages(self, nodes, doc):
        """Add 'page' to each heading node using ViewCursor. Recursive."""
        controller = doc.getCurrentController()
        vc = controller.getViewCursor()
        text = doc.getText()
        for node in nodes:
            try:
                pi = node.get("para_index")
                if pi is not None:
                    node["page"] = self._get_page_for_paragraph(doc, pi)
            except Exception:
                pass
            if "children" in node:
                self._annotate_pages(node["children"], doc)

    def _get_page_for_range(self, doc, text_range) -> int:
        """Get the page number for a text range using ViewCursor."""
        controller = doc.getCurrentController()
        vc = controller.getViewCursor()
        vc.gotoRange(text_range, False)
        return vc.getPage()

    def _get_page_for_paragraph(self, doc, para_index: int) -> int:
        """Get the page number for a paragraph index."""
        text = doc.getText()
        cursor = text.createTextCursor()
        cursor.gotoStart(False)
        for _ in range(para_index):
            if not cursor.gotoNextParagraph(False):
                break
        return self._get_page_for_range(doc, cursor)

    def _anchor_para_index(self, doc, anchor) -> Optional[int]:
        """Return the paragraph index for a text anchor, or None.

        Handles images in the main text body as well as images inside
        text frames (cadres) by walking up to the frame's anchor.
        """
        main_text = doc.getText()

        # Determine the effective anchor range in the main text body.
        rng = anchor
        try:
            anchor_text = anchor.getText()
            if anchor_text != main_text:
                # The anchor lives inside a frame — find that frame's
                # own anchor in the main text.
                if hasattr(doc, 'getTextFrames'):
                    frames = doc.getTextFrames()
                    for fname in frames.getElementNames():
                        frame = frames.getByName(fname)
                        if frame.getText() == anchor_text:
                            rng = frame.getAnchor()
                            break
        except Exception:
            pass

        # Count paragraphs from the start of the main text to rng.
        try:
            tc = main_text.createTextCursorByRange(rng)
            idx = 0
            while tc.gotoPreviousParagraph(False):
                idx += 1
            return idx
        except Exception:
            return None

    def get_page_objects(self, page: int = None,
                         locator: str = None,
                         paragraph_index: int = None,
                         file_path: str = None) -> Dict[str, Any]:
        """Get all objects on a page. Accepts page number or locator to resolve."""
        doc = self._resolve_document(file_path)
        controller = doc.getCurrentController()
        vc = controller.getViewCursor()

        # Resolve page from locator or paragraph_index
        if page is None:
            if locator:
                resolved = self._resolve_locator(doc, locator)
                para_idx = resolved.get("para_index", 0)
            elif paragraph_index is not None:
                para_idx = paragraph_index
            else:
                # Use current view cursor page
                try:
                    page = vc.getPage()
                except Exception:
                    page = 1
                para_idx = None

            if page is None and para_idx is not None:
                try:
                    page = self._get_page_for_paragraph(doc, para_idx)
                except Exception as e:
                    logger.warning(f"get_page_objects: cannot resolve page "
                                   f"for paragraph {para_idx}: {e}")
                    return {"success": False,
                            "error": f"Cannot resolve page for paragraph "
                                     f"{para_idx}: {e}"}

        # Collect images on this page
        images = []
        if hasattr(doc, 'getGraphicObjects'):
            graphics = doc.getGraphicObjects()
            for name in graphics.getElementNames():
                try:
                    g = graphics.getByName(name)
                    anchor = g.getAnchor()
                    # Use the anchor range directly (not .getStart())
                    # to avoid failures with some anchor types.
                    vc.gotoRange(anchor, False)
                    if vc.getPage() == page:
                        size = g.getPropertyValue("Size")
                        images.append({
                            "name": name,
                            "width_mm": size.Width // 100,
                            "height_mm": size.Height // 100,
                            "title": g.getPropertyValue("Title"),
                            "paragraph_index": self._anchor_para_index(
                                doc, anchor),
                        })
                except Exception as e:
                    logger.debug(f"get_page_objects: skip image {name}: {e}")

        # Collect tables on this page
        tables = []
        if hasattr(doc, 'getTextTables'):
            text_tables = doc.getTextTables()
            for name in text_tables.getElementNames():
                try:
                    t = text_tables.getByName(name)
                    anchor = t.getAnchor()
                    vc.gotoRange(anchor, False)
                    if vc.getPage() == page:
                        tables.append({
                            "name": name,
                            "rows": t.getRows().getCount(),
                            "cols": t.getColumns().getCount(),
                        })
                except Exception as e:
                    logger.debug(f"get_page_objects: skip table {name}: {e}")

        # Collect text frames on this page
        frames = []
        if hasattr(doc, 'getTextFrames'):
            text_frames = doc.getTextFrames()
            # Find which images belong to which frame using UNO ==
            frame_images = {}
            for img in images:
                iname = img["name"]
                try:
                    g = doc.getGraphicObjects().getByName(iname)
                    anchor_text = g.getAnchor().getText()
                    for fname in text_frames.getElementNames():
                        fr = text_frames.getByName(fname)
                        if fr.getText() == anchor_text:
                            frame_images.setdefault(
                                fname, []).append(iname)
                            break
                except Exception:
                    pass
            for fname in text_frames.getElementNames():
                try:
                    fr = text_frames.getByName(fname)
                    anchor = fr.getAnchor()
                    vc.gotoRange(anchor, False)
                    if vc.getPage() == page:
                        size = fr.getPropertyValue("Size")
                        entry = {
                            "name": fname,
                            "width_mm": size.Width // 100,
                            "height_mm": size.Height // 100,
                            "paragraph_index": self._anchor_para_index(
                                doc, anchor),
                        }
                        if fname in frame_images:
                            entry["images"] = frame_images[fname]
                        frames.append(entry)
                except Exception as e:
                    logger.debug(
                        f"get_page_objects: skip frame {fname}: {e}")

        return {
            "success": True,
            "page": page,
            "images": images,
            "tables": tables,
            "frames": frames,
        }
    
    def create_document(self, doc_type: str = "writer") -> Any:
        """
        Create new document using UNO API
        
        Args:
            doc_type: Type of document ('writer', 'calc', 'impress', 'draw')
            
        Returns:
            Document object
        """
        try:
            url_map = {
                "writer": "private:factory/swriter",
                "calc": "private:factory/scalc", 
                "impress": "private:factory/simpress",
                "draw": "private:factory/sdraw"
            }
            
            url = url_map.get(doc_type, "private:factory/swriter")
            doc = self.desktop.loadComponentFromURL(url, "_blank", 0, ())
            logger.info(f"Created new {doc_type} document")
            return doc
            
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise
    
    def get_active_document(self) -> Optional[Any]:
        """Get currently active document"""
        try:
            doc = self.desktop.getCurrentComponent()
            if doc:
                logger.info("Retrieved active document")
            return doc
        except Exception as e:
            logger.error(f"Failed to get active document: {e}")
            return None
    
    # ----------------------------------------------------------------
    # Document resolution
    # ----------------------------------------------------------------

    def _find_open_document(self, file_url: str) -> Optional[Any]:
        """Find an already-open document by its URL (normalized comparison)."""
        try:
            components = self.desktop.getComponents()
            if components is None:
                return None

            # Normalize for comparison (lowercase on Windows, decode %xx)
            import urllib.parse
            norm = urllib.parse.unquote(file_url).lower().rstrip('/')

            enum = components.createEnumeration()
            while enum.hasMoreElements():
                doc = enum.nextElement()
                if not hasattr(doc, 'getURL'):
                    continue
                doc_url = urllib.parse.unquote(doc.getURL()).lower().rstrip('/')
                if doc_url == norm:
                    return doc
            return None
        except Exception:
            return None

    def open_document(self, file_path: str,
                      force: bool = False) -> Dict[str, Any]:
        """Open a document by file path, or return it if already open.

        Duplicate detection:
        - Exact URL match → reuse the existing document (already_open=True)
        - Same filename, different path → open normally but include a warning
        - force=True → always open a new frame (_blank)
        """
        try:
            file_url = uno.systemPathToFileUrl(file_path)

            # Exact URL match → reuse existing document
            existing = self._find_open_document(file_url)
            if existing is not None:
                return {"success": True, "doc": existing,
                        "url": file_url, "already_open": True}

            # Same filename at different path → informational warning
            import os
            same_name_url = None
            target_name = os.path.basename(file_path).lower()
            try:
                components = self.desktop.getComponents()
                if components:
                    enum = components.createEnumeration()
                    while enum.hasMoreElements():
                        doc = enum.nextElement()
                        if hasattr(doc, 'getURL'):
                            import urllib.parse
                            doc_name = os.path.basename(
                                urllib.parse.unquote(doc.getURL())).lower()
                            if doc_name == target_name:
                                same_name_url = doc.getURL()
                                break
            except Exception:
                pass

            props = (
                PropertyValue("Hidden", 0, False, 0),
                PropertyValue("ReadOnly", 0, False, 0),
            )
            target = "_blank" if force else "_default"
            doc = self.desktop.loadComponentFromURL(file_url, target, 0, props)
            if doc is None:
                return {"success": False,
                        "error": f"Failed to load document: {file_path}"}

            logger.info(f"Opened document: {file_path}")
            result = {"success": True, "doc": doc,
                      "url": file_url, "already_open": False}
            if same_name_url:
                result["warning"] = (
                    f"Another '{target_name}' is already open "
                    f"from a different path: {same_name_url}")
            return result
        except Exception as e:
            logger.error(f"Failed to open document: {e}")
            return {"success": False, "error": str(e)}

    def close_document(self, file_path: str) -> Dict[str, Any]:
        """Close a document by file path. Does not save."""
        try:
            file_url = uno.systemPathToFileUrl(file_path)
            doc = self._find_open_document(file_url)
            if doc is None:
                return {"success": True, "message": "Document was not open"}
            doc.setModified(False)  # avoid save prompt
            doc.close(True)
            logger.info(f"Closed document: {file_path}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to close document: {e}")
            return {"success": False, "error": str(e)}

    def _resolve_document(self, file_path: str = None) -> Any:
        """Resolve a document: open by path or use active document."""
        if file_path:
            result = self.open_document(file_path)
            if not result["success"]:
                raise RuntimeError(result["error"])
            return result["doc"]
        doc = self.get_active_document()
        if doc is None:
            raise RuntimeError("No active document and no file path provided")
        return doc

    # ----------------------------------------------------------------
    # Locator resolution
    # ----------------------------------------------------------------

    def _resolve_locator(self, doc, locator: str) -> Dict[str, Any]:
        """Parse 'type:value' locator and resolve to document position.

        Writer locators:
          bookmark:_mcp_abc123   -> para_index via bookmarks
          paragraph:42           -> direct index
          page:3                 -> first paragraph of page 3 (XPageCursor)
          section:Introduction   -> first para_index of named section
          heading:2.1            -> hierarchical heading navigation

        Calc locators:
          cell:A1 / cell:Sheet1.A1
          range:A1:D10 / range:Sheet1.A1:D10
          sheet:Sheet1

        Impress locators:
          slide:3
        """
        loc_type, sep, loc_value = locator.partition(":")
        if not sep:
            raise ValueError(f"Invalid locator format: '{locator}'. "
                             "Expected 'type:value'.")

        # -- Writer locators --
        if loc_type == "bookmark":
            result = self.resolve_bookmark(loc_value)
            if not result.get("success"):
                raise ValueError(result.get("error",
                                            f"Bookmark '{loc_value}' not found"))
            return {"para_index": result["para_index"]}

        if loc_type == "paragraph":
            return {"para_index": int(loc_value)}

        if loc_type == "page":
            page_num = int(loc_value)
            try:
                controller = doc.getCurrentController()
                vc = controller.getViewCursor()
                vc.jumpToPage(page_num)
                vc.jumpToStartOfPage()
                # Find which paragraph the view cursor is in
                anchor = vc.getStart()
                para_ranges = self._get_paragraph_ranges(doc)
                text_obj = doc.getText()
                para_idx = self._find_paragraph_for_range(
                    anchor, para_ranges, text_obj)
                return {"para_index": para_idx}
            except Exception as e:
                raise ValueError(
                    f"Cannot resolve page:{loc_value} — {e}")

        if loc_type == "section":
            if not hasattr(doc, 'getTextSections'):
                raise ValueError("Document does not support sections")
            sections = doc.getTextSections()
            if not sections.hasByName(loc_value):
                raise ValueError(f"Section '{loc_value}' not found")
            section = sections.getByName(loc_value)
            anchor = section.getAnchor()
            para_ranges = self._get_paragraph_ranges(doc)
            text_obj = doc.getText()
            para_idx = self._find_paragraph_for_range(
                anchor, para_ranges, text_obj)
            return {"para_index": para_idx, "section_name": loc_value}

        if loc_type == "heading":
            # Parse "2" or "2.1" -> list of 1-based indices per level
            parts = [int(p) for p in loc_value.split(".")]
            tree = self._build_heading_tree(doc)
            node = tree
            for part in parts:
                children = node.get("children", [])
                if part < 1 or part > len(children):
                    raise ValueError(
                        f"Heading index {part} out of range "
                        f"(1..{len(children)}) in '{locator}'")
                node = children[part - 1]
            return {"para_index": node["para_index"]}

        # -- Calc locators --
        if loc_type in ("cell", "range", "sheet"):
            return {"loc_type": loc_type, "loc_value": loc_value}

        # -- Impress locators --
        if loc_type == "slide":
            return {"slide_index": int(loc_value)}

        raise ValueError(f"Unknown locator type: '{loc_type}'")

    # ----------------------------------------------------------------
    # Heading bookmark management (stable IDs)
    # ----------------------------------------------------------------

    def _get_mcp_bookmark_map(self, doc) -> Dict[int, str]:
        """Get {para_index: bookmark_name} for all _mcp_ bookmarks."""
        result = {}
        try:
            if not hasattr(doc, 'getBookmarks'):
                return result
            bookmarks = doc.getBookmarks()
            names = bookmarks.getElementNames()
            if not names:
                return result
            para_ranges = self._get_paragraph_ranges(doc)
            text_obj = doc.getText()
            for name in names:
                if not name.startswith("_mcp_"):
                    continue
                bm = bookmarks.getByName(name)
                anchor = bm.getAnchor()
                para_idx = self._find_paragraph_for_range(
                    anchor, para_ranges, text_obj)
                result[para_idx] = name
        except Exception as e:
            logger.error(f"Failed to get MCP bookmark map: {e}")
        return result

    def _ensure_heading_bookmarks(self, doc) -> Dict[int, str]:
        """Ensure every heading has an _mcp_ bookmark. Returns {para_index: name}."""
        existing_map = self._get_mcp_bookmark_map(doc)
        text = doc.getText()
        enum = text.createEnumeration()
        para_index = 0
        bookmark_map = {}
        needs_bookmark = []

        while enum.hasMoreElements():
            element = enum.nextElement()
            if element.supportsService("com.sun.star.text.Paragraph"):
                outline_level = 0
                try:
                    outline_level = element.getPropertyValue("OutlineLevel")
                except Exception:
                    pass
                if outline_level > 0:
                    if para_index in existing_map:
                        bookmark_map[para_index] = existing_map[para_index]
                    else:
                        needs_bookmark.append(
                            (para_index, element.getStart()))
            para_index += 1

        for para_idx, start_range in needs_bookmark:
            bm_name = f"_mcp_{uuid.uuid4().hex[:8]}"
            bookmark = doc.createInstance("com.sun.star.text.Bookmark")
            bookmark.Name = bm_name
            cursor = text.createTextCursorByRange(start_range)
            text.insertTextContent(cursor, bookmark, False)
            bookmark_map[para_idx] = bm_name

        if needs_bookmark and doc.hasLocation():
            self._store_doc(doc)

        return bookmark_map

    def _find_nearest_heading_bookmark(self, para_index: int,
                                       bookmark_map: Dict[int, str]
                                       ) -> Optional[Dict[str, Any]]:
        """Find the nearest heading bookmark at or before para_index."""
        best_idx = -1
        for idx in bookmark_map:
            if idx <= para_index and idx > best_idx:
                best_idx = idx
        if best_idx >= 0:
            return {"bookmark": bookmark_map[best_idx],
                    "heading_para_index": best_idx}
        return None

    def resolve_bookmark(self, bookmark_name: str,
                         file_path: str = None) -> Dict[str, Any]:
        """Resolve a bookmark name to its current paragraph index."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getBookmarks'):
                return {"success": False,
                        "error": "Document doesn't support bookmarks"}

            bookmarks = doc.getBookmarks()
            if not bookmarks.hasByName(bookmark_name):
                return {"success": False,
                        "error": f"Bookmark '{bookmark_name}' not found"}

            bm = bookmarks.getByName(bookmark_name)
            anchor = bm.getAnchor()
            para_ranges = self._get_paragraph_ranges(doc)
            text_obj = doc.getText()
            para_idx = self._find_paragraph_for_range(
                anchor, para_ranges, text_obj)

            # Get heading info
            heading_info = {}
            enum = text_obj.createEnumeration()
            idx = 0
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == para_idx:
                    if element.supportsService("com.sun.star.text.Paragraph"):
                        try:
                            heading_info["text"] = element.getString()
                            heading_info["outline_level"] = \
                                element.getPropertyValue("OutlineLevel")
                        except Exception:
                            pass
                    break
                idx += 1

            return {
                "success": True,
                "bookmark": bookmark_name,
                "para_index": para_idx,
                **heading_info
            }
        except Exception as e:
            logger.error(f"Failed to resolve bookmark: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Tree navigation
    # ----------------------------------------------------------------

    def _build_heading_tree(self, doc) -> Dict[str, Any]:
        """Build heading tree from paragraph enumeration. Single pass."""
        text = doc.getText()
        enum = text.createEnumeration()

        root = {"level": 0, "text": "root", "para_index": -1,
                "children": [], "body_paragraphs": 0}
        stack = [root]
        para_index = 0

        while enum.hasMoreElements():
            element = enum.nextElement()
            is_para = element.supportsService("com.sun.star.text.Paragraph")
            is_table = element.supportsService("com.sun.star.text.TextTable")

            if is_para:
                outline_level = 0
                try:
                    outline_level = element.getPropertyValue("OutlineLevel")
                except Exception:
                    pass

                if outline_level > 0:
                    while len(stack) > 1 and stack[-1]["level"] >= outline_level:
                        stack.pop()
                    node = {
                        "level": outline_level,
                        "text": element.getString(),
                        "para_index": para_index,
                        "children": [],
                        "body_paragraphs": 0
                    }
                    stack[-1]["children"].append(node)
                    stack.append(node)
                else:
                    stack[-1]["body_paragraphs"] += 1
            elif is_table:
                stack[-1]["body_paragraphs"] += 1

            para_index += 1

        return root

    def _count_all_children(self, node: Dict) -> int:
        """Recursively count all descendants of a node."""
        count = len(node.get("children", []))
        for child in node.get("children", []):
            if "children" in child:
                count += self._count_all_children(child)
        return count + node.get("body_paragraphs", 0)

    def _find_node_by_para_index(self, node: Dict, para_index: int) -> Optional[Dict]:
        """Find a heading node in the tree by its paragraph index."""
        if node.get("para_index") == para_index:
            return node
        for child in node.get("children", []):
            found = self._find_node_by_para_index(child, para_index)
            if found is not None:
                return found
        return None

    def _get_body_preview(self, doc, heading_para_index: int,
                          max_chars: int = 100) -> str:
        """Get a preview of body text following a heading."""
        text = doc.getText()
        enum = text.createEnumeration()
        idx = 0
        preview_parts = []
        found_heading = (heading_para_index == -1)  # -1 means root (start)

        while enum.hasMoreElements():
            element = enum.nextElement()
            is_para = element.supportsService("com.sun.star.text.Paragraph")

            if idx == heading_para_index:
                found_heading = True
                idx += 1
                continue

            if found_heading and is_para:
                outline_level = 0
                try:
                    outline_level = element.getPropertyValue("OutlineLevel")
                except Exception:
                    pass
                if outline_level > 0:
                    break  # next heading reached
                para_text = element.getString().strip()
                if para_text:
                    preview_parts.append(para_text)
                    if sum(len(p) for p in preview_parts) >= max_chars:
                        break

            idx += 1

        full_preview = " ".join(preview_parts)
        if len(full_preview) > max_chars:
            full_preview = full_preview[:max_chars] + "..."
        return full_preview

    def _get_ai_summaries_map(self, doc) -> Dict[int, str]:
        """Build {para_index: summary} map from MCP-AI annotations."""
        summaries = {}
        try:
            fields_supplier = doc.getTextFields()
            enum = fields_supplier.createEnumeration()

            # Build paragraph ranges for position lookup
            para_ranges = self._get_paragraph_ranges(doc)

            while enum.hasMoreElements():
                field = enum.nextElement()
                if not field.supportsService(
                        "com.sun.star.text.textfield.Annotation"):
                    continue
                try:
                    author = field.getPropertyValue("Author")
                except Exception:
                    continue
                if author != "MCP-AI":
                    continue
                content = field.getPropertyValue("Content")
                anchor = field.getAnchor()

                # Find which paragraph this annotation is in
                para_idx = self._find_paragraph_for_range(
                    anchor, para_ranges, doc.getText())
                summaries[para_idx] = content
        except Exception as e:
            logger.error(f"Failed to get AI summaries: {e}")
        return summaries

    def _get_paragraph_ranges(self, doc) -> List[Any]:
        """Get list of paragraph elements for range comparison."""
        text = doc.getText()
        enum = text.createEnumeration()
        ranges = []
        while enum.hasMoreElements():
            element = enum.nextElement()
            ranges.append(element)
        return ranges

    def _find_paragraph_for_range(self, match_range, para_ranges: List,
                                  text_obj=None) -> int:
        """Find which paragraph index a text range belongs to."""
        try:
            if text_obj is None:
                text_obj = match_range.getText()
            match_start = match_range.getStart()

            for i, para in enumerate(para_ranges):
                try:
                    para_start = para.getStart()
                    para_end = para.getEnd()
                    cmp_start = text_obj.compareRegionStarts(
                        match_start, para_start)
                    cmp_end = text_obj.compareRegionStarts(
                        match_start, para_end)
                    if cmp_start <= 0 and cmp_end >= 0:
                        return i
                except Exception:
                    continue
        except Exception:
            pass
        return 0

    def _apply_content_strategy(self, node: Dict, doc,
                                ai_summaries: Dict[int, str],
                                strategy: str,
                                max_chars: int = 100):
        """Add content to a tree node based on strategy."""
        para_idx = node.get("para_index", -1)

        if strategy == "none":
            pass

        elif strategy == "ai_summary_first":
            if para_idx in ai_summaries:
                node["ai_summary"] = ai_summaries[para_idx]
            else:
                node["body_preview"] = self._get_body_preview(
                    doc, para_idx, max_chars)

        elif strategy == "first_lines":
            node["body_preview"] = self._get_body_preview(
                doc, para_idx, max_chars)
            if para_idx in ai_summaries:
                node["ai_summary"] = ai_summaries[para_idx]

        elif strategy == "full":
            node["body_text"] = self._get_full_body_text(doc, para_idx)

    def _get_full_body_text(self, doc, heading_para_index: int) -> str:
        """Get full body text following a heading until next heading."""
        text = doc.getText()
        enum = text.createEnumeration()
        idx = 0
        parts = []
        found_heading = (heading_para_index == -1)

        while enum.hasMoreElements():
            element = enum.nextElement()
            is_para = element.supportsService("com.sun.star.text.Paragraph")

            if idx == heading_para_index:
                found_heading = True
                idx += 1
                continue

            if found_heading and is_para:
                outline_level = 0
                try:
                    outline_level = element.getPropertyValue("OutlineLevel")
                except Exception:
                    pass
                if outline_level > 0:
                    break
                parts.append(element.getString())

            idx += 1

        return "\n".join(parts)

    def _serialize_tree_node(self, child: Dict, doc,
                             ai_summaries: Dict[int, str],
                             content_strategy: str,
                             depth: int,
                             current_depth: int = 1,
                             bookmark_map: Dict[int, str] = None) -> Dict[str, Any]:
        """Serialize a heading tree node to the given depth."""
        node = {
            "type": "heading",
            "level": child["level"],
            "text": child["text"],
            "para_index": child["para_index"],
            "bookmark": (bookmark_map or {}).get(child["para_index"]),
            "children_count": self._count_all_children(child),
            "body_paragraphs": child["body_paragraphs"]
        }
        self._apply_content_strategy(
            node, doc, ai_summaries, content_strategy)

        # Recurse into sub-headings if depth allows
        # depth=0 means unlimited, depth=1 means just this level, etc.
        if depth == 0 or current_depth < depth:
            if child.get("children"):
                node["children"] = [
                    self._serialize_tree_node(
                        sub, doc, ai_summaries, content_strategy,
                        depth, current_depth + 1, bookmark_map)
                    for sub in child["children"]
                ]
        return node

    def get_document_tree(self, content_strategy: str = "first_lines",
                          depth: int = 1,
                          file_path: str = None) -> Dict[str, Any]:
        """Get the document heading tree.

        Args:
            content_strategy: none, first_lines, ai_summary_first, full
            depth: How many levels to return (1=direct children only,
                   2=children+grandchildren, 0=unlimited)
            file_path: Optional file path
        """
        try:
            doc = self._resolve_document(file_path)
            if not self._is_writer(doc):
                return {"success": False,
                        "error": "Not a Writer document"}

            tree = self._build_heading_tree(doc)
            bookmark_map = self._ensure_heading_bookmarks(doc)
            ai_summaries = (self._get_ai_summaries_map(doc)
                            if content_strategy in ("ai_summary_first",
                                                    "first_lines")
                            else {})

            children = [
                self._serialize_tree_node(
                    child, doc, ai_summaries, content_strategy, depth,
                    bookmark_map=bookmark_map)
                for child in tree["children"]
            ]

            # Count total paragraphs
            text = doc.getText()
            enum = text.createEnumeration()
            total = 0
            while enum.hasMoreElements():
                enum.nextElement()
                total += 1

            # Add page numbers to headings (fast: ~20 VC moves)
            try:
                self._annotate_pages(children, doc)
            except Exception as pe:
                logger.debug(f"Could not annotate pages: {pe}")

            # Page count
            page_count = 0
            try:
                controller = doc.getCurrentController()
                page_count = controller.getViewCursor().getPage()
                # Jump to end to get actual last page
                vc = controller.getViewCursor()
                cursor = text.createTextCursor()
                cursor.gotoEnd(False)
                vc.gotoRange(cursor, False)
                page_count = vc.getPage()
            except Exception:
                pass

            return {
                "success": True,
                "content_strategy": content_strategy,
                "depth": depth,
                "children": children,
                "body_before_first_heading": tree["body_paragraphs"],
                "total_paragraphs": total,
                "page_count": page_count,
            }
        except Exception as e:
            logger.error(f"Failed to get document tree: {e}")
            return {"success": False, "error": str(e)}

    def get_heading_children(self, heading_para_index: int = None,
                             heading_bookmark: str = None,
                             locator: str = None,
                             content_strategy: str = "first_lines",
                             depth: int = 1,
                             file_path: str = None) -> Dict[str, Any]:
        """Get children of a heading node.

        Args:
            heading_para_index: Paragraph index of the parent heading
            heading_bookmark: Bookmark name (alternative to para_index)
            locator: Unified locator string (e.g. "bookmark:_mcp_x", "heading:2.1")
            content_strategy: none, first_lines, ai_summary_first, full
            depth: How many sub-levels to include (1=direct, 0=all)
            file_path: Optional file path
        """
        try:
            doc = self._resolve_document(file_path)
            if not self._is_writer(doc):
                return {"success": False,
                        "error": "Not a Writer document"}

            # Resolve locator first (takes priority)
            if locator is not None and heading_para_index is None:
                resolved = self._resolve_locator(doc, locator)
                heading_para_index = resolved.get("para_index")

            # Resolve bookmark to para_index if provided
            elif heading_bookmark is not None and heading_para_index is None:
                if not hasattr(doc, 'getBookmarks'):
                    return {"success": False,
                            "error": "Document doesn't support bookmarks"}
                bm_sup = doc.getBookmarks()
                if not bm_sup.hasByName(heading_bookmark):
                    return {"success": False,
                            "error": f"Bookmark '{heading_bookmark}' not found"}
                bm = bm_sup.getByName(heading_bookmark)
                anchor = bm.getAnchor()
                para_ranges = self._get_paragraph_ranges(doc)
                heading_para_index = self._find_paragraph_for_range(
                    anchor, para_ranges, doc.getText())

            if heading_para_index is None:
                return {"success": False,
                        "error": "Provide locator, heading_para_index, or heading_bookmark"}

            tree = self._build_heading_tree(doc)
            bookmark_map = self._ensure_heading_bookmarks(doc)
            target = self._find_node_by_para_index(tree, heading_para_index)
            if target is None:
                return {"success": False,
                        "error": f"Heading at paragraph {heading_para_index} not found"}

            ai_summaries = (self._get_ai_summaries_map(doc)
                            if content_strategy in ("ai_summary_first",
                                                    "first_lines")
                            else {})

            # Build children list: body paragraphs + sub-headings
            children = []

            # Get body paragraphs between heading and first sub-heading
            text = doc.getText()
            enum = text.createEnumeration()
            idx = 0
            found_heading = False
            parent_level = target["level"]

            while enum.hasMoreElements():
                element = enum.nextElement()
                is_para = element.supportsService("com.sun.star.text.Paragraph")

                if idx == heading_para_index:
                    found_heading = True
                    idx += 1
                    continue

                if found_heading and is_para:
                    outline_level = 0
                    try:
                        outline_level = element.getPropertyValue("OutlineLevel")
                    except Exception:
                        pass

                    if outline_level > 0 and outline_level <= parent_level:
                        break  # next sibling or parent heading

                    if outline_level > 0:
                        # This is a sub-heading; stop reading body,
                        # it will be added from tree children
                        break

                    # Body paragraph
                    para_text = element.getString()
                    preview = para_text[:100] + "..." if len(para_text) > 100 else para_text
                    if content_strategy == "full":
                        children.append({
                            "type": "body",
                            "para_index": idx,
                            "text": para_text
                        })
                    elif content_strategy != "none":
                        children.append({
                            "type": "body",
                            "para_index": idx,
                            "preview": preview
                        })
                    else:
                        children.append({
                            "type": "body",
                            "para_index": idx
                        })

                idx += 1

            # Add sub-headings from tree (with depth control + bookmarks)
            for child in target["children"]:
                node = self._serialize_tree_node(
                    child, doc, ai_summaries, content_strategy, depth,
                    bookmark_map=bookmark_map)
                children.append(node)

            return {
                "success": True,
                "parent": {
                    "level": target["level"],
                    "text": target["text"],
                    "para_index": target["para_index"],
                    "bookmark": bookmark_map.get(target["para_index"])
                },
                "content_strategy": content_strategy,
                "depth": depth,
                "children": children
            }
        except Exception as e:
            logger.error(f"Failed to get heading children: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Paragraph reading
    # ----------------------------------------------------------------

    def get_paragraph_count(self, file_path: str = None) -> Dict[str, Any]:
        """Count paragraphs in the document."""
        try:
            doc = self._resolve_document(file_path)
            text = doc.getText()
            enum = text.createEnumeration()
            count = 0
            while enum.hasMoreElements():
                para = enum.nextElement()
                if para.supportsService("com.sun.star.text.Paragraph"):
                    count += 1
            return {"success": True, "paragraph_count": count}
        except Exception as e:
            logger.error(f"Failed to get paragraph count: {e}")
            return {"success": False, "error": str(e)}

    def read_paragraphs(self, start_index: int = None, count: int = 10,
                        locator: str = None,
                        file_path: str = None) -> Dict[str, Any]:
        """Read a range of paragraphs by index or locator."""
        try:
            doc = self._resolve_document(file_path)

            # Resolve locator if provided
            if locator is not None and start_index is None:
                resolved = self._resolve_locator(doc, locator)
                start_index = resolved.get("para_index", 0)
            if start_index is None:
                start_index = 0
            text = doc.getText()
            enum = text.createEnumeration()

            # Get existing bookmark map for heading paragraphs
            bookmark_map = self._get_mcp_bookmark_map(doc)

            para_pages = []  # populated later if needed

            paragraphs = []
            current_index = 0
            end_index = start_index + count

            while enum.hasMoreElements() and current_index < end_index:
                element = enum.nextElement()

                if current_index >= start_index:
                    if element.supportsService("com.sun.star.text.Paragraph"):
                        style_name = ""
                        outline_level = 0
                        try:
                            style_name = element.getPropertyValue(
                                "ParaStyleName")
                            outline_level = element.getPropertyValue(
                                "OutlineLevel")
                        except Exception:
                            pass
                        para_entry = {
                            "index": current_index,
                            "text": element.getString(),
                            "style_name": style_name,
                            "outline_level": outline_level,
                            "is_table": False
                        }
                        if current_index < len(para_pages):
                            para_entry["page"] = para_pages[current_index]
                        if current_index in bookmark_map:
                            para_entry["bookmark"] = bookmark_map[current_index]
                        paragraphs.append(para_entry)
                    elif element.supportsService(
                            "com.sun.star.text.TextTable"):
                        info = self._extract_table_info(element)
                        paragraphs.append({
                            "index": current_index,
                            "text": f"[Table: {info.get('name', '?')}, "
                                    f"{info.get('rows', '?')}x"
                                    f"{info.get('cols', '?')}]",
                            "style_name": "",
                            "outline_level": 0,
                            "is_table": True,
                            "table_info": info
                        })

                current_index += 1

            return {
                "success": True,
                "paragraphs": paragraphs,
                "start_index": start_index,
                "count_returned": len(paragraphs),
                "has_more": enum.hasMoreElements()
            }
        except Exception as e:
            logger.error(f"Failed to read paragraphs: {e}")
            return {"success": False, "error": str(e)}

    def _extract_table_info(self, table) -> Dict[str, Any]:
        """Extract basic info from a TextTable element."""
        try:
            name = table.getName() if hasattr(table, 'getName') else "unnamed"
            rows = table.getRows().getCount()
            cols = table.getColumns().getCount()
            return {"name": name, "rows": rows, "cols": cols}
        except Exception:
            return {"name": "unknown", "rows": 0, "cols": 0}

    # ----------------------------------------------------------------
    # Search & replace
    # ----------------------------------------------------------------

    def search_document(self, pattern: str, regex: bool = False,
                        case_sensitive: bool = False,
                        max_results: int = 20,
                        context_paragraphs: int = 1,
                        file_path: str = None) -> Dict[str, Any]:
        """Search document using XSearchable with paragraph context."""
        try:
            doc = self._resolve_document(file_path)

            search_desc = doc.createSearchDescriptor()
            search_desc.SearchString = pattern
            search_desc.SearchRegularExpression = regex
            search_desc.SearchCaseSensitive = case_sensitive

            found = doc.findAll(search_desc)
            if found is None or found.getCount() == 0:
                return {"success": True, "matches": [],
                        "total_found": 0}

            total_found = found.getCount()
            para_ranges = self._get_paragraph_ranges(doc)
            text_obj = doc.getText()

            # Get bookmark map for nearest-heading lookup
            bookmark_map = self._get_mcp_bookmark_map(doc)

            # Build paragraph texts for context
            para_texts = []
            text_enum = text_obj.createEnumeration()
            while text_enum.hasMoreElements():
                el = text_enum.nextElement()
                if el.supportsService("com.sun.star.text.Paragraph"):
                    para_texts.append(el.getString())
                else:
                    para_texts.append("[Table]")

            results = []
            for i in range(min(total_found, max_results)):
                match_range = found.getByIndex(i)
                match_text = match_range.getString()
                match_para_idx = self._find_paragraph_for_range(
                    match_range, para_ranges, text_obj)

                ctx_start = max(0, match_para_idx - context_paragraphs)
                ctx_end = min(len(para_texts),
                              match_para_idx + context_paragraphs + 1)
                context = [
                    {"index": j, "text": para_texts[j]}
                    for j in range(ctx_start, ctx_end)
                ]
                match_entry = {
                    "match_index": i,
                    "match_text": match_text,
                    "paragraph_index": match_para_idx,
                    "context": context
                }
                # Add nearest heading bookmark
                nearest = self._find_nearest_heading_bookmark(
                    match_para_idx, bookmark_map)
                if nearest:
                    match_entry["nearest_heading"] = nearest
                results.append(match_entry)

            return {
                "success": True,
                "matches": results,
                "total_found": total_found,
                "returned": len(results)
            }
        except Exception as e:
            logger.error(f"Failed to search document: {e}")
            return {"success": False, "error": str(e)}

    def replace_in_document(self, search: str, replace: str,
                            regex: bool = False,
                            case_sensitive: bool = False,
                            file_path: str = None) -> Dict[str, Any]:
        """Find and replace using XReplaceable."""
        try:
            doc = self._resolve_document(file_path)

            replace_desc = doc.createReplaceDescriptor()
            replace_desc.SearchString = search
            replace_desc.ReplaceString = replace
            replace_desc.SearchRegularExpression = regex
            replace_desc.SearchCaseSensitive = case_sensitive

            count = doc.replaceAll(replace_desc)

            if count > 0 and doc.hasLocation():
                self._store_doc(doc)

            return {
                "success": True,
                "replacements_made": count,
                "search": search,
                "replace": replace
            }
        except Exception as e:
            logger.error(f"Failed to replace in document: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Editing
    # ----------------------------------------------------------------

    def _is_inside_index(self, paragraph) -> Optional[str]:
        """Check if a paragraph is inside a document index (ToC, etc.).

        Returns the index name if inside one, None otherwise.
        """
        try:
            section = paragraph.getPropertyValue("TextSection")
            if section is None:
                return None
            # Check if the section itself is an index, or its parent is
            si = section.supportsService
            if (si("com.sun.star.text.BaseIndex") or
                    si("com.sun.star.text.DocumentIndex") or
                    si("com.sun.star.text.ContentIndex")):
                return section.Name
            # Some index sections are nested — check parent
            if hasattr(section, 'ParentSection'):
                parent = section.ParentSection
                if parent is not None:
                    pi = parent.supportsService
                    if (pi("com.sun.star.text.BaseIndex") or
                            pi("com.sun.star.text.DocumentIndex") or
                            pi("com.sun.star.text.ContentIndex")):
                        return parent.Name
        except Exception:
            pass
        # Fallback: check if protected section (indexes are always protected)
        try:
            section = paragraph.getPropertyValue("TextSection")
            if section and section.IsProtected:
                return section.Name
        except Exception:
            pass
        return None

    def _resolve_style_name(self, doc, style_name: str) -> str:
        """Resolve a style name case-insensitively.

        Returns the exact name from the document's style pool,
        or the original name if no match is found.
        """
        try:
            families = doc.getStyleFamilies()
            para_styles = families.getByName("ParagraphStyles")
            # Exact match first
            if para_styles.hasByName(style_name):
                return style_name
            # Case-insensitive fallback
            lower = style_name.lower()
            for name in para_styles.getElementNames():
                if name.lower() == lower:
                    return name
        except Exception:
            pass
        return style_name

    def insert_at_paragraph(self, paragraph_index: int = None,
                            text: str = "",
                            position: str = "after",
                            locator: str = None,
                            style: str = None,
                            file_path: str = None) -> Dict[str, Any]:
        """Insert text before or after a specific paragraph.

        If style is provided, the new paragraph gets that style instead
        of inheriting from the adjacent paragraph.
        """
        try:
            doc = self._resolve_document(file_path)
            if style:
                style = self._resolve_style_name(doc, style)

            # Resolve locator if provided
            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}
            doc_text = doc.getText()
            enum = doc_text.createEnumeration()

            current_index = 0
            target_para = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if current_index == paragraph_index:
                    target_para = element
                    break
                current_index += 1

            if target_para is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found "
                                 f"(max: {current_index})"}

            # Guard: refuse to insert inside a document index (ToC, etc.)
            idx_name = self._is_inside_index(target_para)
            if idx_name:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} is inside "
                                 f"index '{idx_name}'. Use refresh_indexes() "
                                 f"instead of editing indexes directly."}

            cursor = doc_text.createTextCursorByRange(target_para)

            if position == "before":
                cursor.gotoStartOfParagraph(False)
                doc_text.insertString(cursor, text, False)
                doc_text.insertControlCharacter(
                    cursor, PARAGRAPH_BREAK, False)
                if style:
                    cursor.gotoPreviousParagraph(False)
                    cursor.gotoStartOfParagraph(False)
                    cursor.gotoEndOfParagraph(True)
                    cursor.setPropertyValue("ParaStyleName", style)
                    cursor.gotoNextParagraph(False)
            elif position == "after":
                cursor.gotoEndOfParagraph(False)
                doc_text.insertControlCharacter(
                    cursor, PARAGRAPH_BREAK, False)
                doc_text.insertString(cursor, text, False)
                if style:
                    cursor.gotoStartOfParagraph(False)
                    cursor.gotoEndOfParagraph(True)
                    cursor.setPropertyValue("ParaStyleName", style)
                    cursor.gotoEndOfParagraph(False)
            else:
                return {"success": False,
                        "error": f"Invalid position: {position}"}

            if doc.hasLocation():
                self._store_doc(doc)

            result = {
                "success": True,
                "message": f"Inserted text {position} paragraph "
                           f"{paragraph_index}",
                "text_length": len(text)
            }
            if style:
                result["style"] = style
            return result
        except Exception as e:
            logger.error(f"Failed to insert at paragraph: {e}")
            return {"success": False, "error": str(e)}

    def insert_paragraphs_batch(self, paragraphs: list,
                                paragraph_index: int = None,
                                position: str = "after",
                                locator: str = None,
                                file_path: str = None) -> Dict[str, Any]:
        """Insert multiple paragraphs in a single UNO transaction.

        Each item in paragraphs is {text: str, style?: str}.
        All paragraphs are inserted sequentially after (or before) the
        target, in one call — no index drift between inserts.
        """
        try:
            doc = self._resolve_document(file_path)

            # Pre-resolve all style names (case-insensitive)
            for item in paragraphs or []:
                if item.get("style"):
                    item["style"] = self._resolve_style_name(
                        doc, item["style"])

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}
            if not paragraphs:
                return {"success": False, "error": "Empty paragraphs list"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()

            current_index = 0
            target_para = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if current_index == paragraph_index:
                    target_para = element
                    break
                current_index += 1

            if target_para is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            # Guard: refuse to insert inside a document index (ToC, etc.)
            idx_name = self._is_inside_index(target_para)
            if idx_name:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} is inside "
                                 f"index '{idx_name}'. Use refresh_indexes() "
                                 f"instead of editing indexes directly."}

            cursor = doc_text.createTextCursorByRange(target_para)

            if position == "before":
                cursor.gotoStartOfParagraph(False)
                for item in paragraphs:
                    txt = item.get("text", "")
                    sty = item.get("style")
                    doc_text.insertString(cursor, txt, False)
                    doc_text.insertControlCharacter(
                        cursor, PARAGRAPH_BREAK, False)
                    if sty:
                        cursor.gotoPreviousParagraph(False)
                        cursor.gotoStartOfParagraph(False)
                        cursor.gotoEndOfParagraph(True)  # select whole para
                        cursor.setPropertyValue("ParaStyleName", sty)
                        cursor.gotoNextParagraph(False)
            elif position == "after":
                cursor.gotoEndOfParagraph(False)
                for item in paragraphs:
                    txt = item.get("text", "")
                    sty = item.get("style")
                    doc_text.insertControlCharacter(
                        cursor, PARAGRAPH_BREAK, False)
                    doc_text.insertString(cursor, txt, False)
                    if sty:
                        cursor.gotoStartOfParagraph(False)
                        cursor.gotoEndOfParagraph(True)  # select whole para
                        cursor.setPropertyValue("ParaStyleName", sty)
                        cursor.gotoEndOfParagraph(False)
            else:
                return {"success": False,
                        "error": f"Invalid position: {position}"}

            if doc.hasLocation():
                self._store_doc(doc)

            return {
                "success": True,
                "message": f"Inserted {len(paragraphs)} paragraphs "
                           f"{position} paragraph {paragraph_index}",
                "count": len(paragraphs)
            }
        except Exception as e:
            logger.error(f"Failed to insert paragraphs batch: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # AI annotations
    # ----------------------------------------------------------------

    def add_ai_summary(self, para_index: int = None, summary: str = "",
                       locator: str = None,
                       file_path: str = None) -> Dict[str, Any]:
        """Add an MCP-AI annotation at a heading paragraph."""
        try:
            doc = self._resolve_document(file_path)

            # Resolve locator if provided
            if locator is not None and para_index is None:
                resolved = self._resolve_locator(doc, locator)
                para_index = resolved.get("para_index")
            if para_index is None:
                return {"success": False,
                        "error": "Provide locator or para_index"}
            doc_text = doc.getText()

            # Remove existing MCP-AI annotation at this paragraph first
            self._remove_ai_annotation_at(doc, para_index)

            # Find the target paragraph
            enum = doc_text.createEnumeration()
            idx = 0
            target = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == para_index:
                    target = element
                    break
                idx += 1

            if target is None:
                return {"success": False,
                        "error": f"Paragraph {para_index} not found"}

            # Create annotation
            annotation = doc.createInstance(
                "com.sun.star.text.textfield.Annotation")
            annotation.setPropertyValue("Author", "MCP-AI")
            annotation.setPropertyValue("Content", summary)

            cursor = doc_text.createTextCursorByRange(target.getStart())
            doc_text.insertTextContent(cursor, annotation, False)

            if doc.hasLocation():
                self._store_doc(doc)

            return {
                "success": True,
                "message": f"Added AI summary at paragraph {para_index}",
                "para_index": para_index,
                "summary_length": len(summary)
            }
        except Exception as e:
            logger.error(f"Failed to add AI summary: {e}")
            return {"success": False, "error": str(e)}

    def get_ai_summaries(self, file_path: str = None) -> Dict[str, Any]:
        """List all MCP-AI annotations in the document."""
        try:
            doc = self._resolve_document(file_path)
            summaries_map = self._get_ai_summaries_map(doc)

            summaries = [
                {"para_index": idx, "summary": text}
                for idx, text in sorted(summaries_map.items())
            ]
            return {
                "success": True,
                "summaries": summaries,
                "count": len(summaries)
            }
        except Exception as e:
            logger.error(f"Failed to get AI summaries: {e}")
            return {"success": False, "error": str(e)}

    def remove_ai_summary(self, para_index: int = None,
                          locator: str = None,
                          file_path: str = None) -> Dict[str, Any]:
        """Remove an MCP-AI annotation from a paragraph."""
        try:
            doc = self._resolve_document(file_path)

            # Resolve locator if provided
            if locator is not None and para_index is None:
                resolved = self._resolve_locator(doc, locator)
                para_index = resolved.get("para_index")
            if para_index is None:
                return {"success": False,
                        "error": "Provide locator or para_index"}
            removed = self._remove_ai_annotation_at(doc, para_index)

            if removed and doc.hasLocation():
                self._store_doc(doc)

            return {
                "success": True,
                "removed": removed,
                "para_index": para_index
            }
        except Exception as e:
            logger.error(f"Failed to remove AI summary: {e}")
            return {"success": False, "error": str(e)}

    def _remove_ai_annotation_at(self, doc, para_index: int) -> bool:
        """Remove MCP-AI annotation at a specific paragraph. Returns True if removed."""
        try:
            fields = doc.getTextFields()
            enum = fields.createEnumeration()
            para_ranges = self._get_paragraph_ranges(doc)
            text_obj = doc.getText()

            while enum.hasMoreElements():
                field = enum.nextElement()
                if not field.supportsService(
                        "com.sun.star.text.textfield.Annotation"):
                    continue
                try:
                    author = field.getPropertyValue("Author")
                except Exception:
                    continue
                if author != "MCP-AI":
                    continue
                anchor = field.getAnchor()
                idx = self._find_paragraph_for_range(
                    anchor, para_ranges, text_obj)
                if idx == para_index:
                    text_obj.removeTextContent(field)
                    return True
        except Exception as e:
            logger.error(f"Failed to remove AI annotation: {e}")
        return False

    # ----------------------------------------------------------------
    # Comments (human review workflow)
    # ----------------------------------------------------------------

    def list_comments(self, file_path: str = None) -> Dict[str, Any]:
        """List all comments (annotations) in the document."""
        try:
            doc = self._resolve_document(file_path)
            fields = doc.getTextFields()
            enum = fields.createEnumeration()
            para_ranges = self._get_paragraph_ranges(doc)
            text_obj = doc.getText()

            comments = []
            while enum.hasMoreElements():
                field = enum.nextElement()
                if not field.supportsService(
                        "com.sun.star.text.textfield.Annotation"):
                    continue
                try:
                    author = field.getPropertyValue("Author")
                except Exception:
                    author = ""
                # Skip MCP-AI summaries (handled separately)
                if author == "MCP-AI":
                    continue

                content = field.getPropertyValue("Content")
                name = ""
                parent_name = ""
                resolved = False
                try:
                    name = field.getPropertyValue("Name")
                except Exception:
                    pass
                try:
                    parent_name = field.getPropertyValue("ParentName")
                except Exception:
                    pass
                try:
                    resolved = field.getPropertyValue("Resolved")
                except Exception:
                    pass

                # Date
                date_str = ""
                try:
                    dt = field.getPropertyValue("DateTimeValue")
                    date_str = (f"{dt.Year:04d}-{dt.Month:02d}-{dt.Day:02d} "
                                f"{dt.Hours:02d}:{dt.Minutes:02d}")
                except Exception:
                    pass

                # Position
                anchor = field.getAnchor()
                para_idx = self._find_paragraph_for_range(
                    anchor, para_ranges, text_obj)
                anchor_preview = anchor.getString()[:80]

                entry = {
                    "author": author,
                    "content": content,
                    "date": date_str,
                    "resolved": resolved,
                    "paragraph_index": para_idx,
                    "anchor_preview": anchor_preview,
                }
                if name:
                    entry["name"] = name
                if parent_name:
                    entry["parent_name"] = parent_name
                    entry["is_reply"] = True
                else:
                    entry["is_reply"] = False
                comments.append(entry)

            return {"success": True, "comments": comments,
                    "count": len(comments)}
        except Exception as e:
            logger.error(f"Failed to list comments: {e}")
            return {"success": False, "error": str(e)}

    def add_comment(self, content: str, author: str = "AI Agent",
                    paragraph_index: int = None,
                    locator: str = None,
                    file_path: str = None) -> Dict[str, Any]:
        """Add a comment at a paragraph."""
        try:
            doc = self._resolve_document(file_path)

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()
            idx = 0
            target = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == paragraph_index:
                    target = element
                    break
                idx += 1

            if target is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            annotation = doc.createInstance(
                "com.sun.star.text.textfield.Annotation")
            annotation.setPropertyValue("Author", author)
            annotation.setPropertyValue("Content", content)

            cursor = doc_text.createTextCursorByRange(target.getStart())
            doc_text.insertTextContent(cursor, annotation, False)

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True,
                    "message": f"Comment added at paragraph {paragraph_index}",
                    "author": author}
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return {"success": False, "error": str(e)}

    def resolve_comment(self, comment_name: str,
                        resolution: str = "",
                        author: str = "AI Agent",
                        file_path: str = None) -> Dict[str, Any]:
        """Resolve a comment with an optional reason. Adds a reply then marks resolved."""
        try:
            doc = self._resolve_document(file_path)
            fields = doc.getTextFields()
            enum = fields.createEnumeration()
            target = None

            while enum.hasMoreElements():
                field = enum.nextElement()
                if not field.supportsService(
                        "com.sun.star.text.textfield.Annotation"):
                    continue
                try:
                    name = field.getPropertyValue("Name")
                except Exception:
                    continue
                if name == comment_name:
                    target = field
                    break

            if target is None:
                return {"success": False,
                        "error": f"Comment '{comment_name}' not found"}

            # Add a reply with the resolution reason if provided
            if resolution:
                reply = doc.createInstance(
                    "com.sun.star.text.textfield.Annotation")
                reply.setPropertyValue("Author", author)
                reply.setPropertyValue("Content", resolution)
                try:
                    reply.setPropertyValue("ParentName", comment_name)
                except Exception:
                    pass  # Older LO versions may not support ParentName

                anchor = target.getAnchor()
                cursor = doc.getText().createTextCursorByRange(anchor)
                doc.getText().insertTextContent(cursor, reply, False)

            # Mark the original comment as resolved
            try:
                target.setPropertyValue("Resolved", True)
            except Exception:
                pass  # Resolved property may not exist in older versions

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True,
                    "comment": comment_name,
                    "resolved": True,
                    "resolution": resolution}
        except Exception as e:
            logger.error(f"Failed to resolve comment: {e}")
            return {"success": False, "error": str(e)}

    def delete_comment(self, comment_name: str,
                       file_path: str = None) -> Dict[str, Any]:
        """Delete a comment by its name."""
        try:
            doc = self._resolve_document(file_path)
            fields = doc.getTextFields()
            enum = fields.createEnumeration()
            text_obj = doc.getText()
            deleted = 0

            # Collect all comments to delete (parent + replies)
            to_delete = []
            while enum.hasMoreElements():
                field = enum.nextElement()
                if not field.supportsService(
                        "com.sun.star.text.textfield.Annotation"):
                    continue
                try:
                    name = field.getPropertyValue("Name")
                    parent = field.getPropertyValue("ParentName")
                except Exception:
                    continue
                if name == comment_name or parent == comment_name:
                    to_delete.append(field)

            for field in to_delete:
                text_obj.removeTextContent(field)
                deleted += 1

            if deleted > 0 and doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "deleted": deleted,
                    "comment": comment_name}
        except Exception as e:
            logger.error(f"Failed to delete comment: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Document Protection
    # ----------------------------------------------------------------

    def _get_document_settings(self, doc):
        """Get the document settings object (try multiple approaches)."""
        # Try createInstance first
        try:
            return doc.createInstance(
                "com.sun.star.document.Settings")
        except Exception:
            pass
        # Fall back to direct property access on the document
        return doc

    def set_document_protection(self, enabled: bool,
                                file_path: str = None) -> Dict[str, Any]:
        """Lock or unlock the document for human editing.

        Uses ProtectForm — no password, just a boolean toggle.
        UI becomes read-only but UNO/MCP calls still work normally.
        """
        try:
            doc = self._resolve_document(file_path)
            settings = self._get_document_settings(doc)
            currently_protected = settings.getPropertyValue("ProtectForm")

            if enabled == currently_protected:
                return {"success": True,
                        "protected": currently_protected,
                        "message": "No change needed (already "
                                   f"{'protected' if currently_protected else 'unprotected'})"}

            settings.setPropertyValue("ProtectForm", enabled)
            settings.setPropertyValue("ProtectBookmarks", enabled)
            settings.setPropertyValue("ProtectFields", enabled)

            if enabled:
                return {"success": True, "protected": True,
                        "message": "Document locked (ProtectForm). "
                                   "UNO/MCP edits still work."}
            else:
                return {"success": True, "protected": False,
                        "message": "Document unlocked. Human can edit."}
        except Exception as e:
            logger.error(f"Failed to set document protection: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Track Changes
    # ----------------------------------------------------------------

    def set_track_changes(self, enabled: bool,
                          file_path: str = None) -> Dict[str, Any]:
        """Enable or disable change tracking."""
        try:
            doc = self._resolve_document(file_path)
            doc.setPropertyValue("RecordChanges", enabled)
            return {"success": True, "record_changes": enabled}
        except Exception as e:
            logger.error(f"Failed to set track changes: {e}")
            return {"success": False, "error": str(e)}

    def get_tracked_changes(self,
                            file_path: str = None) -> Dict[str, Any]:
        """List all tracked changes (redlines)."""
        try:
            doc = self._resolve_document(file_path)
            recording = doc.getPropertyValue("RecordChanges")

            if not hasattr(doc, 'getRedlines'):
                return {"success": False,
                        "error": "Document does not support redlines"}

            redlines = doc.getRedlines()
            enum = redlines.createEnumeration()
            changes = []
            while enum.hasMoreElements():
                redline = enum.nextElement()
                entry = {}
                for prop in ("RedlineType", "RedlineAuthor",
                             "RedlineComment", "RedlineIdentifier"):
                    try:
                        entry[prop] = redline.getPropertyValue(prop)
                    except Exception:
                        pass
                try:
                    dt = redline.getPropertyValue("RedlineDateTime")
                    entry["date"] = (f"{dt.Year:04d}-{dt.Month:02d}-"
                                     f"{dt.Day:02d} {dt.Hours:02d}:"
                                     f"{dt.Minutes:02d}")
                except Exception:
                    pass
                changes.append(entry)

            return {"success": True, "recording": recording,
                    "changes": changes, "count": len(changes)}
        except Exception as e:
            logger.error(f"Failed to get tracked changes: {e}")
            return {"success": False, "error": str(e)}

    def accept_all_changes(self,
                           file_path: str = None) -> Dict[str, Any]:
        """Accept all tracked changes."""
        try:
            doc = self._resolve_document(file_path)
            dispatcher = self.smgr.createInstanceWithContext(
                "com.sun.star.frame.DispatchHelper", self.ctx)
            frame = doc.getCurrentController().getFrame()
            dispatcher.executeDispatch(
                frame, ".uno:AcceptAllTrackedChanges", "", 0, ())
            if doc.hasLocation():
                self._store_doc(doc)
            return {"success": True, "message": "All changes accepted"}
        except Exception as e:
            logger.error(f"Failed to accept all changes: {e}")
            return {"success": False, "error": str(e)}

    def reject_all_changes(self,
                           file_path: str = None) -> Dict[str, Any]:
        """Reject all tracked changes."""
        try:
            doc = self._resolve_document(file_path)
            dispatcher = self.smgr.createInstanceWithContext(
                "com.sun.star.frame.DispatchHelper", self.ctx)
            frame = doc.getCurrentController().getFrame()
            dispatcher.executeDispatch(
                frame, ".uno:RejectAllTrackedChanges", "", 0, ())
            if doc.hasLocation():
                self._store_doc(doc)
            return {"success": True, "message": "All changes rejected"}
        except Exception as e:
            logger.error(f"Failed to reject all changes: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Styles
    # ----------------------------------------------------------------

    def list_styles(self, family: str = "ParagraphStyles",
                    file_path: str = None) -> Dict[str, Any]:
        """List available styles.

        Args:
            family: ParagraphStyles, CharacterStyles, PageStyles,
                    FrameStyles, NumberingStyles
        """
        try:
            doc = self._resolve_document(file_path)
            families = doc.getStyleFamilies()

            if not families.hasByName(family):
                available = list(families.getElementNames())
                return {"success": False,
                        "error": f"Unknown style family: {family}",
                        "available_families": available}

            style_family = families.getByName(family)
            styles = []
            for name in style_family.getElementNames():
                style = style_family.getByName(name)
                entry = {
                    "name": name,
                    "is_user_defined": style.isUserDefined(),
                    "is_in_use": style.isInUse(),
                }
                try:
                    entry["parent_style"] = style.getPropertyValue(
                        "ParentStyle")
                except Exception:
                    pass
                styles.append(entry)

            return {"success": True, "family": family,
                    "styles": styles, "count": len(styles)}
        except Exception as e:
            logger.error(f"Failed to list styles: {e}")
            return {"success": False, "error": str(e)}

    def get_style_info(self, style_name: str,
                       family: str = "ParagraphStyles",
                       file_path: str = None) -> Dict[str, Any]:
        """Get detailed properties of a style."""
        try:
            doc = self._resolve_document(file_path)
            families = doc.getStyleFamilies()
            style_family = families.getByName(family)

            if not style_family.hasByName(style_name):
                return {"success": False,
                        "error": f"Style '{style_name}' not found in {family}"}

            style = style_family.getByName(style_name)
            info = {
                "name": style_name,
                "family": family,
                "is_user_defined": style.isUserDefined(),
                "is_in_use": style.isInUse(),
            }

            # Common properties
            props_to_read = {
                "ParagraphStyles": [
                    "ParentStyle", "FollowStyle",
                    "CharFontName", "CharHeight", "CharWeight",
                    "ParaAdjust", "ParaTopMargin", "ParaBottomMargin",
                ],
                "CharacterStyles": [
                    "ParentStyle", "CharFontName", "CharHeight",
                    "CharWeight", "CharPosture", "CharColor",
                ],
            }

            for prop_name in props_to_read.get(family, []):
                try:
                    val = style.getPropertyValue(prop_name)
                    info[prop_name] = val
                except Exception:
                    pass

            return {"success": True, **info}
        except Exception as e:
            logger.error(f"Failed to get style info: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Writer Tables
    # ----------------------------------------------------------------

    def list_tables(self, file_path: str = None) -> Dict[str, Any]:
        """List all text tables in the document."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getTextTables'):
                return {"success": False,
                        "error": "Document does not support text tables"}

            tables_sup = doc.getTextTables()
            tables = []
            for name in tables_sup.getElementNames():
                table = tables_sup.getByName(name)
                rows = table.getRows().getCount()
                cols = table.getColumns().getCount()
                tables.append({
                    "name": name,
                    "rows": rows,
                    "cols": cols,
                })
            return {"success": True, "tables": tables,
                    "count": len(tables)}
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return {"success": False, "error": str(e)}

    def read_table(self, table_name: str,
                   file_path: str = None) -> Dict[str, Any]:
        """Read all cell contents from a Writer table."""
        try:
            doc = self._resolve_document(file_path)
            tables_sup = doc.getTextTables()

            if not tables_sup.hasByName(table_name):
                return {"success": False,
                        "error": f"Table '{table_name}' not found",
                        "available": list(tables_sup.getElementNames())}

            table = tables_sup.getByName(table_name)
            rows = table.getRows().getCount()
            cols = table.getColumns().getCount()
            cell_names = table.getCellNames()

            data = []
            for r in range(rows):
                row_data = []
                for c in range(cols):
                    # Cell naming: A1, B1, ... for row 1
                    col_letter = chr(ord('A') + c) if c < 26 else f"A{chr(ord('A') + c - 26)}"
                    cell_name = f"{col_letter}{r + 1}"
                    try:
                        cell = table.getCellByName(cell_name)
                        row_data.append(cell.getString())
                    except Exception:
                        row_data.append("")
                data.append(row_data)

            return {"success": True, "table_name": table_name,
                    "rows": rows, "cols": cols, "data": data}
        except Exception as e:
            logger.error(f"Failed to read table: {e}")
            return {"success": False, "error": str(e)}

    def write_table_cell(self, table_name: str, cell: str, value: str,
                         file_path: str = None) -> Dict[str, Any]:
        """Write to a cell in a Writer table (e.g. cell='B2')."""
        try:
            doc = self._resolve_document(file_path)
            tables_sup = doc.getTextTables()

            if not tables_sup.hasByName(table_name):
                return {"success": False,
                        "error": f"Table '{table_name}' not found"}

            table = tables_sup.getByName(table_name)
            cell_obj = table.getCellByName(cell)
            if cell_obj is None:
                return {"success": False,
                        "error": f"Cell '{cell}' not found in {table_name}"}

            # Try numeric first
            try:
                cell_obj.setValue(float(value))
            except (ValueError, TypeError):
                cell_obj.setString(value)

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "table": table_name,
                    "cell": cell, "value": value}
        except Exception as e:
            logger.error(f"Failed to write table cell: {e}")
            return {"success": False, "error": str(e)}

    def create_table(self, rows: int, cols: int,
                     paragraph_index: int = None,
                     locator: str = None,
                     file_path: str = None) -> Dict[str, Any]:
        """Create a new table at a position."""
        try:
            doc = self._resolve_document(file_path)

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()
            idx = 0
            target = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == paragraph_index:
                    target = element
                    break
                idx += 1

            if target is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            table = doc.createInstance("com.sun.star.text.TextTable")
            table.initialize(rows, cols)
            cursor = doc_text.createTextCursorByRange(target.getEnd())
            doc_text.insertTextContent(cursor, table, False)

            table_name = table.getName()

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "table_name": table_name,
                    "rows": rows, "cols": cols}
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Images
    # ----------------------------------------------------------------

    def list_images(self, file_path: str = None) -> Dict[str, Any]:
        """List all images/graphic objects in the document."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getGraphicObjects'):
                return {"success": False,
                        "error": "Document does not support graphic objects"}

            graphics = doc.getGraphicObjects()

            images = []
            for name in graphics.getElementNames():
                graphic = graphics.getByName(name)
                entry = {"name": name}
                try:
                    size = graphic.getPropertyValue("Size")
                    entry["width_mm"] = size.Width // 100
                    entry["height_mm"] = size.Height // 100
                except Exception:
                    try:
                        entry["width_mm"] = graphic.Width // 100
                        entry["height_mm"] = graphic.Height // 100
                    except Exception:
                        pass
                try:
                    entry["description"] = graphic.getPropertyValue(
                        "Description")
                    entry["title"] = graphic.getPropertyValue("Title")
                except Exception:
                    pass
                # Resolve anchor paragraph index and page
                try:
                    anchor = graphic.getAnchor()
                    entry["paragraph_index"] = self._anchor_para_index(
                        doc, anchor)
                    page = self._resolve_page(doc, name, anchor)
                    if page is not None:
                        entry["page"] = page
                except Exception:
                    pass
                images.append(entry)

            return {"success": True, "images": images,
                    "count": len(images)}
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return {"success": False, "error": str(e)}

    def get_image_info(self, image_name: str,
                       file_path: str = None) -> Dict[str, Any]:
        """Get detailed info about a specific image."""
        try:
            doc = self._resolve_document(file_path)
            graphics = doc.getGraphicObjects()

            if not graphics.hasByName(image_name):
                return {"success": False,
                        "error": f"Image '{image_name}' not found",
                        "available": list(graphics.getElementNames())}

            graphic = graphics.getByName(image_name)
            info = {"name": image_name, "success": True}

            for prop in ("GraphicURL", "Description", "Title"):
                try:
                    info[prop] = graphic.getPropertyValue(prop)
                except Exception:
                    pass

            # Enum properties — convert UNO enums to JSON-safe values
            anchor_names = ["AT_PARAGRAPH", "AS_CHARACTER",
                            "AT_PAGE", "AT_FRAME", "AT_CHARACTER"]
            for prop in ("AnchorType", "HoriOrient", "VertOrient"):
                try:
                    val = graphic.getPropertyValue(prop)
                    try:
                        str_val = val.value  # UNO enum → string
                    except AttributeError:
                        str_val = str(val)
                    info[prop] = str_val
                    # For AnchorType, also add the integer
                    if prop == "AnchorType" and str_val in anchor_names:
                        info["anchor_type_id"] = anchor_names.index(str_val)
                except Exception:
                    pass

            try:
                size = graphic.getPropertyValue("Size")
                info["width_mm"] = size.Width // 100
                info["height_mm"] = size.Height // 100
            except Exception:
                try:
                    info["width_mm"] = graphic.Width // 100
                    info["height_mm"] = graphic.Height // 100
                except Exception:
                    pass

            # Position offsets (used when orient=NONE)
            for prop, key in (("HoriOrientPosition", "hori_pos_mm"),
                              ("VertOrientPosition", "vert_pos_mm")):
                try:
                    info[key] = graphic.getPropertyValue(prop) // 100
                except Exception:
                    pass

            # Orientation relations
            for prop in ("HoriOrientRelation", "VertOrientRelation"):
                try:
                    info[prop] = int(graphic.getPropertyValue(prop))
                except Exception:
                    pass

            # Margins
            for prop, key in (("TopMargin", "top_margin_mm"),
                              ("BottomMargin", "bottom_margin_mm"),
                              ("LeftMargin", "left_margin_mm"),
                              ("RightMargin", "right_margin_mm")):
                try:
                    info[key] = graphic.getPropertyValue(prop) // 100
                except Exception:
                    pass

            # Wrap / Surround
            for prop in ("Surround", "TextWrapType"):
                try:
                    val = graphic.getPropertyValue(prop)
                    wrap_names = {0: "NONE", 1: "COLUMN", 2: "PARALLEL",
                                  3: "DYNAMIC", 4: "THROUGH"}
                    ival = int(val)
                    info["wrap"] = wrap_names.get(ival, str(ival))
                    info["wrap_id"] = ival
                    break
                except Exception:
                    pass

            # Crop
            try:
                crop = graphic.getPropertyValue("GraphicCrop")
                info["crop"] = {
                    "top_mm": crop.Top // 100,
                    "bottom_mm": crop.Bottom // 100,
                    "left_mm": crop.Left // 100,
                    "right_mm": crop.Right // 100,
                }
            except Exception:
                pass

            # Position in document — find anchor paragraph and page
            try:
                anchor = graphic.getAnchor()
                pidx = self._anchor_para_index(doc, anchor)
                if pidx is not None:
                    info["paragraph_index"] = pidx
                page = self._resolve_page(doc, image_name, anchor)
                if page is not None:
                    info["page"] = page
            except Exception as pe:
                logger.debug(f"Could not resolve image anchor: {pe}")

            return info
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return {"success": False, "error": str(e)}

    def set_image_properties(self, image_name: str,
                             width_mm: int = None,
                             height_mm: int = None,
                             title: str = None,
                             description: str = None,
                             anchor_type: int = None,
                             hori_orient: int = None,
                             vert_orient: int = None,
                             hori_orient_relation: int = None,
                             vert_orient_relation: int = None,
                             crop_top_mm: int = None,
                             crop_bottom_mm: int = None,
                             crop_left_mm: int = None,
                             crop_right_mm: int = None,
                             file_path: str = None) -> Dict[str, Any]:
        """Resize, reposition, crop, or update caption/alt-text for an image.

        Args:
            image_name: Name of the image/graphic object
            width_mm: New width in mm (keeps aspect ratio if height omitted)
            height_mm: New height in mm (keeps aspect ratio if width omitted)
            title: Image title (caption)
            description: Alt-text / description
            anchor_type: 0=AT_PARAGRAPH, 1=AS_CHARACTER, 2=AT_PAGE,
                         3=AT_FRAME, 4=AT_CHARACTER
            hori_orient: 0=NONE, 1=RIGHT, 2=CENTER, 3=LEFT
            vert_orient: 0=NONE, 1=TOP, 2=CENTER, 3=BOTTOM
            hori_orient_relation: 0=PARAGRAPH, 1=FRAME, 2=PAGE, etc.
            vert_orient_relation: 0=PARAGRAPH, 1=FRAME, 2=PAGE, etc.
            crop_top_mm: Crop from top in mm
            crop_bottom_mm: Crop from bottom in mm
            crop_left_mm: Crop from left in mm
            crop_right_mm: Crop from right in mm
        """
        try:
            doc = self._resolve_document(file_path)
            graphics = doc.getGraphicObjects()

            if not graphics.hasByName(image_name):
                return {"success": False,
                        "error": f"Image '{image_name}' not found",
                        "available": list(graphics.getElementNames())}

            graphic = graphics.getByName(image_name)
            changed = []

            # Resize
            if width_mm is not None or height_mm is not None:
                try:
                    size = graphic.getPropertyValue("Size")
                except Exception:
                    from com.sun.star.awt import Size as AwtSize
                    size = AwtSize(graphic.Width, graphic.Height)

                cur_w = size.Width   # in 1/100 mm
                cur_h = size.Height

                if width_mm is not None and height_mm is not None:
                    size.Width = width_mm * 100
                    size.Height = height_mm * 100
                elif width_mm is not None:
                    ratio = (width_mm * 100) / cur_w if cur_w else 1
                    size.Width = width_mm * 100
                    size.Height = int(cur_h * ratio)
                else:
                    ratio = (height_mm * 100) / cur_h if cur_h else 1
                    size.Height = height_mm * 100
                    size.Width = int(cur_w * ratio)

                graphic.setPropertyValue("Size", size)
                changed.append(f"size={size.Width//100}x{size.Height//100}mm")

            if title is not None:
                graphic.setPropertyValue("Title", title)
                changed.append(f"title={title}")

            if description is not None:
                graphic.setPropertyValue("Description", description)
                changed.append(f"description set")

            if anchor_type is not None:
                graphic.setPropertyValue("AnchorType", anchor_type)
                labels = {0: "AT_PARAGRAPH", 1: "AS_CHARACTER",
                          2: "AT_PAGE", 3: "AT_FRAME", 4: "AT_CHARACTER"}
                changed.append(f"anchor={labels.get(anchor_type, anchor_type)}")

            if hori_orient is not None:
                graphic.setPropertyValue("HoriOrient", hori_orient)
                changed.append(f"hori_orient={hori_orient}")

            if vert_orient is not None:
                graphic.setPropertyValue("VertOrient", vert_orient)
                changed.append(f"vert_orient={vert_orient}")

            if hori_orient_relation is not None:
                graphic.setPropertyValue(
                    "HoriOrientRelation", hori_orient_relation)
                changed.append(f"hori_orient_relation={hori_orient_relation}")

            if vert_orient_relation is not None:
                graphic.setPropertyValue(
                    "VertOrientRelation", vert_orient_relation)
                changed.append(f"vert_orient_relation={vert_orient_relation}")

            if any(v is not None for v in (crop_top_mm, crop_bottom_mm,
                                           crop_left_mm, crop_right_mm)):
                try:
                    crop = graphic.getPropertyValue("GraphicCrop")
                except Exception:
                    from com.sun.star.text import GraphicCrop
                    crop = GraphicCrop()
                if crop_top_mm is not None:
                    crop.Top = crop_top_mm * 100
                if crop_bottom_mm is not None:
                    crop.Bottom = crop_bottom_mm * 100
                if crop_left_mm is not None:
                    crop.Left = crop_left_mm * 100
                if crop_right_mm is not None:
                    crop.Right = crop_right_mm * 100
                graphic.setPropertyValue("GraphicCrop", crop)
                changed.append(
                    f"crop=T{crop.Top//100}/B{crop.Bottom//100}"
                    f"/L{crop.Left//100}/R{crop.Right//100}mm")

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "image": image_name,
                    "changes": changed}
        except Exception as e:
            logger.error(f"Failed to set image properties: {e}")
            return {"success": False, "error": str(e)}

    def insert_image(self, image_path: str,
                     paragraph_index: int = None,
                     locator: str = None,
                     caption: str = None,
                     with_frame: bool = True,
                     width_mm: int = None,
                     height_mm: int = None,
                     file_path: str = None) -> Dict[str, Any]:
        """Insert an image from a file path at a paragraph position."""
        try:
            import os
            if not os.path.isfile(image_path):
                return {"success": False,
                        "error": f"Image file not found: {image_path}"}

            doc = self._resolve_document(file_path)

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()
            idx = 0
            target = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == paragraph_index:
                    target = element
                    break
                idx += 1

            if target is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            # Convert path to file URL
            image_url = "file://" + image_path
            if not image_path.startswith("/"):
                image_url = "file:///" + image_path

            # Default size
            w_100mm = (width_mm or 80) * 100   # in 1/100 mm
            h_100mm = (height_mm or 80) * 100

            from com.sun.star.awt import Size as AwtSize

            if with_frame:
                # Create text frame
                frame = doc.createInstance(
                    "com.sun.star.text.TextFrame")
                frame_size = AwtSize(w_100mm, h_100mm)
                frame.setPropertyValue("Size", frame_size)
                frame.setPropertyValue("AnchorType", 4)  # AT_CHARACTER
                frame.setPropertyValue("HoriOrient", 0)  # NONE
                frame.setPropertyValue("VertOrient", 0)  # NONE

                cursor = doc_text.createTextCursorByRange(target.getEnd())
                doc_text.insertTextContent(cursor, frame, False)

                # Create graphic inside the frame
                graphic = doc.createInstance(
                    "com.sun.star.text.TextGraphicObject")
                graphic.setPropertyValue("GraphicURL", image_url)
                graphic_size = AwtSize(w_100mm, h_100mm)
                graphic.setPropertyValue("Size", graphic_size)
                graphic.setPropertyValue("AnchorType", 0)  # AT_PARAGRAPH
                graphic.setPropertyValue("HoriOrient", 2)  # CENTER
                graphic.setPropertyValue("VertOrient", 1)  # TOP

                frame_text = frame.getText()
                frame_cursor = frame_text.createTextCursor()
                frame_text.insertTextContent(
                    frame_cursor, graphic, False)

                # Add caption text if provided
                if caption:
                    frame_cursor = frame_text.createTextCursorByRange(
                        frame_text.getEnd())
                    frame_text.insertControlCharacter(
                        frame_cursor, 0, False)  # PARAGRAPH_BREAK
                    frame_cursor = frame_text.createTextCursorByRange(
                        frame_text.getEnd())
                    frame_text.insertString(frame_cursor, caption, False)

                if doc.hasLocation():
                    self._store_doc(doc)

                return {"success": True,
                        "frame_name": frame.getName(),
                        "image_name": graphic.getName(),
                        "with_frame": True,
                        "caption": caption}
            else:
                # Standalone image (no frame)
                graphic = doc.createInstance(
                    "com.sun.star.text.TextGraphicObject")
                graphic.setPropertyValue("GraphicURL", image_url)
                graphic_size = AwtSize(w_100mm, h_100mm)
                graphic.setPropertyValue("Size", graphic_size)
                graphic.setPropertyValue("AnchorType", 4)  # AT_CHARACTER

                cursor = doc_text.createTextCursorByRange(target.getEnd())
                doc_text.insertTextContent(cursor, graphic, False)

                if doc.hasLocation():
                    self._store_doc(doc)

                return {"success": True,
                        "image_name": graphic.getName(),
                        "with_frame": False}
        except Exception as e:
            logger.error(f"Failed to insert image: {e}")
            return {"success": False, "error": str(e)}

    def delete_image(self, image_name: str,
                     remove_frame: bool = True,
                     file_path: str = None) -> Dict[str, Any]:
        """Delete an image. If inside a frame: remove_frame=True (default)
        removes the whole frame; remove_frame=False removes only the image."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getGraphicObjects'):
                return {"success": False,
                        "error": "Document does not support graphic objects"}

            graphics = doc.getGraphicObjects()
            if not graphics.hasByName(image_name):
                return {"success": False,
                        "error": f"Image '{image_name}' not found",
                        "available": list(graphics.getElementNames())}

            graphic = graphics.getByName(image_name)
            doc_text = doc.getText()

            # Find if the image sits inside a text frame by
            # comparing anchor text with each frame's text using
            # UNO object equality (==).
            anchor_text = graphic.getAnchor().getText()
            frame_name = None
            parent_frame = None
            if hasattr(doc, 'getTextFrames'):
                frames_access = doc.getTextFrames()
                for fname in frames_access.getElementNames():
                    fr = frames_access.getByName(fname)
                    if fr.getText() == anchor_text:
                        frame_name = fname
                        parent_frame = fr
                        break

            if frame_name is not None and remove_frame:
                # Remove the whole frame (takes image + caption with it)
                doc_text.removeTextContent(parent_frame)
            elif frame_name is not None:
                # Remove only the image, keep the frame
                anchor_text.removeTextContent(graphic)
            else:
                # Standalone image — remove directly
                doc_text.removeTextContent(graphic)

            if doc.hasLocation():
                self._store_doc(doc)

            result = {"success": True, "deleted_image": image_name}
            if frame_name and remove_frame:
                result["deleted_frame"] = frame_name
            elif frame_name:
                result["kept_frame"] = frame_name
            return result
        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            return {"success": False, "error": str(e)}

    def replace_image(self, image_name: str, new_image_path: str,
                      width_mm: int = None, height_mm: int = None,
                      file_path: str = None) -> Dict[str, Any]:
        """Replace an image's graphic source, keeping its frame/position."""
        try:
            import os
            if not os.path.isfile(new_image_path):
                return {"success": False,
                        "error": f"Image file not found: {new_image_path}"}

            doc = self._resolve_document(file_path)
            graphics = doc.getGraphicObjects()
            if not graphics.hasByName(image_name):
                return {"success": False,
                        "error": f"Image '{image_name}' not found",
                        "available": list(graphics.getElementNames())}

            graphic = graphics.getByName(image_name)

            # Convert path to file URL
            image_url = "file://" + new_image_path
            if not new_image_path.startswith("/"):
                image_url = "file:///" + new_image_path

            graphic.setPropertyValue("GraphicURL", image_url)

            # Optionally resize
            if width_mm is not None or height_mm is not None:
                from com.sun.star.awt import Size as AwtSize
                size = graphic.getPropertyValue("Size")
                cur_w = size.Width
                cur_h = size.Height
                if width_mm is not None and height_mm is not None:
                    size.Width = width_mm * 100
                    size.Height = height_mm * 100
                elif width_mm is not None:
                    ratio = (width_mm * 100) / cur_w if cur_w else 1
                    size.Width = width_mm * 100
                    size.Height = int(cur_h * ratio)
                else:
                    ratio = (height_mm * 100) / cur_h if cur_h else 1
                    size.Height = height_mm * 100
                    size.Width = int(cur_w * ratio)
                graphic.setPropertyValue("Size", size)

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "image_name": image_name,
                    "new_source": new_image_path}
        except Exception as e:
            logger.error(f"Failed to replace image: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Text Frames
    # ----------------------------------------------------------------

    def list_text_frames(self, file_path: str = None) -> Dict[str, Any]:
        """List all text frames in the document."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getTextFrames'):
                return {"success": False,
                        "error": "Document does not support text frames"}

            frames_access = doc.getTextFrames()

            # Find which images belong to which frame using UNO ==
            frame_images = {}  # frame_name -> [image_name, ...]
            if hasattr(doc, 'getGraphicObjects'):
                graphics = doc.getGraphicObjects()
                for gname in graphics.getElementNames():
                    graphic = graphics.getByName(gname)
                    try:
                        anchor_text = graphic.getAnchor().getText()
                        for fname in frames_access.getElementNames():
                            fr = frames_access.getByName(fname)
                            if fr.getText() == anchor_text:
                                frame_images.setdefault(
                                    fname, []).append(gname)
                                break
                    except Exception:
                        pass

            result = []
            for fname in frames_access.getElementNames():
                frame = frames_access.getByName(fname)
                entry = {"name": fname}
                try:
                    size = frame.getPropertyValue("Size")
                    entry["width_mm"] = size.Width // 100
                    entry["height_mm"] = size.Height // 100
                except Exception:
                    pass
                try:
                    val = frame.getPropertyValue("AnchorType")
                    try:
                        entry["anchor_type"] = val.value
                    except AttributeError:
                        entry["anchor_type"] = str(val)
                except Exception:
                    pass
                for prop, key in (("HoriOrient", "hori_orient"),
                                  ("VertOrient", "vert_orient")):
                    try:
                        entry[key] = int(frame.getPropertyValue(prop))
                    except Exception:
                        pass
                try:
                    anchor = frame.getAnchor()
                    pidx = self._anchor_para_index(doc, anchor)
                    if pidx is not None:
                        entry["paragraph_index"] = pidx
                    page = self._resolve_page(doc, fname, anchor)
                    if page is not None:
                        entry["page"] = page
                except Exception:
                    pass
                if fname in frame_images:
                    entry["images"] = frame_images[fname]
                result.append(entry)

            return {"success": True, "frames": result,
                    "count": len(result)}
        except Exception as e:
            logger.error(f"Failed to list text frames: {e}")
            return {"success": False, "error": str(e)}

    def get_text_frame_info(self, frame_name: str,
                            file_path: str = None) -> Dict[str, Any]:
        """Get detailed info about a specific text frame."""
        try:
            doc = self._resolve_document(file_path)
            frames_access = doc.getTextFrames()

            if not frames_access.hasByName(frame_name):
                return {"success": False,
                        "error": f"Frame '{frame_name}' not found",
                        "available": list(frames_access.getElementNames())}

            frame = frames_access.getByName(frame_name)
            info = {"name": frame_name, "success": True}

            # Size
            try:
                size = frame.getPropertyValue("Size")
                info["width_mm"] = size.Width // 100
                info["height_mm"] = size.Height // 100
            except Exception:
                pass

            # Anchor type
            anchor_names = ["AT_PARAGRAPH", "AS_CHARACTER",
                            "AT_PAGE", "AT_FRAME", "AT_CHARACTER"]
            try:
                val = frame.getPropertyValue("AnchorType")
                try:
                    str_val = val.value
                except AttributeError:
                    str_val = str(val)
                info["anchor_type"] = str_val
                if str_val in anchor_names:
                    info["anchor_type_id"] = anchor_names.index(str_val)
            except Exception:
                pass

            # Orientation
            for prop in ("HoriOrient", "VertOrient"):
                try:
                    info[prop] = int(frame.getPropertyValue(prop))
                except Exception:
                    pass

            # Position (used when orient=NONE)
            for prop, key in (("HoriOrientPosition", "hori_pos_mm"),
                              ("VertOrientPosition", "vert_pos_mm")):
                try:
                    info[key] = frame.getPropertyValue(prop) // 100
                except Exception:
                    pass

            # Wrap / Surround
            for prop in ("Surround", "TextWrapType"):
                try:
                    val = frame.getPropertyValue(prop)
                    wrap_names = {0: "NONE", 1: "COLUMN", 2: "PARALLEL",
                                  3: "DYNAMIC", 4: "THROUGH"}
                    ival = int(val)
                    info["wrap"] = wrap_names.get(ival, str(ival))
                    info["wrap_id"] = ival
                    break
                except Exception:
                    pass

            # Paragraph index and page
            try:
                anchor = frame.getAnchor()
                pidx = self._anchor_para_index(doc, anchor)
                if pidx is not None:
                    info["paragraph_index"] = pidx
                page = self._resolve_page(doc, frame_name, anchor)
                if page is not None:
                    info["page"] = page
            except Exception:
                pass

            # Contained text (caption)
            try:
                frame_text = frame.getText().getString()
                if frame_text:
                    info["text"] = frame_text
            except Exception:
                pass

            # Contained images
            if hasattr(doc, 'getGraphicObjects'):
                imgs = []
                graphics = doc.getGraphicObjects()
                ft = frame.getText()
                for gname in graphics.getElementNames():
                    graphic = graphics.getByName(gname)
                    try:
                        if graphic.getAnchor().getText() == ft:
                            imgs.append(gname)
                    except Exception:
                        pass
                if imgs:
                    info["images"] = imgs

            return info
        except Exception as e:
            logger.error(f"Failed to get text frame info: {e}")
            return {"success": False, "error": str(e)}

    def set_text_frame_properties(self, frame_name: str,
                                  width_mm: int = None,
                                  height_mm: int = None,
                                  anchor_type: int = None,
                                  hori_orient: int = None,
                                  vert_orient: int = None,
                                  hori_pos_mm: int = None,
                                  vert_pos_mm: int = None,
                                  wrap: int = None,
                                  paragraph_index: int = None,
                                  file_path: str = None) -> Dict[str, Any]:
        """Modify text frame properties.

        Args:
            frame_name: Name of the text frame
            width_mm: New width in mm
            height_mm: New height in mm
            anchor_type: 0=AT_PARAGRAPH, 1=AS_CHARACTER, 2=AT_PAGE,
                         3=AT_FRAME, 4=AT_CHARACTER
            hori_orient: 0=NONE, 1=RIGHT, 2=CENTER, 3=LEFT
            vert_orient: 0=NONE, 1=TOP, 2=CENTER, 3=BOTTOM
            hori_pos_mm: Horizontal position in mm (when hori_orient=NONE)
            vert_pos_mm: Vertical position in mm (when vert_orient=NONE)
            wrap: 0=NONE, 1=COLUMN, 2=PARALLEL, 3=DYNAMIC, 4=THROUGH
            paragraph_index: Move anchor to this paragraph index
        """
        try:
            doc = self._resolve_document(file_path)
            frames_access = doc.getTextFrames()

            if not frames_access.hasByName(frame_name):
                return {"success": False,
                        "error": f"Frame '{frame_name}' not found",
                        "available": list(frames_access.getElementNames())}

            frame = frames_access.getByName(frame_name)
            changed = []

            # Resize
            if width_mm is not None or height_mm is not None:
                size = frame.getPropertyValue("Size")
                if width_mm is not None:
                    size.Width = width_mm * 100
                if height_mm is not None:
                    size.Height = height_mm * 100
                frame.setPropertyValue("Size", size)
                changed.append(
                    f"size={size.Width // 100}x{size.Height // 100}mm")

            if anchor_type is not None:
                frame.setPropertyValue("AnchorType", anchor_type)
                labels = {0: "AT_PARAGRAPH", 1: "AS_CHARACTER",
                          2: "AT_PAGE", 3: "AT_FRAME", 4: "AT_CHARACTER"}
                changed.append(
                    f"anchor={labels.get(anchor_type, anchor_type)}")

            if hori_orient is not None:
                frame.setPropertyValue("HoriOrient", hori_orient)
                changed.append(f"hori_orient={hori_orient}")

            if vert_orient is not None:
                frame.setPropertyValue("VertOrient", vert_orient)
                changed.append(f"vert_orient={vert_orient}")

            if hori_pos_mm is not None:
                frame.setPropertyValue(
                    "HoriOrientPosition", hori_pos_mm * 100)
                changed.append(f"hori_pos={hori_pos_mm}mm")

            if vert_pos_mm is not None:
                frame.setPropertyValue(
                    "VertOrientPosition", vert_pos_mm * 100)
                changed.append(f"vert_pos={vert_pos_mm}mm")

            if wrap is not None:
                # Try Surround first (more common), fall back to TextWrapType
                try:
                    frame.setPropertyValue("Surround", wrap)
                except Exception:
                    frame.setPropertyValue("TextWrapType", wrap)
                wrap_names = {0: "NONE", 1: "COLUMN", 2: "PARALLEL",
                              3: "DYNAMIC", 4: "THROUGH"}
                changed.append(
                    f"wrap={wrap_names.get(wrap, wrap)}")

            if paragraph_index is not None:
                text = doc.getText()
                cursor = text.createTextCursor()
                cursor.gotoStart(False)
                for _ in range(paragraph_index):
                    if not cursor.gotoNextParagraph(False):
                        break
                frame.attach(cursor)
                changed.append(f"paragraph_index={paragraph_index}")

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "frame": frame_name,
                    "changes": changed}
        except Exception as e:
            logger.error(f"Failed to set text frame properties: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Recent Documents
    # ----------------------------------------------------------------

    def get_recent_documents(self, max_count: int = 20) -> Dict[str, Any]:
        """Get the list of recently opened documents from LO history."""
        try:
            cfg_provider = self.smgr.createInstanceWithContext(
                "com.sun.star.configuration.ConfigurationProvider",
                self.ctx)

            import urllib.parse

            # Try multiple known config paths
            paths_to_try = [
                "/org.openoffice.Office.Histories/Histories/PickList/ItemList",
                "/org.openoffice.Office.Histories/Histories/PickList",
                "/org.openoffice.Office.Common/History/PickList",
            ]

            for node_path in paths_to_try:
                try:
                    prop = PropertyValue()
                    prop.Name = "nodepath"
                    prop.Value = node_path

                    access = cfg_provider.createInstanceWithArguments(
                        "com.sun.star.configuration.ConfigurationAccess",
                        (prop,))

                    items = access.getElementNames()
                    if not items:
                        continue

                    docs = []
                    for i, name in enumerate(items):
                        if i >= max_count:
                            break
                        try:
                            url = name
                            item = access.getByName(name)

                            title = ""
                            try:
                                title = item.getByName("Title")
                            except Exception:
                                try:
                                    title = item.getPropertyValue("Title")
                                except Exception:
                                    pass

                            path = url
                            if url.startswith("file:///"):
                                path = urllib.parse.unquote(
                                    url[8:]).replace("/", "\\")

                            entry = {"url": url, "path": path}
                            if title:
                                entry["title"] = title
                            docs.append(entry)
                        except Exception:
                            # name might be the URL directly (leaf node)
                            path = name
                            if name.startswith("file:///"):
                                path = urllib.parse.unquote(
                                    name[8:]).replace("/", "\\")
                            docs.append({"url": name, "path": path})

                    if docs:
                        return {"success": True, "documents": docs,
                                "count": len(docs),
                                "config_path": node_path}
                except Exception:
                    continue

            return {"success": True, "documents": [],
                    "count": 0,
                    "note": "No recent documents found in any config path"}
        except Exception as e:
            logger.error(f"Failed to get recent documents: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Structural navigation
    # ----------------------------------------------------------------

    def list_sections(self, file_path: str = None) -> Dict[str, Any]:
        """List all named text sections."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getTextSections'):
                return {"success": True, "sections": [], "count": 0}

            supplier = doc.getTextSections()
            names = supplier.getElementNames()
            sections = []
            for name in names:
                section = supplier.getByName(name)
                sections.append({
                    "name": name,
                    "is_visible": getattr(section, 'IsVisible', True),
                    "is_protected": getattr(section, 'IsProtected', False)
                })
            return {"success": True, "sections": sections,
                    "count": len(sections)}
        except Exception as e:
            logger.error(f"Failed to list sections: {e}")
            return {"success": False, "error": str(e)}

    def read_section(self, section_name: str,
                     file_path: str = None) -> Dict[str, Any]:
        """Read the content of a named text section."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getTextSections'):
                return {"success": False,
                        "error": "Document does not support sections"}

            sections = doc.getTextSections()
            if not sections.hasByName(section_name):
                return {"success": False,
                        "error": f"Section '{section_name}' not found",
                        "available": list(sections.getElementNames())}

            section = sections.getByName(section_name)
            content = section.getAnchor().getString()
            return {"success": True, "section_name": section_name,
                    "content": content, "length": len(content)}
        except Exception as e:
            logger.error(f"Failed to read section: {e}")
            return {"success": False, "error": str(e)}

    def list_bookmarks(self, file_path: str = None) -> Dict[str, Any]:
        """List all bookmarks in the document."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getBookmarks'):
                return {"success": True, "bookmarks": [], "count": 0}

            bookmarks = doc.getBookmarks()
            names = bookmarks.getElementNames()
            result = []
            for name in names:
                bm = bookmarks.getByName(name)
                anchor_text = bm.getAnchor().getString()
                result.append({
                    "name": name,
                    "preview": anchor_text[:100] if anchor_text else ""
                })
            return {"success": True, "bookmarks": result,
                    "count": len(result)}
        except Exception as e:
            logger.error(f"Failed to list bookmarks: {e}")
            return {"success": False, "error": str(e)}

    def get_page_count(self, file_path: str = None) -> Dict[str, Any]:
        """Get the page count via XPageCursor."""
        try:
            doc = self._resolve_document(file_path)
            try:
                controller = doc.getCurrentController()
                if controller:
                    vc = controller.getViewCursor()
                    vc.jumpToLastPage()
                    page_count = vc.getPage()
                    vc.jumpToFirstPage()
                    return {"success": True, "page_count": page_count}
            except Exception:
                pass
            return {"success": False,
                    "error": "Could not determine page count "
                             "(requires visible document)"}
        except Exception as e:
            logger.error(f"Failed to get page count: {e}")
            return {"success": False, "error": str(e)}

    def goto_page(self, page: int,
                  file_path: str = None) -> Dict[str, Any]:
        """Scroll the view to a specific page."""
        try:
            doc = self._resolve_document(file_path)
            controller = doc.getCurrentController()
            vc = controller.getViewCursor()
            vc.jumpToPage(page)
            actual = vc.getPage()
            return {"success": True, "page": actual}
        except Exception as e:
            logger.error(f"Failed to goto page: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Calc tools
    # ----------------------------------------------------------------

    def _parse_cell_address(self, addr: str):
        """Parse 'A1' or 'Sheet1.A1' -> (sheet_name_or_None, col, row)."""
        sheet_name = None
        if '.' in addr:
            sheet_name, addr = addr.split('.', 1)
        # Parse column letters + row number
        col_str = ""
        row_str = ""
        for ch in addr:
            if ch.isalpha():
                col_str += ch
            else:
                row_str += ch
        col = 0
        for ch in col_str.upper():
            col = col * 26 + (ord(ch) - ord('A') + 1)
        col -= 1  # 0-based
        row = int(row_str) - 1  # 0-based
        return sheet_name, col, row

    def _get_calc_sheet(self, doc, sheet_name: str = None):
        """Get a sheet by name or the active sheet."""
        sheets = doc.getSheets()
        if sheet_name:
            if not sheets.hasByName(sheet_name):
                raise ValueError(f"Sheet '{sheet_name}' not found. "
                                 f"Available: {list(sheets.getElementNames())}")
            return sheets.getByName(sheet_name)
        # Use active sheet
        controller = doc.getCurrentController()
        if controller:
            return controller.getActiveSheet()
        return sheets.getByIndex(0)

    def read_cells(self, range_str: str,
                   file_path: str = None) -> Dict[str, Any]:
        """Read cell values from a range (e.g. 'A1:D10' or 'Sheet1.A1:D10')."""
        try:
            doc = self._resolve_document(file_path)
            if not self._is_calc(doc):
                return {"success": False, "error": "Not a Calc document"}

            # Parse range
            if ':' in range_str:
                start_addr, end_addr = range_str.split(':', 1)
            else:
                start_addr = end_addr = range_str

            s_sheet, s_col, s_row = self._parse_cell_address(start_addr)
            e_sheet, e_col, e_row = self._parse_cell_address(end_addr)
            sheet_name = s_sheet or e_sheet
            sheet = self._get_calc_sheet(doc, sheet_name)

            cell_range = sheet.getCellRangeByPosition(
                s_col, s_row, e_col, e_row)
            data = cell_range.getDataArray()

            # Convert to list of lists (tuples -> lists)
            rows = [list(row) for row in data]

            return {
                "success": True,
                "range": range_str,
                "sheet": sheet.getName(),
                "data": rows,
                "row_count": len(rows),
                "col_count": len(rows[0]) if rows else 0,
            }
        except Exception as e:
            logger.error(f"Failed to read cells: {e}")
            return {"success": False, "error": str(e)}

    def write_cell(self, cell: str, value: str,
                   file_path: str = None) -> Dict[str, Any]:
        """Write a value to a cell (e.g. 'B3' or 'Sheet1.B3')."""
        try:
            doc = self._resolve_document(file_path)
            if not self._is_calc(doc):
                return {"success": False, "error": "Not a Calc document"}

            sheet_name, col, row = self._parse_cell_address(cell)
            sheet = self._get_calc_sheet(doc, sheet_name)
            cell_obj = sheet.getCellByPosition(col, row)

            # Try to set as number first, fall back to string
            try:
                num_val = float(value)
                cell_obj.setValue(num_val)
            except ValueError:
                cell_obj.setString(value)

            if doc.hasLocation():
                self._store_doc(doc)

            return {
                "success": True,
                "cell": cell,
                "sheet": sheet.getName(),
                "value": value,
            }
        except Exception as e:
            logger.error(f"Failed to write cell: {e}")
            return {"success": False, "error": str(e)}

    def list_sheets(self, file_path: str = None) -> Dict[str, Any]:
        """List all sheets with names and basic info."""
        try:
            doc = self._resolve_document(file_path)
            if not self._is_calc(doc):
                return {"success": False, "error": "Not a Calc document"}

            sheets_obj = doc.getSheets()
            count = sheets_obj.getCount()
            sheets = []
            for i in range(count):
                sheet = sheets_obj.getByIndex(i)
                sheets.append({
                    "index": i,
                    "name": sheet.getName(),
                    "is_visible": sheet.IsVisible if hasattr(sheet, 'IsVisible') else True,
                })
            return {"success": True, "sheets": sheets, "count": count}
        except Exception as e:
            logger.error(f"Failed to list sheets: {e}")
            return {"success": False, "error": str(e)}

    def get_sheet_info(self, sheet_name: str = None,
                       file_path: str = None) -> Dict[str, Any]:
        """Get info about a sheet: used range, row/col count."""
        try:
            doc = self._resolve_document(file_path)
            if not self._is_calc(doc):
                return {"success": False, "error": "Not a Calc document"}

            sheet = self._get_calc_sheet(doc, sheet_name)

            # Use cursor to find used area extent
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)

            range_addr = cursor.getRangeAddress()
            used_rows = range_addr.EndRow - range_addr.StartRow + 1
            used_cols = range_addr.EndColumn - range_addr.StartColumn + 1

            return {
                "success": True,
                "sheet_name": sheet.getName(),
                "used_rows": used_rows,
                "used_cols": used_cols,
                "start_row": range_addr.StartRow,
                "start_col": range_addr.StartColumn,
                "end_row": range_addr.EndRow,
                "end_col": range_addr.EndColumn,
            }
        except Exception as e:
            logger.error(f"Failed to get sheet info: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Impress tools
    # ----------------------------------------------------------------

    def list_slides(self, file_path: str = None) -> Dict[str, Any]:
        """List slides: count, titles, layout names."""
        try:
            doc = self._resolve_document(file_path)
            if not self._is_impress(doc):
                return {"success": False,
                        "error": "Not an Impress document"}

            pages = doc.getDrawPages()
            count = pages.getCount()
            slides = []
            for i in range(count):
                page = pages.getByIndex(i)
                name = page.Name if hasattr(page, 'Name') else f"Slide {i+1}"
                layout = ""
                try:
                    layout = str(page.Layout)
                except Exception:
                    pass
                # Try to get title from first shape
                title = ""
                for s in range(page.getCount()):
                    shape = page.getByIndex(s)
                    if hasattr(shape, 'getString'):
                        txt = shape.getString().strip()
                        if txt:
                            title = txt[:100]
                            break
                slides.append({
                    "index": i,
                    "name": name,
                    "layout": layout,
                    "title": title,
                })
            return {"success": True, "slides": slides, "count": count}
        except Exception as e:
            logger.error(f"Failed to list slides: {e}")
            return {"success": False, "error": str(e)}

    def read_slide_text(self, slide_index: int,
                        file_path: str = None) -> Dict[str, Any]:
        """Get all text from a slide + notes page."""
        try:
            doc = self._resolve_document(file_path)
            if not self._is_impress(doc):
                return {"success": False,
                        "error": "Not an Impress document"}

            pages = doc.getDrawPages()
            if slide_index < 0 or slide_index >= pages.getCount():
                return {"success": False,
                        "error": f"Slide index {slide_index} out of range "
                                 f"(0..{pages.getCount()-1})"}

            page = pages.getByIndex(slide_index)

            # Collect text from all shapes
            texts = []
            for s in range(page.getCount()):
                shape = page.getByIndex(s)
                if hasattr(shape, 'getString'):
                    txt = shape.getString()
                    if txt.strip():
                        texts.append(txt)

            # Notes page
            notes_text = ""
            try:
                notes_page = page.getNotesPage()
                for s in range(notes_page.getCount()):
                    shape = notes_page.getByIndex(s)
                    if hasattr(shape, 'getString'):
                        txt = shape.getString().strip()
                        if txt:
                            notes_text += txt + "\n"
            except Exception:
                pass

            return {
                "success": True,
                "slide_index": slide_index,
                "name": page.Name if hasattr(page, 'Name') else "",
                "texts": texts,
                "notes": notes_text.strip(),
            }
        except Exception as e:
            logger.error(f"Failed to read slide text: {e}")
            return {"success": False, "error": str(e)}

    def get_presentation_info(self,
                              file_path: str = None) -> Dict[str, Any]:
        """Slide count, dimensions, master page names."""
        try:
            doc = self._resolve_document(file_path)
            if not self._is_impress(doc):
                return {"success": False,
                        "error": "Not an Impress document"}

            pages = doc.getDrawPages()
            slide_count = pages.getCount()

            # Dimensions from first slide
            width = height = 0
            if slide_count > 0:
                first = pages.getByIndex(0)
                width = first.Width
                height = first.Height

            # Master pages
            masters = doc.getMasterPages()
            master_names = []
            for i in range(masters.getCount()):
                mp = masters.getByIndex(i)
                master_names.append(mp.Name if hasattr(mp, 'Name') else f"Master {i+1}")

            return {
                "success": True,
                "slide_count": slide_count,
                "width": width,
                "height": height,
                "master_pages": master_names,
            }
        except Exception as e:
            logger.error(f"Failed to get presentation info: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Document maintenance
    # ----------------------------------------------------------------

    def refresh_indexes(self, file_path: str = None) -> Dict[str, Any]:
        """Refresh all document indexes (TOC, alphabetical, etc.)."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getDocumentIndexes'):
                return {"success": False,
                        "error": "Document does not support indexes"}

            indexes = doc.getDocumentIndexes()
            count = indexes.getCount()
            refreshed = []
            for i in range(count):
                idx = indexes.getByIndex(i)
                idx.update()
                name = idx.getName() if hasattr(idx, 'getName') else f"index_{i}"
                refreshed.append(name)

            if count > 0 and doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "refreshed": refreshed,
                    "count": count}
        except Exception as e:
            logger.error(f"Failed to refresh indexes: {e}")
            return {"success": False, "error": str(e)}

    def update_fields(self, file_path: str = None) -> Dict[str, Any]:
        """Refresh all text fields (dates, page numbers, cross-refs)."""
        try:
            doc = self._resolve_document(file_path)
            if not hasattr(doc, 'getTextFields'):
                return {"success": False,
                        "error": "Document does not support text fields"}

            fields = doc.getTextFields()
            fields.refresh()

            # Count fields
            enum = fields.createEnumeration()
            count = 0
            while enum.hasMoreElements():
                enum.nextElement()
                count += 1

            return {"success": True, "fields_refreshed": count}
        except Exception as e:
            logger.error(f"Failed to update fields: {e}")
            return {"success": False, "error": str(e)}

    def delete_paragraph(self, paragraph_index: int = None,
                         locator: str = None,
                         file_path: str = None) -> Dict[str, Any]:
        """Delete a paragraph by index or locator."""
        try:
            doc = self._resolve_document(file_path)

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()
            idx = 0
            target = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == paragraph_index:
                    target = element
                    break
                idx += 1

            if target is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            idx_name = self._is_inside_index(target)
            if idx_name:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} is inside "
                                 f"index '{idx_name}'. Indexes are "
                                 f"auto-generated — use refresh_indexes()."}

            # Select the paragraph + its trailing break and delete
            cursor = doc_text.createTextCursorByRange(target)
            # Extend to include the paragraph break
            cursor.gotoStartOfParagraph(False)
            cursor.gotoEndOfParagraph(True)
            # If not the last paragraph, also grab the break after it
            if enum.hasMoreElements():
                cursor.goRight(1, True)
            doc_text.setString("") if False else None  # no-op
            cursor.setString("")

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True,
                    "message": f"Deleted paragraph {paragraph_index}"}
        except Exception as e:
            logger.error(f"Failed to delete paragraph: {e}")
            return {"success": False, "error": str(e)}

    def set_paragraph_text(self, paragraph_index: int = None,
                           text: str = "",
                           locator: str = None,
                           file_path: str = None) -> Dict[str, Any]:
        """Replace the entire text content of a paragraph (preserves style)."""
        try:
            doc = self._resolve_document(file_path)

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()
            idx = 0
            target = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == paragraph_index:
                    target = element
                    break
                idx += 1

            if target is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            idx_name = self._is_inside_index(target)
            if idx_name:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} is inside "
                                 f"index '{idx_name}'. Indexes are "
                                 f"auto-generated — use refresh_indexes()."}

            old_text = target.getString()
            target.setString(text)

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True,
                    "paragraph_index": paragraph_index,
                    "old_length": len(old_text),
                    "new_length": len(text)}
        except Exception as e:
            logger.error(f"Failed to set paragraph text: {e}")
            return {"success": False, "error": str(e)}

    def get_document_properties(self,
                                file_path: str = None) -> Dict[str, Any]:
        """Read document metadata (title, author, subject, keywords, etc.)."""
        try:
            doc = self._resolve_document(file_path)
            props = doc.getDocumentProperties()

            result = {
                "success": True,
                "title": props.Title,
                "author": props.Author,
                "subject": props.Subject,
                "description": props.Description,
                "keywords": list(props.Keywords) if props.Keywords else [],
                "generator": props.Generator,
            }

            # Creation/modification dates
            try:
                cd = props.CreationDate
                result["creation_date"] = (
                    f"{cd.Year:04d}-{cd.Month:02d}-{cd.Day:02d}")
            except Exception:
                pass
            try:
                md = props.ModificationDate
                result["modification_date"] = (
                    f"{md.Year:04d}-{md.Month:02d}-{md.Day:02d}")
            except Exception:
                pass

            # Custom properties
            try:
                user_props = props.getUserDefinedProperties()
                info = user_props.getPropertySetInfo()
                custom = {}
                for prop in info.getProperties():
                    try:
                        custom[prop.Name] = str(
                            user_props.getPropertyValue(prop.Name))
                    except Exception:
                        pass
                if custom:
                    result["custom_properties"] = custom
            except Exception:
                pass

            return result
        except Exception as e:
            logger.error(f"Failed to get document properties: {e}")
            return {"success": False, "error": str(e)}

    def set_document_properties(self, title: str = None,
                                author: str = None,
                                subject: str = None,
                                description: str = None,
                                keywords: list = None,
                                file_path: str = None) -> Dict[str, Any]:
        """Update document metadata."""
        try:
            doc = self._resolve_document(file_path)
            props = doc.getDocumentProperties()
            updated = []

            if title is not None:
                props.Title = title
                updated.append("title")
            if author is not None:
                props.Author = author
                updated.append("author")
            if subject is not None:
                props.Subject = subject
                updated.append("subject")
            if description is not None:
                props.Description = description
                updated.append("description")
            if keywords is not None:
                props.Keywords = tuple(keywords)
                updated.append("keywords")

            if updated and doc.hasLocation():
                self._store_doc(doc)

            return {"success": True, "updated_fields": updated}
        except Exception as e:
            logger.error(f"Failed to set document properties: {e}")
            return {"success": False, "error": str(e)}

    def set_paragraph_style(self, style_name: str,
                            paragraph_index: int = None,
                            locator: str = None,
                            file_path: str = None) -> Dict[str, Any]:
        """Set the paragraph style (e.g. 'Heading 1', 'Text Body', 'List Bullet')."""
        try:
            doc = self._resolve_document(file_path)

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()
            idx = 0
            target = None
            while enum.hasMoreElements():
                element = enum.nextElement()
                if idx == paragraph_index:
                    target = element
                    break
                idx += 1

            if target is None:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            idx_name = self._is_inside_index(target)
            if idx_name:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} is inside "
                                 f"index '{idx_name}'. Indexes are "
                                 f"auto-generated — use refresh_indexes()."}

            old_style = target.getPropertyValue("ParaStyleName")
            target.setPropertyValue("ParaStyleName", style_name)

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True,
                    "paragraph_index": paragraph_index,
                    "old_style": old_style,
                    "new_style": style_name}
        except Exception as e:
            logger.error(f"Failed to set paragraph style: {e}")
            return {"success": False, "error": str(e)}

    def duplicate_paragraph(self, paragraph_index: int = None,
                            locator: str = None,
                            count: int = 1,
                            file_path: str = None) -> Dict[str, Any]:
        """Duplicate a paragraph (with its style) after itself.

        If count > 1, duplicates the paragraph and the next (count-1)
        paragraphs as a block (useful for heading + body).
        """
        try:
            doc = self._resolve_document(file_path)

            if locator is not None and paragraph_index is None:
                resolved = self._resolve_locator(doc, locator)
                paragraph_index = resolved.get("para_index")
            if paragraph_index is None:
                return {"success": False,
                        "error": "Provide locator or paragraph_index"}

            doc_text = doc.getText()
            enum = doc_text.createEnumeration()

            # Collect target paragraphs
            paragraphs = []
            idx = 0
            while enum.hasMoreElements():
                element = enum.nextElement()
                if paragraph_index <= idx < paragraph_index + count:
                    if element.supportsService("com.sun.star.text.Paragraph"):
                        paragraphs.append({
                            "text": element.getString(),
                            "style": element.getPropertyValue("ParaStyleName"),
                        })
                    else:
                        paragraphs.append({
                            "text": "[table]",
                            "style": "",
                            "is_table": True,
                        })
                if idx >= paragraph_index + count - 1:
                    # Remember the last element to insert after
                    last_element = element
                    break
                idx += 1

            if not paragraphs:
                return {"success": False,
                        "error": f"Paragraph {paragraph_index} not found"}

            # Insert duplicates after the last collected paragraph
            cursor = doc_text.createTextCursorByRange(last_element)
            cursor.gotoEndOfParagraph(False)

            for para in paragraphs:
                if para.get("is_table"):
                    continue  # skip tables in duplication
                doc_text.insertControlCharacter(
                    cursor, PARAGRAPH_BREAK, False)
                doc_text.insertString(cursor, para["text"], False)
                if para["style"]:
                    cursor.setPropertyValue("ParaStyleName", para["style"])

            if doc.hasLocation():
                self._store_doc(doc)

            return {"success": True,
                    "duplicated_from": paragraph_index,
                    "paragraphs_duplicated": len(paragraphs)}
        except Exception as e:
            logger.error(f"Failed to duplicate paragraph: {e}")
            return {"success": False, "error": str(e)}

    def save_document_as(self, target_path: str,
                         file_path: str = None) -> Dict[str, Any]:
        """Save/duplicate a document under a new name."""
        try:
            doc = self._resolve_document(file_path)
            url = uno.systemPathToFileUrl(target_path)
            doc.storeToURL(url, ())
            logger.info(f"Saved document as {target_path}")
            return {"success": True,
                    "message": f"Document saved as {target_path}",
                    "path": target_path}
        except Exception as e:
            logger.error(f"Failed to save document as: {e}")
            return {"success": False, "error": str(e)}

    # ----------------------------------------------------------------
    # Original methods
    # ----------------------------------------------------------------

    def get_document_info(self, doc: Any = None) -> Dict[str, Any]:
        """Get information about a document"""
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"error": "No document available"}
            
            info = {
                "title": getattr(doc, 'Title', 'Unknown') if hasattr(doc, 'Title') else "Unknown",
                "url": doc.getURL() if hasattr(doc, 'getURL') else "",
                "modified": doc.isModified() if hasattr(doc, 'isModified') else False,
                "type": self._get_document_type(doc),
                "has_selection": self._has_selection(doc)
            }
            
            # Add document-specific information
            if self._is_writer(doc):
                text = doc.getText()
                info["word_count"] = len(text.getString().split())
                info["character_count"] = len(text.getString())
            elif self._is_calc(doc):
                sheets = doc.getSheets()
                info["sheet_count"] = sheets.getCount()
                info["sheet_names"] = [sheets.getByIndex(i).getName() 
                                     for i in range(sheets.getCount())]
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return {"error": str(e)}
    
    def insert_text(self, text: str, position: Optional[int] = None, doc: Any = None) -> Dict[str, Any]:
        """
        Insert text into a document
        
        Args:
            text: Text to insert
            position: Position to insert at (None for current cursor position)
            doc: Document to insert into (None for active document)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No active document"}
            
            # Handle Writer documents
            if self._is_writer(doc):
                text_obj = doc.getText()
                
                if position is None:
                    # Insert at current cursor position
                    cursor = doc.getCurrentController().getViewCursor()
                else:
                    # Insert at specific position
                    cursor = text_obj.createTextCursor()
                    cursor.gotoStart(False)
                    cursor.goRight(position, False)
                
                text_obj.insertString(cursor, text, False)
                logger.info(f"Inserted {len(text)} characters into Writer document")
                return {"success": True, "message": f"Inserted {len(text)} characters"}
            
            # Handle other document types
            else:
                return {"success": False, "error": f"Text insertion not supported for {self._get_document_type(doc)}"}
                
        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return {"success": False, "error": str(e)}
    
    def format_text(self, formatting: Dict[str, Any], doc: Any = None) -> Dict[str, Any]:
        """
        Apply formatting to selected text
        
        Args:
            formatting: Dictionary of formatting options
            doc: Document to format (None for active document)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc or not self._is_writer(doc):
                return {"success": False, "error": "No Writer document available"}
            
            # Get current selection
            selection = doc.getCurrentController().getSelection()
            if selection.getCount() == 0:
                return {"success": False, "error": "No text selected"}
            
            # Apply formatting to selection
            text_range = selection.getByIndex(0)
            
            # Apply various formatting options
            if "bold" in formatting:
                text_range.CharWeight = 150.0 if formatting["bold"] else 100.0
            
            if "italic" in formatting:
                text_range.CharPosture = 2 if formatting["italic"] else 0
            
            if "underline" in formatting:
                text_range.CharUnderline = 1 if formatting["underline"] else 0
            
            if "font_size" in formatting:
                text_range.CharHeight = formatting["font_size"]
            
            if "font_name" in formatting:
                text_range.CharFontName = formatting["font_name"]
            
            logger.info("Applied formatting to selected text")
            return {"success": True, "message": "Formatting applied successfully"}
            
        except Exception as e:
            logger.error(f"Failed to format text: {e}")
            return {"success": False, "error": str(e)}
    
    def save_document(self, doc: Any = None, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Save a document
        
        Args:
            doc: Document to save (None for active document)
            file_path: Path to save to (None to save to current location)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No document to save"}
            
            if file_path:
                # Save as new file
                url = uno.systemPathToFileUrl(file_path)
                doc.storeAsURL(url, ())
                logger.info(f"Saved document to {file_path}")
                return {"success": True, "message": f"Document saved to {file_path}"}
            else:
                # Save to current location
                if doc.hasLocation():
                    self._store_doc(doc)
                    logger.info("Saved document to current location")
                    return {"success": True, "message": "Document saved"}
                else:
                    return {"success": False, "error": "Document has no location, specify file_path"}
                    
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return {"success": False, "error": str(e)}
    
    def export_document(self, export_format: str, file_path: str, doc: Any = None) -> Dict[str, Any]:
        """
        Export document to different format
        
        Args:
            export_format: Target format ('pdf', 'docx', 'odt', 'txt', etc.)
            file_path: Path to export to
            doc: Document to export (None for active document)
            
        Returns:
            Result dictionary
        """
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No document to export"}
            
            # Filter map for different formats
            filter_map = {
                'pdf': 'writer_pdf_Export',
                'docx': 'MS Word 2007 XML',
                'doc': 'MS Word 97',
                'odt': 'writer8',
                'txt': 'Text',
                'rtf': 'Rich Text Format',
                'html': 'HTML (StarWriter)'
            }
            
            filter_name = filter_map.get(export_format.lower())
            if not filter_name:
                return {"success": False, "error": f"Unsupported export format: {export_format}"}
            
            # Prepare export properties
            properties = (
                PropertyValue("FilterName", 0, filter_name, 0),
                PropertyValue("Overwrite", 0, True, 0),
            )
            
            # Export document
            url = uno.systemPathToFileUrl(file_path)
            doc.storeToURL(url, properties)
            
            logger.info(f"Exported document to {file_path} as {export_format}")
            return {"success": True, "message": f"Document exported to {file_path}"}
            
        except Exception as e:
            logger.error(f"Failed to export document: {e}")
            return {"success": False, "error": str(e)}
    
    def get_text_content(self, doc: Any = None) -> Dict[str, Any]:
        """Get text content from a document"""
        try:
            if doc is None:
                doc = self.get_active_document()
            
            if not doc:
                return {"success": False, "error": "No document available"}
            
            if self._is_writer(doc):
                text = doc.getText().getString()
                return {"success": True, "content": text, "length": len(text)}
            else:
                return {"success": False, "error": f"Text extraction not supported for {self._get_document_type(doc)}"}
                
        except Exception as e:
            logger.error(f"Failed to get text content: {e}")
            return {"success": False, "error": str(e)}
    
    def _is_writer(self, doc: Any) -> bool:
        return hasattr(doc, 'supportsService') and doc.supportsService(
            "com.sun.star.text.TextDocument")

    def _is_calc(self, doc: Any) -> bool:
        return hasattr(doc, 'supportsService') and doc.supportsService(
            "com.sun.star.sheet.SpreadsheetDocument")

    def _is_impress(self, doc: Any) -> bool:
        return hasattr(doc, 'supportsService') and doc.supportsService(
            "com.sun.star.presentation.PresentationDocument")

    def _get_document_type(self, doc: Any) -> str:
        """Determine document type"""
        if hasattr(doc, 'supportsService'):
            if doc.supportsService("com.sun.star.text.TextDocument"):
                return "writer"
            if doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                return "calc"
            if doc.supportsService("com.sun.star.presentation.PresentationDocument"):
                return "impress"
            if doc.supportsService("com.sun.star.drawing.DrawingDocument"):
                return "draw"
        return "unknown"
    
    def _has_selection(self, doc: Any) -> bool:
        """Check if document has selected content"""
        try:
            if hasattr(doc, 'getCurrentController'):
                controller = doc.getCurrentController()
                if hasattr(controller, 'getSelection'):
                    selection = controller.getSelection()
                    return selection.getCount() > 0
        except:
            pass
        return False
