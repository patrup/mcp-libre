import sys
import tempfile
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import TextResourceContents

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "test-output"
DOCUMENT_PATH = OUTPUT_DIRECTORY / "mcp-stdio-smoke.odt"


@pytest.mark.asyncio
async def test_stdio_protocol():
    """Exercise the actual MCPServer process over stdio."""
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    server = StdioServerParameters(
        command=sys.executable,
        args=["src/main.py"],
        cwd=PROJECT_ROOT,
    )

    with tempfile.TemporaryFile(mode="w+") as stderr:
        async with (
            stdio_client(server, errlog=stderr) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as client,
        ):
            initialized = await client.initialize()
            assert initialized.server_info.name == "LibreOffice MCP Server"

            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} >= {
                "create_document",
                "read_document_text",
                "insert_text_at_position",
            }

            resources = await client.list_resources()
            assert any(str(resource.uri) == "documents://" for resource in resources.resources)

            templates = await client.list_resource_templates()
            assert any(
                template.uri_template == "document://{+path}"
                for template in templates.resource_templates
            )

            created = await client.call_tool(
                "create_document",
                {
                    "path": str(DOCUMENT_PATH),
                    "doc_type": "writer",
                    "content": "MCP SDK 2 stdio smoke test.",
                },
            )
            assert created.is_error is False
            assert created.structured_content["exists"] is True
            assert DOCUMENT_PATH.is_file()

            content = await client.read_resource(f"document://{DOCUMENT_PATH}")
            resource_content = content.contents[0]
            assert isinstance(resource_content, TextResourceContents)
            assert "MCP SDK 2 stdio smoke test." in resource_content.text

            missing = await client.call_tool(
                "read_document_text",
                {"path": str(OUTPUT_DIRECTORY / "missing.odt")},
            )
            assert missing.is_error is True

        stderr.seek(0)
        assert "Starting LibreOffice MCP Server" in stderr.read()
