#!/bin/bash
# Wrapper script for mcp-helper.sh
exec "$(dirname "$0")/scripts/mcp-helper.sh" "$@"