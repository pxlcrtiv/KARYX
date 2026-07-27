"""MCP tool definitions for Karyx.

Each tool is registered on the FastMCP server instance passed in at
module level.  The functions themselves are thin: they parse
parameters, delegate to ``mcp_karyx.wrapper``, and return dicts.
"""
from mcp.server.fastmcp import FastMCP

from mcp_karyx import wrapper


def register_tools(mcp: FastMCP) -> None:
    """Register all karyx MCP tools on *mcp*."""

    @mcp.tool()
    def karyx_optimize(
        model: str,
        target: str,
        precision: str = "INT8",
        security_level: str = "IL4",
    ) -> dict:
        """Optimize an ONNX model for a target edge device.

        Runs the full Karyx pipeline: validate → detect → quantize →
        optimize → audit → package.  Returns the package path, audit
        chain hash, and session id.
        """
        return wrapper.optimize(
            model=model,
            target=target,
            precision=precision,
            security_level=security_level,
        )

    @mcp.tool()
    def karyx_verify(package: str) -> dict:
        """Verify the integrity of a Karyx deployment package.

        Extracts the audit log from the package tarball and confirms
        the hash chain is unbroken and untampered.
        """
        return wrapper.verify(package=package)

    @mcp.tool()
    def karyx_deploy(package: str, target_host: str = "") -> dict:
        """Deploy a Karyx package to a target host (stub).

        This tool is a placeholder.  Real deployment logic is not yet
        implemented; the call succeeds but returns ``deployed: false``.
        """
        return wrapper.deploy(
            package=package,
            target_host=target_host or None,
        )
