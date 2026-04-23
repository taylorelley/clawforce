"""MCP Registry client and implementation for the official Model Context Protocol registry.

.. deprecated::
   Use :mod:`specops_lib.registry` and :func:`get_mcp_registry` instead.
   Uses official MCP registry (registry.modelcontextprotocol.io).
"""

from specops_lib.mcpregistry.client import (
    MCPRegistryClient,
    search_mcp_registry,
)
from specops_lib.mcpregistry.models import MCPServerInfo
from specops_lib.mcpregistry.official_mcp import OfficialMCPRegistry
from specops_lib.mcpregistry.yaml_catalog import YamlMCPRegistry

__all__ = [
    "MCPRegistryClient",
    "MCPServerInfo",
    "OfficialMCPRegistry",
    "YamlMCPRegistry",
    "search_mcp_registry",
]
