#!/usr/bin/env python3
"""
Test script for the LibreOffice MCP Server
This demonstrates basic usage of the server tools
"""

import asyncio
import json
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from mcp.shared.memory import create_connected_server_and_client_session as client_session
from libremcp import mcp

async def test_mcp_client():
    """Test the MCP server by calling its tools as a client would"""
    print("Testing LibreOffice MCP Server Tools")
    print("=" * 50)
    
    async with client_session(mcp._mcp_server) as client:
        # List available tools
        tools_result = await client.list_tools()
        print(f"\n📋 Available Tools ({len(tools_result.tools)}):")
        for tool in tools_result.tools:
            print(f"  • {tool.name}: {tool.description}")
        
        # List available resources
        resources_result = await client.list_resources()
        print(f"\n📁 Available Resources ({len(resources_result.resources)}):")
        for resource in resources_result.resources:
            print(f"  • {resource.uri}: {resource.description}")
        
        # Test creating a document
        print("\n🆕 Creating a test document...")
        result = await client.call_tool("create_document", {
            "path": "/tmp/mcp_test_doc.odt",
            "doc_type": "writer",
            "content": "This is a test document created via MCP!\n\nIt demonstrates the LibreOffice MCP Server capabilities."
        })
        
        if result.structuredContent:
            doc_info = result.structuredContent
            print(f"   ✓ Created: {doc_info['filename']}")
            print(f"   ✓ Size: {doc_info['size_bytes']} bytes")
        
        # Test reading the document
        print("\n📖 Reading document content...")
        result = await client.call_tool("read_document_text", {
            "path": "/tmp/mcp_test_doc.odt"
        })
        
        if result.structuredContent:
            content = result.structuredContent
            print(f"   ✓ Words: {content['word_count']}")
            print(f"   ✓ Characters: {content['char_count']}")
            print(f"   ✓ Content preview: {content['content'][:100]}...")
        
        # Test document statistics
        print("\n📊 Getting document statistics...")
        result = await client.call_tool("get_document_statistics", {
            "path": "/tmp/mcp_test_doc.odt"
        })
        
        if result.structuredContent:
            stats = result.structuredContent
            if 'content_stats' in stats:
                content_stats = stats['content_stats']
                print(f"   ✓ Words: {content_stats['word_count']}")
                print(f"   ✓ Sentences: {content_stats['sentence_count']}")
                print(f"   ✓ Paragraphs: {content_stats['paragraph_count']}")
                print(f"   ✓ Avg words/sentence: {content_stats['average_words_per_sentence']:.1f}")
            else:
                print(f"   ⚠ Statistics error: {stats.get('error', 'Unknown error')}")
        else:
            print("   ⚠ No statistics data returned")
        
        # Test text insertion
        print("\n✏️  Adding text to document...")
        result = await client.call_tool("insert_text_at_position", {
            "path": "/tmp/mcp_test_doc.odt",
            "text": "\n\nThis text was added via the MCP server!",
            "position": "end"
        })
        
        if result.structuredContent:
            print("   ✓ Text added successfully")
        
        # Test document conversion (if it works)
        print("\n🔄 Attempting document conversion...")
        try:
            result = await client.call_tool("convert_document", {
                "source_path": "/tmp/mcp_test_doc.odt",
                "target_path": "/tmp/mcp_test_doc.html",
                "target_format": "html"
            })
            
            if result.structuredContent:
                conversion = result.structuredContent
                if conversion['success']:
                    print(f"   ✓ Converted to HTML successfully")
                else:
                    print(f"   ⚠ Conversion failed: {conversion['error_message']}")
        except Exception as e:
            print(f"   ⚠ Conversion test failed: {str(e)}")
        
        # Test resource access
        print("\n📂 Testing resource access...")
        try:
            # Try to read the document resource with correct URI format
            from pydantic import AnyUrl
            resource_uri = AnyUrl("document://tmp/mcp_test_doc.odt")
            resource_result = await client.read_resource(resource_uri)
            if resource_result.contents:
                content = resource_result.contents[0]
                # Import proper content types
                from mcp.types import TextResourceContents
                # Check content type and access accordingly
                if isinstance(content, TextResourceContents):
                    print(f"   ✓ Resource text content preview: {content.text[:100]}...")
                else:
                    print("   ✓ Resource content available (binary)")
        except Exception as e:
            print(f"   ⚠ Resource test failed: {str(e)}")
        
        print("\n✅ MCP Server test completed!")
        
        # Cleanup
        print("\n🧹 Cleaning up test files...")
        import os
        for file in ["/tmp/mcp_test_doc.odt", "/tmp/mcp_test_doc.html"]:
            try:
                os.unlink(file)
                print(f"   ✓ Removed {file}")
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"   ⚠ Could not remove {file}: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_client())
