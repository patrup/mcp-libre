#!/usr/bin/env python3

"""
Test script for the insert_text_at_position function to verify the fix
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from libremcp import create_document, insert_text_at_position, read_document_text


def test_insert_text_fix():
    """Insert, prepend, and replace text in a Writer document."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_doc = Path(temp_dir) / "test_insert.odt"

        result = create_document(str(test_doc), "writer", "Hello World")
        assert result.exists

        content = read_document_text(str(test_doc))
        assert "Hello World" in content.content

        insert_text_at_position(str(test_doc), ".", "end")
        content = read_document_text(str(test_doc))
        assert "Hello World" in content.content
        assert "." in content.content

        insert_text_at_position(str(test_doc), "Beginning: ", "start")
        content = read_document_text(str(test_doc))
        assert "Beginning:" in content.content

        insert_text_at_position(str(test_doc), "This is completely new content!", "replace")
        final_content = read_document_text(str(test_doc))
        assert final_content.content.strip() == "This is completely new content!"


def test_edge_cases():
    """Verify that Writer insertion accepts representative text edge cases."""
    edge_cases = [
        ("Empty string", ""),
        ("Just a space", " "),
        ("Single character", "x"),
        ("Special characters", "!@#$%^&*()"),
        ("Unicode", "Hello 世界 🌍"),
        ("Newlines", "Line 1\nLine 2\nLine 3"),
        ("Long text", "This is a very long text " * 20),
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for test_name, test_text in edge_cases:
            test_doc = temp_path / f"test_{test_name.replace(' ', '_').lower()}.odt"
            create_document(str(test_doc), "writer", "Initial content")
            insert_text_at_position(str(test_doc), test_text, "end")
            content = read_document_text(str(test_doc))
            assert "Initial content" in content.content
            if test_text.strip():
                assert " ".join(test_text.split()) in " ".join(content.content.split())


if __name__ == "__main__":
    test_insert_text_fix()
    test_edge_cases()
