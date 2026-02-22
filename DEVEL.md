# DEVEL

## Scripts

| Script | Purpose |
|--------|---------|
| `install.ps1` | Full setup: Python, LibreOffice, UV, Claude config |
| `install.ps1 -Plugin` | Build + install the .oxt extension via unopkg |
| `install.ps1 -BuildOnly` | Build the .oxt only (no install) |
| `scripts/dev-deploy.ps1` | Dev mode: sync plugin/ → build/dev/ + junction in LO |
| `scripts/kill-libreoffice.ps1` | Kill all soffice processes |
| `scripts/launch-lo-debug.ps1` | Launch LO with SAL_LOG for debugging |
| `scripts/install-plugin.ps1` | Build + install plugin (called by `install.ps1 -Plugin`) |
| `scripts/generate-config.sh` | Generate Claude config (Linux/macOS) |
| `scripts/mcp-helper.sh` | Helper utilities (Linux/macOS) |

## Hot deploy

```powershell
.\scripts\dev-deploy.ps1     # sync plugin/ → build/dev/ + junction into LO extensions
# restart LibreOffice
curl http://localhost:8765/health
```

## Logs

- **Plugin (LO side):** `~/mcp-extension.log`
- **MCP server (Claude side):** stderr in Claude Code terminal
- **Claude Desktop MCP:** `%APPDATA%\Claude\logs\mcp.log`
- **LO internal debug** (slow startup!): `.\scripts\launch-lo-debug.ps1 -Full`

## Architecture

```
plugin/               → LO extension (.oxt), runs INSIDE LibreOffice
  pythonpath/
    registration.py   → UNO component, menu, HTTP server lifecycle
    ai_interface.py   → HTTP server (port 8765), routes /health /tools /execute
    mcp_server.py     → tool registry + handlers (calls uno_bridge)
    uno_bridge.py     → UNO API: Writer, Calc, Impress
src/                  → MCP server (stdio), runs on Claude's side
  server.py           → FastMCP instance, entry point
  plugin.py           → HTTP client → localhost:8765
  backends/           → GUI (default, via plugin HTTP) / Headless (subprocess soffice)
  tools/              → common, writer, calc, impress
```

**Flow:** Claude → MCP stdio → `src/` → HTTP POST → `plugin/` (inside LO) → UNO API

## Env vars

| Variable | Default | Effect |
|----------|---------|--------|
| `MCP_LIBREOFFICE_HEADLESS` | `0` | `1` = headless mode (subprocess), otherwise GUI |
| `MCP_PLUGIN_URL` | `http://localhost:8765` | Plugin HTTP endpoint |

## Known pitfalls

- **NEVER nuke `uno_packages/cache/`** — use `unopkg remove` + `unopkg add`
- **`allow_reuse_address = True`** on Windows = port shadowing. Forbidden.
- **PowerShell UTF-8 BOM**: `Set-Content -Encoding UTF8` adds BOM → LO Python crashes. Use `System.Text.UTF8Encoding($false)`.
- **Relative imports** in plugin: `from .module import X` → `from module import X` (LO adds `pythonpath/` to sys.path directly). `dev-deploy.ps1` converts automatically.
- **`registration.py` loaded twice** by LO: once for UNO registration, once at runtime.

## Locator convention (`type:value`)

Writer: `bookmark:_mcp_x`, `paragraph:42`, `page:3`, `section:Intro`, `heading:2.1`
Calc: direct params (`range`, `cell`, `sheet_name`)
Impress: direct params (`slide_index`)

## Tests

```bash
uv run pytest tests/
curl http://localhost:8765/tools          # list plugin tools
curl -X POST http://localhost:8765/tools/list_sheets -d '{}'
```
