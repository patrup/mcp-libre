# LibreOffice MCP — Agent Guide

## Quick start

1. **No save required** — all tools work on the in-memory document via UNO. Even a brand-new unsaved doc is fully accessible.
2. **Always start with** `list_open_documents` — see what's open. No need to guess paths.
3. **Drill down, never dump** — `get_document_tree(depth=1)` → `get_heading_children` → `read_paragraphs`. Never load a whole document.
4. **Use bookmarks** (`bookmark:_mcp_*`) to remember positions — they survive edits. `paragraph:N` shifts after any insert/delete.
5. **Search, don't scan** — `search_in_document` uses native LO search. Don't loop through paragraphs.
6. **Find objects by page** — `get_page_objects(paragraph_index=N)` returns images/tables nearby. Don't use `list_images` on large docs.
7. **Check comments** — the human may have left TODOs. Call `list_comments` early.
8. **30s timeout** — UNO calls that exceed 30s return HTTP 504. Avoid `depth=0` or `content_strategy="full"` on large documents.

## First call

```
What do I need?
├── See what's open           → list_open_documents
├── Understand a document     → get_document_tree(depth=1)
├── Find specific text        → search_in_document(pattern="...")
├── Read a section            → get_heading_children(locator="bookmark:...")
│                               then read_paragraphs(locator="paragraph:N", count=10)
├── Find images near text     → get_page_objects(paragraph_index=N)
├── See human TODOs           → list_comments
├── Open a file               → open_document(file_path="...")
└── Full session example      → see "Typical Session" at the end of this guide
```

### Minimal session (5 calls)

```
list_open_documents                                         # 1. what's open?
get_document_tree(depth=1, content_strategy="first_lines")  # 2. table of contents + page numbers
search_in_document(pattern="keyword")                       # 3. find what you need
read_paragraphs(locator="paragraph:42", count=10)           # 4. read it
set_paragraph_text(locator="paragraph:42", text="...")       # 5. edit it
```

## Locators

All tools that take a `locator` parameter accept these formats:

| Locator | Example | What it targets | When to use |
|---------|---------|-----------------|-------------|
| `bookmark:` | `bookmark:_mcp_df3919e3` | The paragraph where this bookmark sits | **Default choice** — stable across edits |
| `heading:` | `heading:2.1` | 2nd top heading → 1st child | Quick structural nav (breaks if headings are added/removed) |
| `paragraph:` | `paragraph:42` | Paragraph at index 42 | Immediate use only — **do not store for later** |
| `page:` | `page:3` | First paragraph on page 3 | Visual reference — approximate, shifts with reflow |

### Rules

- **After editing** (insert, delete, duplicate paragraphs): stored `paragraph:N` values are invalid. Re-resolve via `resolve_bookmark` or re-call `get_document_tree`.
- **Bookmarks survive editing**: insert/delete paragraphs, edit text, resize images — the bookmark stays on its heading.
- **Bookmarks are created automatically** by `get_document_tree` (one per heading, persisted in the .odt file).
- **If a heading is deleted**, its bookmark becomes orphaned — `resolve_bookmark` will return an error. Call `get_document_tree` again to refresh.
- **`page:N` is approximate** — reflow (text edits, image resize) changes page boundaries. Use it to jump to an area, not to target a precise paragraph.

## content_strategy

Controls body text in `get_document_tree` / `get_heading_children`:

| Value | Returns | Use when |
|---|---|---|
| `"none"` | Headings only | Navigating structure |
| `"first_lines"` | Headings + first line of body | **Default** — good balance |
| `"ai_summary_first"` | AI summaries if cached, else first lines | Repeated analysis |
| `"full"` | Complete body text | Small sections only — **avoid on large docs** |

## Don't / Do

| Don't | Do instead |
|---|---|
| `insert_at_paragraph` then `set_paragraph_style` | `insert_at_paragraph(text="...", style="Text Body")` — one call |
| Multiple `insert_at_paragraph` calls for a section | `insert_paragraphs_batch(paragraphs=[...])` — one call, no index drift |
| Edit paragraphs inside Table of Contents | Editing indexes is blocked — use `refresh_indexes()` to update them |
| `get_text_content_live` on big docs | `get_document_tree` + `read_paragraphs` |
| `depth=0` on unknown docs | `depth=1`, then drill |
| `content_strategy="full"` at depth > 1 | `"first_lines"`, then read specific paragraphs |
| Read all paragraphs in a loop | `search_in_document` |
| Store `paragraph:N` for use after edits | Store the `bookmark` from `get_document_tree` |
| `list_images` on a 50-page doc | `get_page_objects(page=N)` for the page you care about |
| Edit without tracking | `set_track_changes(true)` first |
| Ignore human comments | `list_comments` → act → `resolve_comment` |
| Leave doc unprotected while working | `set_document_protection(true)` at start, `false` when done |

## Tool Reference

### Navigation (read-only)

| Tool | What it does |
|---|---|
| `list_open_documents` | List all open docs in LibreOffice |
| `open_document` | Open a file in LibreOffice |
| `get_document_tree` | Heading tree (with depth + content_strategy) |
| `get_heading_children` | Drill into a heading's children |
| `read_paragraphs` | Read N paragraphs from a locator |
| `get_paragraph_count` | Total paragraph count |
| `search_in_document` | Native search with context |
| `get_page_count` | Page count |
| `get_page_objects` | All images, tables, and frames on a page (the page index) |
| `list_sections` | Named text sections |
| `read_section` | Content of a named section |
| `list_bookmarks` | All bookmarks |
| `resolve_bookmark` | Bookmark → current paragraph index |

### Editing

| Tool | What it does |
|---|---|
| `replace_in_document` | Global find & replace (preserves formatting) |
| `insert_at_paragraph` | Insert text before/after a paragraph (optional `style`) |
| `insert_paragraphs_batch` | Insert N paragraphs in one call (each with text + style) |
| `set_paragraph_text` | Replace entire paragraph content (preserves style) |
| `set_paragraph_style` | Change paragraph style (e.g. "Heading 1", "Text Body") |
| `delete_paragraph` | Remove a paragraph |
| `duplicate_paragraph` | Copy a paragraph (with style) after itself. `count>1` for blocks |

### Document Protection

| Tool | What it does |
|---|---|
| `set_document_protection` | Lock/unlock the UI (no password, just a toggle) |

Lock the document before making edits so the human can't accidentally interfere. Uses Writer's ProtectForm setting — UNO/MCP calls pass through normally. **Always unlock when done.**

```
set_document_protection(enabled=true)   # UI read-only, MCP still works
# ... do your work ...
set_document_protection(enabled=false)  # human can edit again
```

### Comments & Review

| Tool | What it does |
|---|---|
| `list_comments` | List all human comments (excludes AI summaries) |
| `add_comment` | Add a comment at a paragraph |
| `resolve_comment` | Close a comment with a reason (adds reply + marks resolved) |
| `delete_comment` | Delete a comment and its replies |

**Workflow**: Human leaves TODOs as comments → agent reads with `list_comments` → acts on each → closes with `resolve_comment(name, resolution="Done: updated age to 14")`.

### Track Changes

| Tool | What it does |
|---|---|
| `set_track_changes` | Enable/disable change recording |
| `get_tracked_changes` | List all redlines (type, author, date) |
| `accept_all_changes` | Accept all tracked changes |
| `reject_all_changes` | Reject all tracked changes |

**Workflow**: `set_track_changes(true)` → make edits → human reviews diffs in LO → `accept_all_changes()` or `reject_all_changes()`.

### Styles

| Tool | What it does |
|---|---|
| `list_styles` | List styles in a family (Paragraph, Character, Page...) |
| `get_style_info` | Detailed style properties (font, size, margins) |

Use `list_styles(family="ParagraphStyles")` to discover existing styles before applying with `set_paragraph_style`. Keep the document clean — use existing styles, don't create a patchwork.

### Document management

| Tool | What it does |
|---|---|
| `save_document` | Save active document |
| `save_document_copy` | Save As / duplicate under a new name |
| `refresh_indexes` | Refresh Table of Contents and other indexes |
| `update_fields` | Refresh all fields (dates, page numbers, cross-refs) |
| `get_document_properties` | Read metadata (title, author, subject, keywords) |
| `set_document_properties` | Update metadata |

### AI annotations

| Tool | What it does |
|---|---|
| `add_ai_summary` | Attach AI summary to a heading |
| `get_ai_summaries` | List all AI annotations |
| `remove_ai_summary` | Remove an AI annotation |

### Writer Tables

| Tool | What it does |
|---|---|
| `list_tables` | List all text tables (name, rows, cols) |
| `read_table` | Read all cell contents as 2D array |
| `write_table_cell` | Write to a cell (e.g. 'B3') |
| `create_table` | Create a new table at a paragraph position |

### Images

| Tool | What it does |
|---|---|
| `list_images` | List all images (name, dimensions, title, page) |
| `get_image_info` | Detailed info (URL, anchor, position, crop) |
| `set_image_properties` | Resize, reanchor, orient, crop, set title/alt-text |
| `insert_image` | Insert an image from a file path (with or without caption frame) |
| `delete_image` | Delete an image (and optionally its parent frame) |
| `replace_image` | Swap the image source file, keeping frame/position/caption |

Insert with frame (default): `insert_image(image_path="/path/to/photo.jpg", locator="paragraph:5", caption="Photo de famille")`.
Insert standalone: `insert_image(image_path="/path/to/photo.jpg", locator="paragraph:5", with_frame=false)`.
Replace source (keeps frame + caption): `replace_image(image_name="Image1", new_image_path="/path/to/new.jpg")`.
Delete (removes frame + caption if framed): `delete_image(image_name="Image1")`.
Delete image only (keep frame for replacement): `delete_image(image_name="Image1", remove_frame=false)`.

Resize keeping aspect ratio: `set_image_properties(image_name="Image1", width_mm=80)`.
Set caption: `set_image_properties(image_name="Image1", title="Photo de famille")`.
Anchor types: 0=AT_PARAGRAPH, 1=AS_CHARACTER (inline), 2=AT_PAGE, 4=AT_CHARACTER.
Orient: hori_orient (0=NONE, 1=RIGHT, 2=CENTER, 3=LEFT), vert_orient (0=NONE, 1=TOP, 2=CENTER, 3=BOTTOM).
Crop: `crop_top_mm`, `crop_bottom_mm`, `crop_left_mm`, `crop_right_mm` — trims the visible area without distortion.

### Text Frames

| Tool | What it does |
|---|---|
| `list_frames` | List all text frames (name, size, anchor, page, contained images) |
| `get_frame_info` | Detailed info (size, position, wrap, caption text, images) |
| `set_frame_properties` | Resize, reposition, change wrap/anchor, move to paragraph |

Frames are containers that hold images + caption text. To control image layout (e.g. align 3 images in a row), manipulate the frames, not the images directly.

#### Strategy: Images with captions in frames

Images in Writer are often placed inside text frames alongside a caption. Key principles:

1. **Control layout via the frame**, not the image. Frame properties (size, position, wrap, anchor paragraph) determine where the content appears on the page.
2. **All frames in a row must share the same anchor paragraph.** If one frame is anchored to a different paragraph, `vert_pos_mm` values are relative to different baselines and won't align visually. Use `set_frame_properties(paragraph_index=N)` to move an anchor.
3. **Set images to CENTER/TOP** inside their frame (`hori_orient=2, vert_orient=1`). The image fills the top of the frame; the caption sits below.
4. **Set `hori_orient_relation=0` and `vert_orient_relation=0`** (PARAGRAPH) on all images in a group. If one image has relation=1 (FRAME) while others have 0, they will be visually offset even with identical orient values.
5. **Match image width to frame width** to avoid gaps. Calculate height proportionally to avoid distortion: `new_height = frame_width * original_height / original_width`.
6. **Use crop to equalize visual height** when images have different aspect ratios. Crop the taller one (`crop_bottom_mm`) to match the shorter one's height. **Important:** crop only trims the source — you must also set `height_mm` to the target display height, otherwise the image box stays at the original size.
7. **Frame height = image visible height + caption space** (~15mm for one-line caption, more for longer text).
8. **"50/50" layout** means each frame gets half the usable page width. Check actual margins and page size first. Example for A4 with ~170mm usable: `frame_width = (usable_width - (N-1) * gap) / N`. Positions: `hori_pos = i * (frame_width + gap)`.

#### Alignment checklist

```
# 1. Identify frames and images on the target page
list_frames → filter by page number
get_frame_info for each → note paragraph_index, positions, images

# 2. Move all frames to the same anchor paragraph
set_frame_properties(paragraph_index=N) for any mismatched frame

# 3. Resize frames to equal width, calculate positions
frame_width = (170 - (N-1) * 6) / N
set_frame_properties(width_mm=W, height_mm=H, hori_pos_mm=..., vert_pos_mm=0)

# 4. For each image in a frame:
#    a. Set orient and relation
set_image_properties(hori_orient=2, vert_orient=1,
                     hori_orient_relation=0, vert_orient_relation=0)
#    b. Resize to frame width, proportional height
new_h = frame_width * orig_h / orig_w
set_image_properties(width_mm=frame_width, height_mm=new_h)
#    c. Find the shortest image height → that's the target
target_h = min(all new_h values)
#    d. Crop taller images AND set display height
excess = new_h - target_h
set_image_properties(height_mm=target_h, crop_bottom_mm=excess)
```

#### Page cache

Page numbers are cached lazily. The first call resolves via ViewCursor and caches. Any `doc.store()` (triggered by any write operation) invalidates the cache for that document.

### Recent Documents

| Tool | What it does |
|---|---|
| `get_recent_documents` | LO history (paths + titles, max 20) |

Use this to find documents without knowing their exact path.

### Calc (.ods, .xlsx)

| Tool | What it does |
|---|---|
| `list_sheets` | Enumerate sheets |
| `get_sheet_info` | Used range, dimensions |
| `read_cells` | Read a cell range (e.g. `A1:D10`) |
| `write_cell` | Write a single cell |

Prefix cell addresses with sheet name for multi-sheet docs: `Sheet1.A1:D10`.

### Impress (.odp, .pptx)

| Tool | What it does |
|---|---|
| `list_slides` | Slide names and titles |
| `read_slide_text` | Text + notes from one slide |
| `get_presentation_info` | Metadata, dimensions |

## Typical Session: Document Revision

```
# 1. What's open?
list_open_documents

# 2. Duplicate the document for the new year
save_document_copy(target_path="C:/Users/.../IEF 2026.odt")
open_document(file_path="C:/Users/.../IEF 2026.odt")

# 3. Get the overview
get_document_tree(depth=1)

# 4. Lock the doc so human doesn't interfere
set_document_protection(enabled=true)

# 5. Check for human review comments
list_comments  # → human left "TODO: update ages" at paragraph 45

# 6. Enable track changes so human can review diffs
set_track_changes(enabled=true)

# 7. Global date replacement
replace_in_document(search="2025-2026", replace="2026-2027")

# 8. Refresh the Table of Contents
refresh_indexes()

# 9. Find specific content to update
search_in_document(pattern="13 ans", max_results=5)

# 10. Targeted paragraph edit (don't change it everywhere)
set_paragraph_text(locator="paragraph:45", text="Zachary, qui est âgé de 14 ans...")

# 11. Close the comment with what was done
resolve_comment(comment_name="__Annotation__42", resolution="Done: age updated 13→14")

# 12. Add a new section by duplicating an existing one as template
duplicate_paragraph(locator="bookmark:_mcp_abc123", count=4)

# 13. Update document metadata for the new year
set_document_properties(title="IEF 2026-2027", subject="Instruction en famille")

# 14. Save and unlock
save_document()
set_document_protection(enabled=false)  # human can edit again
```

## Page Object Indexing Strategy

Working with images, frames, and tables requires knowing their names, positions, and relationships. Rather than calling `list_images`, `list_frames`, and `list_tables` separately (each returns **all** objects in the document), use `get_page_objects` to build a focused index of a single page.

### `get_page_objects` — the page index tool

One call returns all images, tables, and frames on a page:

```
get_page_objects(page=3)
# → { images: [...], tables: [...], frames: [...] }
```

Each entry includes name, dimensions, paragraph_index, and (for frames) contained images. This is enough to plan layout changes without calling `get_image_info` or `get_frame_info` for every object.

You can also resolve from a locator or paragraph index:

```
get_page_objects(locator="paragraph:89")    # finds which page para 89 is on
get_page_objects(paragraph_index=89)        # same thing
```

### Recommended workflow for image/layout tasks

```
# 1. Identify the target page
get_page_objects(page=5)
# → images: [{name: "Image1", width_mm: 80, ...}, {name: "Image2", ...}]
#   frames: [{name: "Frame1", images: ["Image1"], ...}, ...]
#   tables: [...]

# 2. Cache this result locally — it's your index for the page
# Now you know all names, sizes, and which images belong to which frames

# 3. Work from the index: resize, reposition, crop, insert, delete
set_frame_properties(frame_name="Frame1", width_mm=82, hori_pos_mm=0)
set_image_properties(image_name="Image1", width_mm=82, height_mm=60)

# 4. After structural changes (insert/delete), re-index the page
#    because names and paragraph indices may have changed
get_page_objects(page=5)
```

### When to re-index

Re-index a page (call `get_page_objects` again) after:
- Inserting or deleting an image (`insert_image`, `delete_image`)
- Creating or deleting a table (`create_table`)
- Deleting or duplicating paragraphs that anchor objects
- Any operation that changes paragraph indices (inserts, deletes)

You do NOT need to re-index after:
- Resizing images or frames (`set_image_properties`, `set_frame_properties`)
- Changing anchor/orient/crop on existing objects
- Editing text within paragraphs (`set_paragraph_text`, `replace_in_document`)

### Anti-pattern: calling list_images + list_frames on large documents

On a 50-page document with 30 images and 20 frames, `list_images` returns all 30 and `list_frames` returns all 20 — most of which you don't need. Instead:

```
# Bad: loads everything
list_images → 30 entries, most irrelevant
list_frames → 20 entries, most irrelevant

# Good: loads only what's on page 5
get_page_objects(page=5) → 3 images, 2 frames, 1 table
```

## Performance Notes

- All UNO calls run on the LibreOffice main thread (thread-safe via AsyncCallback).
- Calls that take over 30 seconds will timeout (HTTP 504).
- Opening very large documents is the slowest operation — subsequent reads are fast.
- `search_in_document` uses native LibreOffice search, not paragraph-by-paragraph scanning.
- `refresh_indexes` and `update_fields` are fast even on large documents.
