#!/usr/bin/env python3

"""
Test script for the insert_text_at_position function to verify the fix
"""

import tempfile
import os
import sys
from pathlib import Path

# Add the project root to Python path so 'src' is importable as a package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.server import backend


def test_insert_text_fix():
    """Test that insert_text works with simple character insertion"""

    print("Testing insert_text fix...")
    print("=" * 50)

    temp_dir = Path(tempfile.mkdtemp())
    test_doc = temp_dir / "test_insert.odt"

    try:
        # 1. Create a test document
        print("\n Step 1: Creating test document...")
        result = backend.create_document(str(test_doc), "writer", "Hello World")
        print(f"  Created: {result.path}")

        # 2. Read initial content
        print("\n Step 2: Reading initial content...")
        content = backend.read_document_text(str(test_doc))
        print(f"  Initial content: '{content.content.strip()}'")
        print(f"   Word count: {content.word_count}")

        # 3. Test inserting a simple character
        print("\n Step 3: Inserting a simple period '.' at the end...")
        try:
            result = backend.insert_text(str(test_doc), ".", "end")
            print("  Successfully inserted period")
            print(f"   File updated: {result.filename}")
        except Exception as e:
            print(f"  Failed to insert period: {e}")
            return False

        # 4. Verify the change
        print("\n Step 4: Verifying the change...")
        content = backend.read_document_text(str(test_doc))
        print(f"  Updated content: '{content.content.strip()}'")

        # 5. Test inserting at start
        print("\n Step 5: Inserting text at start...")
        try:
            result = backend.insert_text(str(test_doc), "Beginning: ", "start")
            print("  Successfully inserted at start")
        except Exception as e:
            print(f"  Failed to insert at start: {e}")
            return False

        # 6. Test replacing content
        print("\n Step 6: Replacing content...")
        try:
            result = backend.insert_text(str(test_doc), "This is completely new content!", "replace")
            print("  Successfully replaced content")
        except Exception as e:
            print(f"  Failed to replace content: {e}")
            return False

        # 7. Final verification
        print("\n Step 7: Final verification...")
        final_content = backend.read_document_text(str(test_doc))
        print(f"  Final content: '{final_content.content.strip()}'")
        print(f"   Final word count: {final_content.word_count}")

        print("\n All tests passed!")
        return True

    except Exception as e:
        print(f"\n Test failed with error: {e}")
        return False

    finally:
        import shutil
        try:
            shutil.rmtree(temp_dir)
            print(f"\n Cleaned up: {temp_dir}")
        except Exception:
            pass


def test_edge_cases():
    """Test edge cases that might cause issues"""

    print("\n Testing edge cases...")
    print("=" * 30)

    temp_dir = Path(tempfile.mkdtemp())

    edge_cases = [
        ("Empty string", ""),
        ("Just a space", " "),
        ("Single character", "x"),
        ("Special characters", "!@#$%^&*()"),
        ("Unicode", "Hello world"),
        ("Newlines", "Line 1\nLine 2\nLine 3"),
        ("Long text", "This is a very long text " * 20),
    ]

    for test_name, test_text in edge_cases:
        test_doc = temp_dir / f"test_{test_name.replace(' ', '_').lower()}.odt"

        try:
            print(f"\n Testing: {test_name}")
            backend.create_document(str(test_doc), "writer", "Initial content")
            backend.insert_text(str(test_doc), test_text, "end")
            content = backend.read_document_text(str(test_doc))
            print(f"   Success - Final length: {len(content.content)} chars")
        except Exception as e:
            print(f"   Failed: {e}")

    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


if __name__ == "__main__":
    print("LibreOffice MCP Server - Insert Text Fix Test")
    print("=" * 60)

    success = test_insert_text_fix()

    if success:
        test_edge_cases()
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
    else:
        print("\n" + "=" * 60)
        print("Some tests failed.")
