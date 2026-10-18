#!/usr/bin/env python3
"""Ponto de entrada compativel com a configuracao do cliente (uv run mcp_server.py).

O servidor de verdade mora em accessibility_mcp/server.py."""

from accessibility_mcp.server import main

if __name__ == "__main__":
    main()
