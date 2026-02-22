"""
HeadlessBackend — drives LibreOffice via subprocess (soffice --headless).
"""

import csv
import html
import os
import platform
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import DocumentBackend
from ..models import (
    DocumentInfo, TextContent, ConversionResult, SpreadsheetData,
    get_document_info,
)

# ---------------------------------------------------------------------------
# LibreOffice executable discovery (cached)
# ---------------------------------------------------------------------------

_libreoffice_exe: Optional[str] = None


def _find_libreoffice_executable() -> str:
    if platform.system() == "Windows":
        candidates = []
        for prog_dir in [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        ]:
            if prog_dir:
                candidates.append(
                    os.path.join(prog_dir, "LibreOffice", "program", "soffice.exe"))
        for name in ['soffice', 'soffice.exe', 'libreoffice', 'loffice']:
            found = shutil.which(name)
            if found:
                return found
        for path in candidates:
            if os.path.isfile(path):
                return path
        return "soffice"
    else:
        for name in ['libreoffice', 'loffice', 'soffice']:
            found = shutil.which(name)
            if found:
                return found
        return "libreoffice"


def _get_libreoffice_exe() -> str:
    global _libreoffice_exe
    if _libreoffice_exe is None:
        _libreoffice_exe = _find_libreoffice_executable()
    return _libreoffice_exe


def _is_libreoffice_running() -> bool:
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq soffice.bin", "/NH"],
                capture_output=True, text=True, timeout=5)
            return "soffice.bin" in result.stdout
        else:
            result = subprocess.run(
                ["pgrep", "-x", "soffice.bin"],
                capture_output=True, timeout=5)
            return result.returncode == 0
    except Exception:
        return False


def _run_libreoffice_command(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    executable = _get_libreoffice_exe()
    try:
        cmd = [executable] + args
        kwargs: Dict[str, Any] = {}
        if platform.system() == "Windows":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            kwargs['startupinfo'] = si
        return subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, check=False, **kwargs)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"LibreOffice executable not found at '{executable}'. "
            "Please install LibreOffice and ensure it is in your PATH.\n"
            "Windows: run install.ps1 or add LibreOffice\\program to PATH.")
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"LibreOffice command timed out after {timeout} seconds")


# ---------------------------------------------------------------------------
# ODT helpers
# ---------------------------------------------------------------------------

def _extract_text_from_odt(file_path: str) -> str:
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            content_xml = zf.read('content.xml').decode('utf-8')
            root = ET.fromstring(content_xml)
            parts: List[str] = []
            for elem in root.iter():
                if elem.text:
                    parts.append(elem.text)
                if elem.tail:
                    parts.append(elem.tail)
            return ' '.join(parts).strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from ODT: {e}")


def _create_minimal_odt(path: Path, content: str) -> None:
    escaped = html.escape(content)
    paragraphs = escaped.split('\n')
    text_paragraphs = []
    for para in paragraphs:
        if para.strip():
            text_paragraphs.append(
                f'   <text:p text:style-name="Standard">{para}</text:p>')
        else:
            text_paragraphs.append(
                '   <text:p text:style-name="Standard"/>')
    text_content = '\n'.join(text_paragraphs)

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('mimetype',
                     'application/vnd.oasis.opendocument.text',
                     compress_type=zipfile.ZIP_STORED)
        zf.writestr('META-INF/manifest.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>''')
        zf.writestr('content.xml', f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">
 <office:scripts/>
 <office:font-face-decls/>
 <office:automatic-styles/>
 <office:body>
  <office:text>
{text_content}
  </office:text>
 </office:body>
</office:document-content>''')
        zf.writestr('styles.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">
 <office:font-face-decls/>
 <office:styles>
  <style:default-style style:family="paragraph">
   <style:paragraph-properties fo:hyphenation-ladder-count="no-limit"/>
   <style:text-properties style:tab-stop-distance="0.5in"/>
  </style:default-style>
  <style:style style:name="Standard" style:family="paragraph" style:class="text"/>
 </office:styles>
 <office:automatic-styles/>
 <office:master-styles/>
</office:document-styles>''')
        zf.writestr('meta.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" office:version="1.2">
 <office:meta>
  <meta:generator>LibreOffice MCP Server</meta:generator>
 </office:meta>
</office:document-meta>''')


# ---------------------------------------------------------------------------
# HeadlessBackend
# ---------------------------------------------------------------------------

class HeadlessBackend(DocumentBackend):

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

        if doc_type == "writer" and content:
            with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                result = _run_libreoffice_command([
                    '--headless', '--convert-to', 'odt',
                    '--outdir', str(path_obj.parent), tmp_path])
                converted = path_obj.parent / f"{Path(tmp_path).stem}.odt"
                if converted.exists():
                    converted.rename(path_obj)
                else:
                    _create_minimal_odt(path_obj, content)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            if doc_type == "writer":
                _create_minimal_odt(path_obj, "")
            else:
                path_obj.touch()

        return get_document_info(str(path_obj))

    # -- read_document_text -------------------------------------------------
    def read_document_text(self, path: str) -> TextContent:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            _run_libreoffice_command([
                '--headless', '--convert-to', 'txt',
                '--outdir', tmp_dir, str(path_obj)])

            tmp_path = Path(tmp_dir)
            txt_file = None
            for name in [path_obj.stem + '.txt', path_obj.name + '.txt']:
                candidate = tmp_path / name
                if candidate.exists():
                    txt_file = candidate
                    break
            if not txt_file:
                txt_files = list(tmp_path.glob('*.txt'))
                if txt_files:
                    txt_file = txt_files[0]

            if txt_file and txt_file.exists():
                content = txt_file.read_text(encoding='utf-8', errors='ignore')
            elif path_obj.suffix.lower() == '.odt':
                content = _extract_text_from_odt(str(path_obj))
            else:
                try:
                    content = path_obj.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    raise RuntimeError(
                        f"Could not extract text from {path_obj.name}")

        return TextContent(
            content=content,
            word_count=len(content.split()),
            char_count=len(content),
            page_count=None,
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
        try:
            result = _run_libreoffice_command([
                '--headless', '--convert-to', target_format,
                '--outdir', str(target.parent), str(source)])
            expected = target.parent / f"{source.stem}.{target_format}"
            if expected.exists() and expected != target:
                expected.rename(target)
            success = target.exists()
            return ConversionResult(
                source_path=source_path, target_path=str(target),
                source_format=source.suffix.lower().lstrip('.'),
                target_format=target_format, success=success,
                error_message=None if success else
                    f"Conversion failed. LibreOffice output: {result.stderr}")
        except Exception as e:
            return ConversionResult(
                source_path=source_path, target_path=target_path,
                source_format=source.suffix.lower().lstrip('.'),
                target_format=target_format, success=False,
                error_message=str(e))

    # -- read_spreadsheet_data ----------------------------------------------
    def read_spreadsheet_data(self, path: str, sheet_name: Optional[str],
                              max_rows: int) -> SpreadsheetData:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Spreadsheet not found: {path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            _run_libreoffice_command([
                '--headless', '--convert-to', 'csv',
                '--outdir', tmp_dir, str(path_obj)])
            csv_file = Path(tmp_dir) / (path_obj.stem + '.csv')
            if not csv_file.exists():
                raise RuntimeError("Failed to convert spreadsheet to CSV")
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

        existing = self.read_document_text(path).content

        if position == "start":
            new_content = text + "\n" + existing
        elif position == "end":
            new_content = existing + "\n" + text
        elif position == "replace":
            new_content = text
        else:
            raise ValueError("Position must be 'start', 'end', or 'replace'")

        backup_path = str(path_obj) + '.backup'
        shutil.copy2(path_obj, backup_path)
        try:
            ext = path_obj.suffix.lower()
            if ext in ('.odt', '.docx', '.doc'):
                self._recreate_writer_document(str(path_obj), new_content)
            else:
                with open(path_obj, 'w', encoding='utf-8') as f:
                    f.write(new_content)
        except Exception as e:
            shutil.copy2(backup_path, path_obj)
            raise RuntimeError(f"Failed to modify document: {e}")
        finally:
            Path(backup_path).unlink(missing_ok=True)

        return get_document_info(str(path_obj))

    # -- open_document ------------------------------------------------------
    def open_document(self, path: str, readonly: bool,
                      force: bool = False) -> Dict[str, Any]:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        cmd = [_get_libreoffice_exe()]
        if readonly:
            cmd.append('--view')
        cmd.append(str(path_obj.absolute()))

        popen_kwargs: Dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS)
        else:
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(cmd, **popen_kwargs)
        return {
            "success": True,
            "message": f"Opened {path_obj.name} in LibreOffice GUI",
            "path": str(path_obj.absolute()),
            "readonly": readonly,
            "process_id": process.pid,
            "note": "Document is now open for live viewing.",
        }

    # -- refresh_document ---------------------------------------------------
    def refresh_document(self, path: str) -> Dict[str, Any]:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")
        path_obj.touch()
        return {
            "success": True,
            "message": f"Refresh signal sent for {path_obj.name}",
            "path": str(path_obj.absolute()),
            "note": "LibreOffice should detect the file change and prompt to reload.",
        }

    # -- private helpers ----------------------------------------------------
    def _recreate_writer_document(self, path: str, content: str) -> None:
        path_obj = Path(path)
        original_ext = path_obj.suffix.lower()

        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            target_fmt = {'.odt': 'odt', '.docx': 'docx', '.doc': 'doc'}.get(
                original_ext, 'odt')
            if path_obj.exists():
                path_obj.unlink()
            result = _run_libreoffice_command([
                '--headless', '--invisible', '--convert-to', target_fmt,
                '--outdir', str(path_obj.parent), tmp_path])
            converted = path_obj.parent / f"{Path(tmp_path).stem}.{target_fmt}"
            if converted.exists():
                converted.rename(path_obj)
                return
            if original_ext == '.odt' or target_fmt == 'odt':
                _create_minimal_odt(path_obj, content)
            else:
                with open(path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
