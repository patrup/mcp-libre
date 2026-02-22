"""
LibreOffice MCP Extension - MCP Server Module

This module implements an embedded MCP server that integrates with LibreOffice
via the UNO API, providing real-time document manipulation capabilities.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from .uno_bridge import UNOBridge

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LibreOfficeMCPServer:
    """Embedded MCP server for LibreOffice plugin"""
    
    def __init__(self):
        """Initialize the MCP server"""
        self.uno_bridge = UNOBridge()
        self.tools = {}
        self._register_tools()
        logger.info("LibreOffice MCP Server initialized")
    
    def _register_tools(self):
        """Register all available MCP tools"""
        
        # Document creation tools
        self.tools["create_document_live"] = {
            "description": "Create a new document in LibreOffice",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_type": {
                        "type": "string",
                        "enum": ["writer", "calc", "impress", "draw"],
                        "description": "Type of document to create",
                        "default": "writer"
                    }
                }
            },
            "handler": self.create_document_live
        }
        
        # Text manipulation tools
        self.tools["insert_text_live"] = {
            "description": "Insert text into the currently active document",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to insert"
                    },
                    "position": {
                        "type": "integer",
                        "description": "Position to insert at (optional, defaults to cursor position)"
                    }
                },
                "required": ["text"]
            },
            "handler": self.insert_text_live
        }
        
        # Document info tools
        self.tools["get_document_info_live"] = {
            "description": "Get information about the currently active document",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "handler": self.get_document_info_live
        }
        
        # Text formatting tools
        self.tools["format_text_live"] = {
            "description": "Apply formatting to selected text in active document",
            "parameters": {
                "type": "object",
                "properties": {
                    "bold": {
                        "type": "boolean",
                        "description": "Apply bold formatting"
                    },
                    "italic": {
                        "type": "boolean",
                        "description": "Apply italic formatting"
                    },
                    "underline": {
                        "type": "boolean",
                        "description": "Apply underline formatting"
                    },
                    "font_size": {
                        "type": "number",
                        "description": "Font size in points"
                    },
                    "font_name": {
                        "type": "string",
                        "description": "Font family name"
                    }
                }
            },
            "handler": self.format_text_live
        }
        
        # Document saving tools
        self.tools["save_document_live"] = {
            "description": "Save the currently active document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to save document to (optional, saves to current location if not specified)"
                    }
                }
            },
            "handler": self.save_document_live
        }
        
        # Document export tools
        self.tools["export_document_live"] = {
            "description": "Export the currently active document to a different format",
            "parameters": {
                "type": "object",
                "properties": {
                    "export_format": {
                        "type": "string",
                        "enum": ["pdf", "docx", "doc", "odt", "txt", "rtf", "html"],
                        "description": "Format to export to"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to export document to"
                    }
                },
                "required": ["export_format", "file_path"]
            },
            "handler": self.export_document_live
        }
        
        # Content reading tools
        self.tools["get_text_content_live"] = {
            "description": "Get the text content of the currently active document",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "handler": self.get_text_content_live
        }
        
        # Document list tools
        self.tools["list_open_documents"] = {
            "description": "List all currently open documents in LibreOffice",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "handler": self.list_open_documents
        }
        
        # -------------------------------------------------------
        # Context-efficient document tools (tree navigation)
        # -------------------------------------------------------

        self.tools["open_document"] = {
            "description": "Open a document by file path in LibreOffice",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "Absolute file path"},
                    "force": {"type": "boolean", "default": False,
                              "description": "Force open even if a document "
                                             "with the same name is already open"}
                },
                "required": ["file_path"]
            },
            "handler": self._h_open_document
        }

        self.tools["close_document"] = {
            "description": "Close a document by file path (no save)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "Absolute file path"}
                },
                "required": ["file_path"]
            },
            "handler": self._h_close_document
        }

        self.tools["get_page_objects"] = {
            "description": "Get images and tables on a page. "
                           "Pass page number OR locator to resolve the page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer",
                             "description": "Page number (1-based)"},
                    "locator": {"type": "string",
                                "description": "Locator to resolve page from "
                                "(e.g. paragraph:89, bookmark:_mcp_x)"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph index"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_page_objects
        }

        self.tools["get_document_tree"] = {
            "description": "Get document heading tree. Use depth to control "
                           "how many levels are returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_strategy": {
                        "type": "string",
                        "enum": ["none", "first_lines",
                                 "ai_summary_first", "full"],
                        "description": "What to show for body text "
                                       "(default: first_lines)"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Levels to return: 1=direct children, "
                                       "2=two levels, 0=unlimited (default: 1)"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_document_tree
        }

        self.tools["get_heading_children"] = {
            "description": "Get children of a heading (drill down into tree). "
                           "Use locator or heading_bookmark for stable navigation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {
                        "type": "string",
                        "description": "Unified locator (e.g. 'bookmark:_mcp_x', "
                                       "'heading:2.1', 'paragraph:5')"
                    },
                    "heading_para_index": {
                        "type": "integer",
                        "description": "Paragraph index of the heading (legacy)"
                    },
                    "heading_bookmark": {
                        "type": "string",
                        "description": "Bookmark name (legacy, use locator instead)"
                    },
                    "content_strategy": {
                        "type": "string",
                        "enum": ["none", "first_lines",
                                 "ai_summary_first", "full"],
                        "description": "default: first_lines"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Sub-levels to include (default: 1)"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_heading_children
        }

        self.tools["read_paragraphs"] = {
            "description": "Read a range of paragraphs by locator or index",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {
                        "type": "string",
                        "description": "Unified locator (e.g. 'paragraph:0', "
                                       "'page:2', 'bookmark:_mcp_x')"
                    },
                    "start_index": {"type": "integer",
                                    "description": "First paragraph index (legacy)"},
                    "count": {"type": "integer",
                              "description": "Number to read (default: 10)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_read_paragraphs
        }

        self.tools["get_paragraph_count"] = {
            "description": "Get total paragraph count",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_paragraph_count
        }

        self.tools["search_in_document"] = {
            "description": "Search text with paragraph context",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string",
                                "description": "Search string or regex"},
                    "regex": {"type": "boolean",
                              "description": "Use regex (default: false)"},
                    "case_sensitive": {"type": "boolean",
                                      "description": "default: false"},
                    "max_results": {"type": "integer",
                                    "description": "default: 20"},
                    "context_paragraphs": {
                        "type": "integer",
                        "description": "Paragraphs of context (default: 1)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["pattern"]
            },
            "handler": self._h_search_in_document
        }

        self.tools["replace_in_document"] = {
            "description": "Find and replace text (preserves formatting)",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Text to find"},
                    "replace": {"type": "string",
                                "description": "Replacement text"},
                    "regex": {"type": "boolean", "description": "default: false"},
                    "case_sensitive": {"type": "boolean",
                                      "description": "default: false"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["search", "replace"]
            },
            "handler": self._h_replace_in_document
        }

        self.tools["insert_at_paragraph"] = {
            "description": "Insert text before or after a paragraph",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {
                        "type": "string",
                        "description": "Unified locator (e.g. 'paragraph:5', "
                                       "'bookmark:_mcp_x')"
                    },
                    "paragraph_index": {"type": "integer",
                                        "description": "Target paragraph (legacy)"},
                    "text": {"type": "string", "description": "Text to insert"},
                    "position": {"type": "string", "enum": ["before", "after"],
                                 "description": "default: after"},
                    "style": {"type": "string",
                              "description": "Paragraph style for the new "
                                             "paragraph (e.g. 'Text Body', "
                                             "'Heading 1'). If omitted, "
                                             "inherits from adjacent paragraph."},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["text"]
            },
            "handler": self._h_insert_at_paragraph
        }

        self.tools["insert_paragraphs_batch"] = {
            "description": "Insert multiple paragraphs in one call. "
                           "Each item has text and optional style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {
                        "type": "string",
                        "description": "Unified locator (e.g. 'paragraph:5', "
                                       "'bookmark:_mcp_x')"
                    },
                    "paragraph_index": {"type": "integer",
                                        "description": "Target paragraph (legacy)"},
                    "paragraphs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "style": {"type": "string"}
                            },
                            "required": ["text"]
                        },
                        "description": "List of {text, style?} to insert"
                    },
                    "position": {"type": "string", "enum": ["before", "after"],
                                 "description": "default: after"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["paragraphs"]
            },
            "handler": self._h_insert_paragraphs_batch
        }

        self.tools["add_ai_summary"] = {
            "description": "Add an AI annotation/summary to a heading",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {
                        "type": "string",
                        "description": "Unified locator (e.g. 'paragraph:5', "
                                       "'heading:2.1')"
                    },
                    "para_index": {"type": "integer",
                                   "description": "Heading paragraph index (legacy)"},
                    "summary": {"type": "string",
                                "description": "Summary text"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["summary"]
            },
            "handler": self._h_add_ai_summary
        }

        self.tools["get_ai_summaries"] = {
            "description": "List all AI annotations in the document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_ai_summaries
        }

        self.tools["remove_ai_summary"] = {
            "description": "Remove an AI annotation from a heading",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {
                        "type": "string",
                        "description": "Unified locator (e.g. 'paragraph:5')"
                    },
                    "para_index": {"type": "integer",
                                   "description": "Heading paragraph index (legacy)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_remove_ai_summary
        }

        self.tools["list_sections"] = {
            "description": "List named text sections",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_sections
        }

        self.tools["read_section"] = {
            "description": "Read the content of a named section",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_name": {"type": "string",
                                     "description": "Section name"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["section_name"]
            },
            "handler": self._h_read_section
        }

        self.tools["list_bookmarks"] = {
            "description": "List all bookmarks in the document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_bookmarks
        }

        self.tools["resolve_bookmark"] = {
            "description": "Resolve a bookmark to its current paragraph index "
                           "(bookmarks are stable across edits)",
            "parameters": {
                "type": "object",
                "properties": {
                    "bookmark_name": {
                        "type": "string",
                        "description": "Bookmark name (e.g. _mcp_a1b2c3d4)"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["bookmark_name"]
            },
            "handler": self._h_resolve_bookmark
        }

        self.tools["get_page_count"] = {
            "description": "Get the document page count",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_page_count
        }

        self.tools["goto_page"] = {
            "description": "Scroll the view to a specific page",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer",
                             "description": "Page number (1-based)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["page"]
            },
            "handler": self._h_goto_page
        }

        # -------------------------------------------------------
        # Calc tools
        # -------------------------------------------------------

        self.tools["read_cells"] = {
            "description": "Read cell values from a Calc spreadsheet range",
            "parameters": {
                "type": "object",
                "properties": {
                    "range_str": {
                        "type": "string",
                        "description": "Cell range (e.g. 'A1:D10', "
                                       "'Sheet1.A1:D10', or 'B3')"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["range_str"]
            },
            "handler": self._h_read_cells
        }

        self.tools["write_cell"] = {
            "description": "Write a value to a Calc spreadsheet cell",
            "parameters": {
                "type": "object",
                "properties": {
                    "cell": {
                        "type": "string",
                        "description": "Cell address (e.g. 'B3', 'Sheet1.B3')"
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to write"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["cell", "value"]
            },
            "handler": self._h_write_cell
        }

        self.tools["list_sheets"] = {
            "description": "List all sheets in a Calc spreadsheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_sheets
        }

        self.tools["get_sheet_info"] = {
            "description": "Get info about a Calc sheet (used range, dimensions)",
            "parameters": {
                "type": "object",
                "properties": {
                    "sheet_name": {
                        "type": "string",
                        "description": "Sheet name (optional, defaults to active)"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_sheet_info
        }

        # -------------------------------------------------------
        # Impress tools
        # -------------------------------------------------------

        self.tools["list_slides"] = {
            "description": "List all slides in an Impress presentation",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_slides
        }

        self.tools["read_slide_text"] = {
            "description": "Get all text from a slide and its notes page",
            "parameters": {
                "type": "object",
                "properties": {
                    "slide_index": {
                        "type": "integer",
                        "description": "Zero-based slide index"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["slide_index"]
            },
            "handler": self._h_read_slide_text
        }

        self.tools["get_presentation_info"] = {
            "description": "Get presentation metadata (slide count, dimensions, masters)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_presentation_info
        }

        # -------------------------------------------------------
        # Document maintenance tools
        # -------------------------------------------------------

        self.tools["refresh_indexes"] = {
            "description": "Refresh all document indexes (TOC, alphabetical, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_refresh_indexes
        }

        self.tools["update_fields"] = {
            "description": "Refresh all text fields (dates, page numbers, cross-refs)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_update_fields
        }

        self.tools["delete_paragraph"] = {
            "description": "Delete a paragraph by index or locator",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {"type": "string",
                                "description": "Unified locator (e.g. 'paragraph:5')"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph index (legacy)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_delete_paragraph
        }

        self.tools["set_paragraph_text"] = {
            "description": "Replace the entire text of a paragraph (preserves style)",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {"type": "string",
                                "description": "Unified locator"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph index (legacy)"},
                    "text": {"type": "string",
                             "description": "New text content"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["text"]
            },
            "handler": self._h_set_paragraph_text
        }

        self.tools["set_paragraph_style"] = {
            "description": "Set the paragraph style (e.g. 'Heading 1', 'Text Body')",
            "parameters": {
                "type": "object",
                "properties": {
                    "style_name": {"type": "string",
                                   "description": "Paragraph style name"},
                    "locator": {"type": "string",
                                "description": "Unified locator"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph index (legacy)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["style_name"]
            },
            "handler": self._h_set_paragraph_style
        }

        self.tools["duplicate_paragraph"] = {
            "description": "Duplicate a paragraph (with style) after itself. "
                           "Use count>1 to duplicate a heading+body block.",
            "parameters": {
                "type": "object",
                "properties": {
                    "locator": {"type": "string",
                                "description": "Unified locator"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph index (legacy)"},
                    "count": {"type": "integer",
                              "description": "Number of consecutive paragraphs "
                                             "to duplicate (default: 1)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_duplicate_paragraph
        }

        self.tools["get_document_properties"] = {
            "description": "Read document metadata (title, author, subject, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_document_properties
        }

        self.tools["set_document_properties"] = {
            "description": "Update document metadata (title, author, subject, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "keywords": {"type": "array",
                                 "items": {"type": "string"}},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_set_document_properties
        }

        self.tools["save_document_as"] = {
            "description": "Save/duplicate a document under a new name",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_path": {"type": "string",
                                    "description": "New file path to save to"},
                    "file_path": {"type": "string",
                                  "description": "Source document (optional, "
                                                 "uses active doc)"}
                },
                "required": ["target_path"]
            },
            "handler": self._h_save_document_as
        }

        # -------------------------------------------------------
        # Document Protection
        # -------------------------------------------------------

        self.tools["set_document_protection"] = {
            "description": "Lock/unlock the document for human editing. "
                           "When locked, UI is read-only but UNO/MCP can "
                           "still edit. No password, just a toggle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean",
                                "description": "True to lock (human can't edit), "
                                               "False to unlock"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["enabled"]
            },
            "handler": self._h_set_document_protection
        }

        # -------------------------------------------------------
        # Comments
        # -------------------------------------------------------

        self.tools["list_comments"] = {
            "description": "List all comments/annotations in the document "
                           "(excludes MCP-AI summaries)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_comments
        }

        self.tools["add_comment"] = {
            "description": "Add a comment at a paragraph",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string",
                                "description": "Comment text"},
                    "author": {"type": "string",
                               "description": "Author name (default: AI Agent)"},
                    "locator": {"type": "string",
                                "description": "Unified locator"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph index (legacy)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["content"]
            },
            "handler": self._h_add_comment
        }

        self.tools["resolve_comment"] = {
            "description": "Resolve a comment with an optional reason. "
                           "Adds a reply then marks as resolved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comment_name": {"type": "string",
                                     "description": "Name/ID of the comment"},
                    "resolution": {"type": "string",
                                   "description": "Reason for resolution"},
                    "author": {"type": "string",
                               "description": "Author name (default: AI Agent)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["comment_name"]
            },
            "handler": self._h_resolve_comment
        }

        self.tools["delete_comment"] = {
            "description": "Delete a comment and its replies",
            "parameters": {
                "type": "object",
                "properties": {
                    "comment_name": {"type": "string",
                                     "description": "Name/ID of the comment"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["comment_name"]
            },
            "handler": self._h_delete_comment
        }

        # -------------------------------------------------------
        # Track Changes
        # -------------------------------------------------------

        self.tools["set_track_changes"] = {
            "description": "Enable or disable change tracking (record changes)",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean",
                                "description": "True to enable, False to disable"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["enabled"]
            },
            "handler": self._h_set_track_changes
        }

        self.tools["get_tracked_changes"] = {
            "description": "List all tracked changes (redlines) in the document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_get_tracked_changes
        }

        self.tools["accept_all_changes"] = {
            "description": "Accept all tracked changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_accept_all_changes
        }

        self.tools["reject_all_changes"] = {
            "description": "Reject all tracked changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_reject_all_changes
        }

        # -------------------------------------------------------
        # Styles
        # -------------------------------------------------------

        self.tools["list_styles"] = {
            "description": "List available styles in a family "
                           "(ParagraphStyles, CharacterStyles, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "family": {"type": "string",
                               "description": "Style family: ParagraphStyles, "
                                              "CharacterStyles, PageStyles, "
                                              "FrameStyles, NumberingStyles "
                                              "(default: ParagraphStyles)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_styles
        }

        self.tools["get_style_info"] = {
            "description": "Get detailed properties of a style",
            "parameters": {
                "type": "object",
                "properties": {
                    "style_name": {"type": "string",
                                   "description": "Name of the style"},
                    "family": {"type": "string",
                               "description": "Style family "
                                              "(default: ParagraphStyles)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["style_name"]
            },
            "handler": self._h_get_style_info
        }

        # -------------------------------------------------------
        # Writer Tables
        # -------------------------------------------------------

        self.tools["list_tables"] = {
            "description": "List all text tables in a Writer document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_tables
        }

        self.tools["read_table"] = {
            "description": "Read all cell contents from a Writer table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string",
                                   "description": "Name of the table"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["table_name"]
            },
            "handler": self._h_read_table
        }

        self.tools["write_table_cell"] = {
            "description": "Write to a cell in a Writer table (e.g. cell='B2')",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string",
                                   "description": "Name of the table"},
                    "cell": {"type": "string",
                             "description": "Cell address (e.g. 'A1', 'B3')"},
                    "value": {"type": "string",
                              "description": "Value to write"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["table_name", "cell", "value"]
            },
            "handler": self._h_write_table_cell
        }

        self.tools["create_table"] = {
            "description": "Create a new table at a paragraph position",
            "parameters": {
                "type": "object",
                "properties": {
                    "rows": {"type": "integer",
                             "description": "Number of rows"},
                    "cols": {"type": "integer",
                             "description": "Number of columns"},
                    "locator": {"type": "string",
                                "description": "Unified locator"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph index (legacy)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["rows", "cols"]
            },
            "handler": self._h_create_table
        }

        # -------------------------------------------------------
        # Images
        # -------------------------------------------------------

        self.tools["list_images"] = {
            "description": "List all images/graphic objects in the document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_images
        }

        self.tools["get_image_info"] = {
            "description": "Get detailed info about a specific image",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_name": {"type": "string",
                                   "description": "Name of the image/graphic object"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["image_name"]
            },
            "handler": self._h_get_image_info
        }

        self.tools["set_image_properties"] = {
            "description": "Resize, reposition, crop, or update "
                           "caption/alt-text for an image",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_name": {"type": "string",
                                   "description": "Name of the image"},
                    "width_mm": {"type": "integer",
                                 "description": "New width in mm"},
                    "height_mm": {"type": "integer",
                                  "description": "New height in mm"},
                    "title": {"type": "string",
                              "description": "Image title (caption)"},
                    "description": {"type": "string",
                                    "description": "Alt-text / description"},
                    "anchor_type": {
                        "type": "integer",
                        "description": "0=AT_PARAGRAPH, 1=AS_CHARACTER, "
                                       "2=AT_PAGE, 3=AT_FRAME, 4=AT_CHARACTER"
                    },
                    "hori_orient": {
                        "type": "integer",
                        "description": "0=NONE, 1=RIGHT, 2=CENTER, 3=LEFT"
                    },
                    "vert_orient": {
                        "type": "integer",
                        "description": "0=NONE, 1=TOP, 2=CENTER, 3=BOTTOM"
                    },
                    "hori_orient_relation": {
                        "type": "integer",
                        "description": "0=PARAGRAPH, 1=FRAME, 2=PAGE..."
                    },
                    "vert_orient_relation": {
                        "type": "integer",
                        "description": "0=PARAGRAPH, 1=FRAME, 2=PAGE..."
                    },
                    "crop_top_mm": {"type": "integer",
                                    "description": "Crop from top in mm"},
                    "crop_bottom_mm": {"type": "integer",
                                       "description": "Crop from bottom in mm"},
                    "crop_left_mm": {"type": "integer",
                                     "description": "Crop from left in mm"},
                    "crop_right_mm": {"type": "integer",
                                      "description": "Crop from right in mm"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["image_name"]
            },
            "handler": self._h_set_image_properties
        }

        self.tools["insert_image"] = {
            "description": "Insert an image from a file path into the "
                           "document, optionally inside a caption frame",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string",
                                   "description": "Absolute path to the "
                                                  "image file"},
                    "paragraph_index": {"type": "integer",
                                        "description": "Paragraph to insert "
                                                       "after (legacy)"},
                    "locator": {"type": "string",
                                "description": "Unified locator"},
                    "caption": {"type": "string",
                                "description": "Caption text (optional)"},
                    "with_frame": {"type": "boolean",
                                   "description": "Wrap in a text frame "
                                                  "(default: true)"},
                    "width_mm": {"type": "integer",
                                 "description": "Width in mm (default: 80)"},
                    "height_mm": {"type": "integer",
                                  "description": "Height in mm (default: 80)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["image_path"]
            },
            "handler": self._h_insert_image
        }

        self.tools["delete_image"] = {
            "description": "Delete an image. By default also removes its "
                           "parent frame. Set remove_frame=false to keep "
                           "the frame (e.g. before inserting a replacement).",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_name": {"type": "string",
                                   "description": "Name of the image to "
                                                  "delete"},
                    "remove_frame": {"type": "boolean",
                                     "description": "Also remove parent "
                                                    "frame (default: true)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["image_name"]
            },
            "handler": self._h_delete_image
        }

        self.tools["replace_image"] = {
            "description": "Replace an image's source file, keeping its "
                           "frame, position, and caption intact",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_name": {"type": "string",
                                   "description": "Name of the image to "
                                                  "replace"},
                    "new_image_path": {"type": "string",
                                       "description": "Path to the new "
                                                      "image file"},
                    "width_mm": {"type": "integer",
                                 "description": "New width in mm (optional)"},
                    "height_mm": {"type": "integer",
                                  "description": "New height in mm "
                                                 "(optional)"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["image_name", "new_image_path"]
            },
            "handler": self._h_replace_image
        }

        # -------------------------------------------------------
        # Text Frames
        # -------------------------------------------------------

        self.tools["list_text_frames"] = {
            "description": "List all text frames in the document",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                }
            },
            "handler": self._h_list_text_frames
        }

        self.tools["get_text_frame_info"] = {
            "description": "Get detailed info about a specific text frame",
            "parameters": {
                "type": "object",
                "properties": {
                    "frame_name": {"type": "string",
                                   "description": "Name of the text frame"},
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["frame_name"]
            },
            "handler": self._h_get_text_frame_info
        }

        self.tools["set_text_frame_properties"] = {
            "description": "Modify text frame properties (size, position, "
                           "wrap, anchor)",
            "parameters": {
                "type": "object",
                "properties": {
                    "frame_name": {"type": "string",
                                   "description": "Name of the text frame"},
                    "width_mm": {"type": "integer",
                                 "description": "New width in mm"},
                    "height_mm": {"type": "integer",
                                  "description": "New height in mm"},
                    "anchor_type": {
                        "type": "integer",
                        "description": "0=AT_PARAGRAPH, 1=AS_CHARACTER, "
                                       "2=AT_PAGE, 3=AT_FRAME, 4=AT_CHARACTER"
                    },
                    "hori_orient": {
                        "type": "integer",
                        "description": "0=NONE, 1=RIGHT, 2=CENTER, 3=LEFT"
                    },
                    "vert_orient": {
                        "type": "integer",
                        "description": "0=NONE, 1=TOP, 2=CENTER, 3=BOTTOM"
                    },
                    "hori_pos_mm": {
                        "type": "integer",
                        "description": "Horizontal position in mm "
                                       "(when hori_orient=NONE)"
                    },
                    "vert_pos_mm": {
                        "type": "integer",
                        "description": "Vertical position in mm "
                                       "(when vert_orient=NONE)"
                    },
                    "wrap": {
                        "type": "integer",
                        "description": "0=NONE, 1=COLUMN, 2=PARALLEL, "
                                       "3=DYNAMIC, 4=THROUGH"
                    },
                    "paragraph_index": {
                        "type": "integer",
                        "description": "Move anchor to this paragraph index"
                    },
                    "file_path": {"type": "string",
                                  "description": "File path (optional)"}
                },
                "required": ["frame_name"]
            },
            "handler": self._h_set_text_frame_properties
        }

        # -------------------------------------------------------
        # Recent Documents
        # -------------------------------------------------------

        self.tools["get_recent_documents"] = {
            "description": "Get the list of recently opened documents "
                           "from LibreOffice history",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_count": {"type": "integer",
                                  "description": "Max documents to return "
                                                 "(default: 20)"}
                }
            },
            "handler": self._h_get_recent_documents
        }

        logger.info(f"Registered {len(self.tools)} MCP tools")
    
    def execute_tool_sync(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool (synchronous).

        This is the primary entry point used by the HTTP handler via
        MainThreadExecutor — it runs on the VCL main thread.
        """
        try:
            if tool_name not in self.tools:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                    "available_tools": list(self.tools.keys())
                }

            tool = self.tools[tool_name]
            handler = tool["handler"]

            result = handler(**parameters)

            logger.info(f"Executed tool '{tool_name}' successfully")
            return result

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "parameters": parameters
            }
    
    def get_tool_list(self) -> List[Dict[str, Any]]:
        """Get list of available tools with their descriptions"""
        return [
            {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for name, tool in self.tools.items()
        ]
    
    # Tool handler methods
    
    def create_document_live(self, doc_type: str = "writer") -> Dict[str, Any]:
        """Create a new document in LibreOffice"""
        try:
            doc = self.uno_bridge.create_document(doc_type)
            doc_info = self.uno_bridge.get_document_info(doc)
            
            return {
                "success": True,
                "message": f"Created new {doc_type} document",
                "document_info": doc_info
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def insert_text_live(self, text: str, position: Optional[int] = None) -> Dict[str, Any]:
        """Insert text into the currently active document"""
        return self.uno_bridge.insert_text(text, position)
    
    def get_document_info_live(self) -> Dict[str, Any]:
        """Get information about the currently active document"""
        doc_info = self.uno_bridge.get_document_info()
        if "error" in doc_info:
            return {"success": False, **doc_info}
        else:
            return {"success": True, "document_info": doc_info}
    
    def format_text_live(self, **formatting) -> Dict[str, Any]:
        """Apply formatting to selected text"""
        return self.uno_bridge.format_text(formatting)
    
    def save_document_live(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Save the currently active document"""
        return self.uno_bridge.save_document(file_path=file_path)
    
    def export_document_live(self, export_format: str, file_path: str) -> Dict[str, Any]:
        """Export the currently active document"""
        return self.uno_bridge.export_document(export_format, file_path)
    
    def get_text_content_live(self) -> Dict[str, Any]:
        """Get text content of the currently active document"""
        return self.uno_bridge.get_text_content()
    
    # -- Context-efficient tool handlers --

    def _h_open_document(self, file_path: str,
                         force: bool = False) -> Dict[str, Any]:
        result = self.uno_bridge.open_document(file_path, force=force)
        return {k: v for k, v in result.items() if k != "doc"}

    def _h_close_document(self, file_path: str) -> Dict[str, Any]:
        return self.uno_bridge.close_document(file_path)

    def _h_get_page_objects(self, page: int = None,
                             locator: str = None,
                             paragraph_index: int = None,
                             file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_page_objects(
            page, locator, paragraph_index, file_path)

    def _h_get_document_tree(self, content_strategy: str = "first_lines",
                             depth: int = 1,
                             file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_document_tree(
            content_strategy, depth, file_path)

    def _h_get_heading_children(self, heading_para_index: int = None,
                                heading_bookmark: str = None,
                                locator: str = None,
                                content_strategy: str = "first_lines",
                                depth: int = 1,
                                file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_heading_children(
            heading_para_index, heading_bookmark, locator,
            content_strategy, depth, file_path)

    def _h_read_paragraphs(self, start_index: int = None,
                           locator: str = None,
                           count: int = 10,
                           file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.read_paragraphs(
            start_index, count, locator, file_path)

    def _h_get_paragraph_count(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_paragraph_count(file_path)

    def _h_search_in_document(self, pattern: str, regex: bool = False,
                              case_sensitive: bool = False,
                              max_results: int = 20,
                              context_paragraphs: int = 1,
                              file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.search_document(
            pattern, regex, case_sensitive, max_results,
            context_paragraphs, file_path)

    def _h_replace_in_document(self, search: str, replace: str,
                               regex: bool = False,
                               case_sensitive: bool = False,
                               file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.replace_in_document(
            search, replace, regex, case_sensitive, file_path)

    def _h_insert_at_paragraph(self, paragraph_index: int = None,
                               text: str = "",
                               position: str = "after",
                               locator: str = None,
                               style: str = None,
                               file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.insert_at_paragraph(
            paragraph_index, text, position, locator, style, file_path)

    def _h_insert_paragraphs_batch(self, paragraphs: list = None,
                                    paragraph_index: int = None,
                                    position: str = "after",
                                    locator: str = None,
                                    file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.insert_paragraphs_batch(
            paragraphs or [], paragraph_index, position, locator, file_path)

    def _h_add_ai_summary(self, para_index: int = None,
                           summary: str = "",
                           locator: str = None,
                           file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.add_ai_summary(
            para_index, summary, locator, file_path)

    def _h_get_ai_summaries(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_ai_summaries(file_path)

    def _h_remove_ai_summary(self, para_index: int = None,
                              locator: str = None,
                              file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.remove_ai_summary(
            para_index, locator, file_path)

    def _h_list_sections(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_sections(file_path)

    def _h_read_section(self, section_name: str,
                         file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.read_section(section_name, file_path)

    def _h_list_bookmarks(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_bookmarks(file_path)

    def _h_resolve_bookmark(self, bookmark_name: str,
                             file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.resolve_bookmark(bookmark_name, file_path)

    def _h_get_page_count(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_page_count(file_path)

    def _h_goto_page(self, page: int,
                      file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.goto_page(page, file_path)

    # -- Calc handlers --

    def _h_read_cells(self, range_str: str,
                      file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.read_cells(range_str, file_path)

    def _h_write_cell(self, cell: str, value: str,
                      file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.write_cell(cell, value, file_path)

    def _h_list_sheets(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_sheets(file_path)

    def _h_get_sheet_info(self, sheet_name: str = None,
                          file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_sheet_info(sheet_name, file_path)

    # -- Impress handlers --

    def _h_list_slides(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_slides(file_path)

    def _h_read_slide_text(self, slide_index: int,
                           file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.read_slide_text(slide_index, file_path)

    def _h_get_presentation_info(self,
                                 file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_presentation_info(file_path)

    # -- Document maintenance handlers --

    def _h_refresh_indexes(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.refresh_indexes(file_path)

    def _h_update_fields(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.update_fields(file_path)

    def _h_delete_paragraph(self, paragraph_index: int = None,
                             locator: str = None,
                             file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.delete_paragraph(
            paragraph_index, locator, file_path)

    def _h_set_paragraph_text(self, paragraph_index: int = None,
                               text: str = "",
                               locator: str = None,
                               file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.set_paragraph_text(
            paragraph_index, text, locator, file_path)

    def _h_set_paragraph_style(self, style_name: str,
                                paragraph_index: int = None,
                                locator: str = None,
                                file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.set_paragraph_style(
            style_name, paragraph_index, locator, file_path)

    def _h_duplicate_paragraph(self, paragraph_index: int = None,
                                locator: str = None,
                                count: int = 1,
                                file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.duplicate_paragraph(
            paragraph_index, locator, count, file_path)

    def _h_get_document_properties(self,
                                    file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_document_properties(file_path)

    def _h_set_document_properties(self, title: str = None,
                                    author: str = None,
                                    subject: str = None,
                                    description: str = None,
                                    keywords: list = None,
                                    file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.set_document_properties(
            title, author, subject, description, keywords, file_path)

    def _h_save_document_as(self, target_path: str,
                             file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.save_document_as(target_path, file_path)

    # -- Document Protection handler --

    def _h_set_document_protection(self, enabled: bool,
                                    file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.set_document_protection(enabled, file_path)

    # -- Comments handlers --

    def _h_list_comments(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_comments(file_path)

    def _h_add_comment(self, content: str, author: str = "AI Agent",
                        paragraph_index: int = None,
                        locator: str = None,
                        file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.add_comment(
            content, author, paragraph_index, locator, file_path)

    def _h_resolve_comment(self, comment_name: str,
                            resolution: str = "",
                            author: str = "AI Agent",
                            file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.resolve_comment(
            comment_name, resolution, author, file_path)

    def _h_delete_comment(self, comment_name: str,
                           file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.delete_comment(comment_name, file_path)

    # -- Track Changes handlers --

    def _h_set_track_changes(self, enabled: bool,
                              file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.set_track_changes(enabled, file_path)

    def _h_get_tracked_changes(self,
                                file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_tracked_changes(file_path)

    def _h_accept_all_changes(self,
                               file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.accept_all_changes(file_path)

    def _h_reject_all_changes(self,
                               file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.reject_all_changes(file_path)

    # -- Styles handlers --

    def _h_list_styles(self, family: str = "ParagraphStyles",
                        file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_styles(family, file_path)

    def _h_get_style_info(self, style_name: str,
                           family: str = "ParagraphStyles",
                           file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_style_info(
            style_name, family, file_path)

    # -- Writer Tables handlers --

    def _h_list_tables(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_tables(file_path)

    def _h_read_table(self, table_name: str,
                       file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.read_table(table_name, file_path)

    def _h_write_table_cell(self, table_name: str, cell: str,
                             value: str,
                             file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.write_table_cell(
            table_name, cell, value, file_path)

    def _h_create_table(self, rows: int, cols: int,
                         paragraph_index: int = None,
                         locator: str = None,
                         file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.create_table(
            rows, cols, paragraph_index, locator, file_path)

    # -- Images handlers --

    def _h_list_images(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_images(file_path)

    def _h_get_image_info(self, image_name: str,
                           file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_image_info(image_name, file_path)

    def _h_set_image_properties(self, image_name: str,
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
        return self.uno_bridge.set_image_properties(
            image_name, width_mm, height_mm, title, description,
            anchor_type, hori_orient, vert_orient,
            hori_orient_relation, vert_orient_relation,
            crop_top_mm, crop_bottom_mm, crop_left_mm, crop_right_mm,
            file_path)

    def _h_insert_image(self, image_path: str,
                         paragraph_index: int = None,
                         locator: str = None,
                         caption: str = None,
                         with_frame: bool = True,
                         width_mm: int = None,
                         height_mm: int = None,
                         file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.insert_image(
            image_path, paragraph_index, locator, caption,
            with_frame, width_mm, height_mm, file_path)

    def _h_delete_image(self, image_name: str,
                         remove_frame: bool = True,
                         file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.delete_image(
            image_name, remove_frame, file_path)

    def _h_replace_image(self, image_name: str,
                          new_image_path: str,
                          width_mm: int = None,
                          height_mm: int = None,
                          file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.replace_image(
            image_name, new_image_path, width_mm, height_mm, file_path)

    # -- Text Frames handlers --

    def _h_list_text_frames(self, file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.list_text_frames(file_path)

    def _h_get_text_frame_info(self, frame_name: str,
                                file_path: str = None) -> Dict[str, Any]:
        return self.uno_bridge.get_text_frame_info(frame_name, file_path)

    def _h_set_text_frame_properties(self, frame_name: str,
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
        return self.uno_bridge.set_text_frame_properties(
            frame_name, width_mm, height_mm, anchor_type, hori_orient,
            vert_orient, hori_pos_mm, vert_pos_mm, wrap, paragraph_index,
            file_path)

    # -- Recent Documents handler --

    def _h_get_recent_documents(self,
                                 max_count: int = 20) -> Dict[str, Any]:
        return self.uno_bridge.get_recent_documents(max_count)

    def list_open_documents(self) -> Dict[str, Any]:
        """List all open documents in LibreOffice"""
        try:
            desktop = self.uno_bridge.desktop
            documents = []
            
            # Get all open documents
            frames = desktop.getFrames()
            for i in range(frames.getCount()):
                frame = frames.getByIndex(i)
                controller = frame.getController()
                if controller:
                    doc = controller.getModel()
                    if doc:
                        doc_info = self.uno_bridge.get_document_info(doc)
                        documents.append(doc_info)
            
            return {
                "success": True,
                "documents": documents,
                "count": len(documents)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
mcp_server = None

def get_mcp_server() -> LibreOfficeMCPServer:
    """Get or create the global MCP server instance"""
    global mcp_server
    if mcp_server is None:
        mcp_server = LibreOfficeMCPServer()
    return mcp_server
