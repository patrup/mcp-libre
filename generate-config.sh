#!/bin/bash
# Wrapper script for generate-config.sh
exec "$(dirname "$0")/scripts/generate-config.sh" "$@"