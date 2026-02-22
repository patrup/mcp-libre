"""
Abstract base class for document backends.

Exactly the 7 operations that differ between GUI and headless modes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..models import DocumentInfo, TextContent, ConversionResult, SpreadsheetData


class DocumentBackend(ABC):
    """Abstract document backend with 7 operations."""

    @abstractmethod
    def create_document(self, path: str, doc_type: str, content: str) -> DocumentInfo:
        """Create a new document at *path*."""

    @abstractmethod
    def read_document_text(self, path: str) -> TextContent:
        """Extract text content from a document."""

    @abstractmethod
    def convert_document(self, source_path: str, target_path: str,
                         target_format: str) -> ConversionResult:
        """Convert a document to a different format."""

    @abstractmethod
    def read_spreadsheet_data(self, path: str, sheet_name: Optional[str],
                              max_rows: int) -> SpreadsheetData:
        """Read data from a spreadsheet."""

    @abstractmethod
    def insert_text(self, path: str, text: str, position: str) -> DocumentInfo:
        """Insert text into a Writer document."""

    @abstractmethod
    def open_document(self, path: str, readonly: bool,
                      force: bool = False) -> Dict[str, Any]:
        """Open a document for live viewing."""

    @abstractmethod
    def refresh_document(self, path: str) -> Dict[str, Any]:
        """Refresh / reload a document in the viewer."""
