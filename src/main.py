#!/usr/bin/env python3
"""
Main entry point for the LibreOffice MCP Server
"""

import sys
import os

# When run directly (python src/main.py), add parent dir so 'src' is importable as a package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.server import main

if __name__ == "__main__":
    main()
