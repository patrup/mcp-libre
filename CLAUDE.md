# Technical Caveats

## LibreOffice Subprocess

- Multiple executable names attempted (libreoffice, loffice, soffice) due to platform variations
- Process exits are not always reliable indicators of success; soffice may report exit code != 0 despite success
- Conversion to temp directory then rename to target ensures atomic operation but adds complexity

## File Operations

- Temporary files cleaned via unlink() in catch blocks; not guaranteed on process termination
- Text encoding uses utf-8 with 'ignore' flag; invalid sequences silently discarded
- No explicit file locking; concurrent access to same document may cause conflicts

## Performance Limits

- Hardcoded 30s timeout for LibreOffice operations; large documents may exceed limit
- Recursive file search depth limited to 5 levels to prevent excessive traversal
- Document search reads entire file content into memory; not suitable for documents > 100MB
- Document discovery scans multiple directories on first call; initial latency significant

## Error Handling

- Most file system errors in loops use empty catch blocks; failures silently skipped
- Tool errors partially evaluated (first match context only for search)
- Network/socket errors during MCP streaming not explicitly handled

## MCP Protocol

- Readline-based JSONRPC parser assumes complete messages per line; partial messages cause parse errors
- No signal handling; SIGTERM/SIGINT terminate immediately without cleanup
- Concurrent tool calls processed sequentially; async/await in loop blocks on each operation

## Resource Limitations

- read_spreadsheet_data returns stub (empty arrays); full spreadsheet parsing not implemented
- ODT document creation uses minimal structure; may not preserve all properties in round-trip
- Search contexts limited to 200 chars around match; longer matches truncated

## Dependencies

- Requires LibreOffice 24.2+ with headless mode support
- Requires Node.js 18+ for ES modules and modern async/await
- No external npm dependencies; all functionality built-in Node.js
