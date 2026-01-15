"""
Entry point for running the MCP server.

Usage:
    uv run python scripts/run_mcp_server.py
"""
from src.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()