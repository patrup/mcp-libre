# mcp-libre contributor guide

## Setup, build, and validation

- The project requires Python 3.12+, `uv`, and LibreOffice 24.2+ available on `PATH`. Install Python dependencies with `uv sync`.
- Run the external MCPServer in stdio mode with `uv run python src/main.py`; use `uv run python src/main.py --test` for its built-in LibreOffice smoke test. It keeps generated artifacts in `test-output/`.
- Run the focused Writer insertion test with `uv run pytest -q tests/test_insert_fix.py::test_insert_text_fix`, or run its complete script (including edge cases) with `uv run python tests/test_insert_fix.py`.
- Run the MCP client integration scenario with `uv run pytest -q tests/test_client.py`. It uses LibreOffice and retains inspectable artifacts in `test-output/`.
- Build the LibreOffice extension with `cd plugin && ./build.sh`. The packaged `.oxt` is written to `build/`; the build and install scripts currently contain machine-specific absolute paths, so update them before relying on them outside that checkout.
- With the extension installed and LibreOffice running, validate its HTTP API via `cd plugin && ./install.sh test`; `./install.sh status` checks installation and `http://localhost:8765/health`.
- No lint or formatter command is configured in `pyproject.toml`.

## Architecture

The repository supports two distinct integrations:

- **External file-oriented MCP server:** `src/main.py` imports `src/libremcp.py`, which owns the MCP SDK 2.x `MCPServer` instance. `@mcp.tool()` functions create, read, convert, edit, search, and analyze files; `@mcp.resource()` functions expose document discovery and content. LibreOffice CLI subprocesses (`--headless`) perform most document work, while ODT text extraction and minimal ODT generation are fallbacks. Keep MCP tool return values as the Pydantic response models (`DocumentInfo`, `TextContent`, `ConversionResult`, `SpreadsheetData`) where applicable.
- **Embedded live LibreOffice extension:** files under `plugin/pythonpath/` run inside LibreOffice's Python/UNO environment. `registration.py` is the extension lifecycle and menu-command entry point; it starts `ai_interface.py` on localhost port 8765. The HTTP handler forwards requests to `mcp_server.py`, whose tool registry delegates live-document operations to `uno_bridge.py`. These tools operate on the active LibreOffice document and return dictionaries with `success` and either result data or `error`.

The root `libremcp.py` re-exports `src.libremcp` for backward-compatible imports. Treat `src/libremcp.py` as the implementation for the external server and keep entry-point imports aligned with it.

## Repository conventions

- Register externally visible file operations with `@mcp.tool()` and resources with `@mcp.resource()` on the shared `mcp` object in `src/libremcp.py`. The function docstring and typed signature form the client-facing tool contract.
- Route LibreOffice CLI calls through `_run_libreoffice_command`, which tries `libreoffice`, `loffice`, then `soffice`, captures output, and applies a timeout.
- File-oriented operations create parent directories as needed. Editing preserves a `.backup` until the operation completes, then removes it; preserve that rollback behavior when changing document mutation.
- The extension's tool registry is the API schema source of truth: add a schema and handler in `LibreOfficeMCPServer._register_tools`, implement behavior through `UNOBridge`, and preserve the `{"success": bool, ...}` response shape.
- The extension HTTP API is local-only: `GET /`, `/tools`, and `/health`; `POST /tools/{tool_name}` and `/execute`. Keep registration and API changes consistent with the XML extension metadata and menu configuration.
- The test suite combines an in-memory MCP SDK transport test with a real stdio subprocess test. Use MCP SDK 2.x snake_case result fields such as `structured_content`, `is_error`, and `uri_template`; dynamic file resources use the `document://{+path}` template with an explicit path-security exemption.
