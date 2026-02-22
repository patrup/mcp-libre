"""
GuiBackend — delegates to the LibreOffice UNO plugin HTTP API.
"""

import csv
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .base import DocumentBackend
from ..models import (
    DocumentInfo, TextContent, ConversionResult, SpreadsheetData,
    get_document_info,
)


class GuiBackend(DocumentBackend):
    """Backend that talks to the running LibreOffice instance via HTTP plugin."""

    def __init__(self, call_plugin: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
        self._call = call_plugin

    # -- create_document ----------------------------------------------------
    def create_document(self, path: str, doc_type: str, content: str) -> DocumentInfo:
        FORMAT_MAP = {
            "writer": ".odt", "calc": ".ods",
            "impress": ".odp", "draw": ".odg",
        }
        if doc_type not in FORMAT_MAP:
            raise ValueError(
                f"Unsupported document type: {doc_type}. "
                f"Use: {list(FORMAT_MAP.keys())}")

        path_obj = Path(path)
        if not path_obj.suffix:
            path_obj = Path(str(path_obj) + FORMAT_MAP[doc_type])
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        self._call("create_document_live", {"doc_type": doc_type})
        if content and doc_type == "writer":
            self._call("insert_text_live", {"text": content})
        self._call("save_document_live",
                    {"file_path": str(path_obj.absolute())})
        return get_document_info(str(path_obj))

    # -- read_document_text -------------------------------------------------
    def read_document_text(self, path: str) -> TextContent:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        self._call("open_document",
                    {"file_path": str(path_obj.absolute())})
        result = self._call("get_text_content_live", {})
        txt = result.get("content", "")
        return TextContent(
            content=txt,
            word_count=len(txt.split()),
            char_count=len(txt),
            page_count=result.get("page_count"),
        )

    # -- convert_document ---------------------------------------------------
    def convert_document(self, source_path: str, target_path: str,
                         target_format: str) -> ConversionResult:
        source = Path(source_path)
        target = Path(target_path)

        if not source.exists():
            return ConversionResult(
                source_path=source_path, target_path=target_path,
                source_format=source.suffix.lower().lstrip('.'),
                target_format=target_format, success=False,
                error_message=f"Source file not found: {source_path}")

        target.parent.mkdir(parents=True, exist_ok=True)
        self._call("open_document",
                    {"file_path": str(source.absolute())})
        export_result = self._call("export_document_live", {
            "export_format": target_format,
            "file_path": str(target.absolute()),
        })
        success = export_result.get("success", False) or target.exists()
        return ConversionResult(
            source_path=source_path, target_path=str(target),
            source_format=source.suffix.lower().lstrip('.'),
            target_format=target_format, success=success,
            error_message=None if success else export_result.get(
                "error", "Export failed"))

    # -- read_spreadsheet_data ----------------------------------------------
    def read_spreadsheet_data(self, path: str, sheet_name: Optional[str],
                              max_rows: int) -> SpreadsheetData:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Spreadsheet not found: {path}")

        self._call("open_document",
                    {"file_path": str(path_obj.absolute())})
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = str(Path(tmp_dir) / (path_obj.stem + ".csv"))
            self._call("export_document_live", {
                "export_format": "csv", "file_path": csv_path})
            csv_file = Path(csv_path)
            if not csv_file.exists():
                raise RuntimeError("Failed to export spreadsheet to CSV")
            data: List[List[str]] = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    data.append(row)
        row_count = len(data)
        col_count = max((len(r) for r in data), default=0)
        return SpreadsheetData(
            sheet_name=sheet_name or "Sheet1",
            data=data, row_count=row_count, col_count=col_count)

    # -- insert_text --------------------------------------------------------
    def insert_text(self, path: str, text: str, position: str) -> DocumentInfo:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        self._call("open_document",
                    {"file_path": str(path_obj.absolute())})
        result = self._call("get_text_content_live", {})
        existing = result.get("content", "")

        if position == "start":
            new_content = text + "\n" + existing
        elif position == "end":
            new_content = existing + "\n" + text
        elif position == "replace":
            new_content = text
        else:
            raise ValueError("Position must be 'start', 'end', or 'replace'")

        # Write back via headless helper then reopen in GUI
        from .headless import _create_minimal_odt
        ext = path_obj.suffix.lower()
        if ext == '.odt':
            _create_minimal_odt(path_obj, new_content)
        else:
            with open(path_obj, 'w', encoding='utf-8') as f:
                f.write(new_content)
        self._call("open_document",
                    {"file_path": str(path_obj.absolute())})
        return get_document_info(str(path_obj))

    # -- open_document ------------------------------------------------------
    def open_document(self, path: str, readonly: bool,
                      force: bool = False) -> Dict[str, Any]:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        result = self._call("open_document",
                             {"file_path": str(path_obj.absolute()),
                              "force": force})
        resp = {
            "success": result.get("success", True),
            "already_open": result.get("already_open", False),
            "message": f"Opened {path_obj.name} in LibreOffice",
            "path": str(path_obj.absolute()),
            "readonly": readonly,
            "note": "Document opened in running LibreOffice instance.",
        }
        if result.get("warning"):
            resp["warning"] = result["warning"]
        return resp

    # -- refresh_document ---------------------------------------------------
    def refresh_document(self, path: str) -> Dict[str, Any]:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        self._call("open_document",
                    {"file_path": str(path_obj.absolute())})
        return {
            "success": True,
            "message": f"Refreshed {path_obj.name} in LibreOffice",
            "path": str(path_obj.absolute()),
        }
