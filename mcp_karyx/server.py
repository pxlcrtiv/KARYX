"""MCP stdio server entry-point for Karyx.

Usage::

    mcp-karyx              # via console_script
    python -m mcp_karyx.server   # via module invocation

The server exposes three tools: ``karyx_optimize``, ``karyx_verify``,
``karyx_deploy`` — all defined in ``mcp_karyx.tools``.
"""
from mcp.server.fastmcp import FastMCP

from mcp_karyx.tools import register_tools

mcp = FastMCP("karyx")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run()
