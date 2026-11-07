import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

import pytest
from mcp import ClientSession
from mcp.client._memory import InMemoryTransport
from mcp.types import TextResourceContents

from libremcp import mcp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "test-output"


@pytest.mark.asyncio
async def test_mcp_client():
    """Exercise tool and resource operations through the in-memory MCP transport."""
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    document_path = OUTPUT_DIRECTORY / "mcp-client.odt"
    html_path = OUTPUT_DIRECTORY / "mcp-client.html"

    async with (
        InMemoryTransport(mcp, raise_exceptions=True) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as client,
    ):
        await client.initialize()

        tools_result = await client.list_tools()
        assert {tool.name for tool in tools_result.tools} >= {
            "create_document",
            "read_document_text",
            "insert_text_at_position",
        }

        resources_result = await client.list_resources()
        assert any(str(resource.uri) == "documents://" for resource in resources_result.resources)

        templates_result = await client.list_resource_templates()
        assert any(
            template.uri_template == "document://{+path}"
            for template in templates_result.resource_templates
        )

        created = await client.call_tool(
            "create_document",
            {
                "path": str(document_path),
                "doc_type": "writer",
                "content": "This is a test document created via MCP.",
            },
        )
        assert created.is_error is False
        assert created.structured_content["exists"] is True

        text = await client.call_tool("read_document_text", {"path": str(document_path)})
        assert text.is_error is False
        assert "test document created via MCP" in text.structured_content["content"]

        stats = await client.call_tool("get_document_statistics", {"path": str(document_path)})
        assert stats.is_error is False
        assert stats.structured_content["result"]["content_stats"]["word_count"] > 0

        inserted = await client.call_tool(
            "insert_text_at_position",
            {
                "path": str(document_path),
                "text": "Additional MCP text.",
                "position": "end",
            },
        )
        assert inserted.is_error is False

        conversion = await client.call_tool(
            "convert_document",
            {
                "source_path": str(document_path),
                "target_path": str(html_path),
                "target_format": "html",
            },
        )
        assert conversion.is_error is False
        assert conversion.structured_content["success"] is True

        resource_result = await client.read_resource(f"document://{document_path}")
        assert resource_result.contents
        resource_content = resource_result.contents[0]
        assert isinstance(resource_content, TextResourceContents)
        assert "Additional MCP text." in resource_content.text


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
