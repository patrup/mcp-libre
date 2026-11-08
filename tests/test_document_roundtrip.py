import zipfile
from pathlib import Path

import pytest

from src.libremcp import (
    _find_uno_python,
    create_document,
    read_document_text,
    read_spreadsheet_data,
)


@pytest.mark.parametrize(
    ("doc_type", "extension", "mime_type", "content"),
    [
        ("writer", "odt", "application/vnd.oasis.opendocument.text", "Writer round-trip text"),
        pytest.param(
            "calc",
            "ods",
            "application/vnd.oasis.opendocument.spreadsheet",
            "Calc round-trip text",
            marks=pytest.mark.skipif(
                _find_uno_python() is None,
                reason="LibreOffice UNO Python bindings are required for Calc round-trip tests",
            ),
        ),
        pytest.param(
            "impress",
            "odp",
            "application/vnd.oasis.opendocument.presentation",
            "Impress round-trip text",
            marks=pytest.mark.skipif(
                _find_uno_python() is None,
                reason="LibreOffice UNO Python bindings are required for Impress round-trip tests",
            ),
        ),
    ],
)
def test_create_save_close_and_reopen_odf_documents(
    tmp_path: Path, doc_type: str, extension: str, mime_type: str, content: str
):
    """Create documents externally, then reopen them through LibreOffice readers."""
    path = tmp_path / f"round-trip.{extension}"

    result = create_document(str(path), doc_type, content)

    assert result.exists
    assert result.size_bytes > 0
    assert zipfile.is_zipfile(path)
    with zipfile.ZipFile(path) as document:
        assert document.read("mimetype").decode() == mime_type
        assert content in document.read("content.xml").decode()

    if doc_type == "calc":
        reopened = read_spreadsheet_data(str(path))
        assert reopened.data[0][0] == content
    else:
        reopened = read_document_text(str(path))
        assert content in reopened.content
