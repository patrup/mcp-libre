"""
Pydantic models for structured MCP tool responses.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    """Information about a LibreOffice document"""
    path: str = Field(description="Full path to the document")
    filename: str = Field(description="Document filename")
    format: str = Field(description="Document format (odt, ods, odp, etc.)")
    size_bytes: int = Field(description="File size in bytes")
    modified_time: datetime = Field(description="Last modification time")
    exists: bool = Field(description="Whether the file exists")


class TextContent(BaseModel):
    """Text content extracted from a document"""
    content: str = Field(description="The extracted text content")
    word_count: int = Field(description="Number of words in the content")
    char_count: int = Field(description="Number of characters in the content")
    page_count: Optional[int] = Field(description="Number of pages (if available)")


class ConversionResult(BaseModel):
    """Result of document conversion"""
    source_path: str = Field(description="Source document path")
    target_path: str = Field(description="Target document path")
    source_format: str = Field(description="Original format")
    target_format: str = Field(description="Converted format")
    success: bool = Field(description="Whether conversion was successful")
    error_message: Optional[str] = Field(description="Error message if conversion failed")


class SpreadsheetData(BaseModel):
    """Data from a spreadsheet"""
    sheet_name: str = Field(description="Name of the sheet")
    data: List[List[str]] = Field(description="2D array of cell values")
    row_count: int = Field(description="Number of rows")
    col_count: int = Field(description="Number of columns")


def get_document_info(file_path: str) -> DocumentInfo:
    """Get information about a document file."""
    path = Path(file_path)
    return DocumentInfo(
        path=str(path.absolute()),
        filename=path.name,
        format=path.suffix.lower().lstrip('.'),
        size_bytes=path.stat().st_size if path.exists() else 0,
        modified_time=datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else datetime.now(),
        exists=path.exists()
    )
