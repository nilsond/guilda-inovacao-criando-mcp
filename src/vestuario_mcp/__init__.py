"""Vestuário MCP: backend simulado de um e-commerce de roupas exposto via Model Context Protocol."""

from vestuario_mcp.server import build_server
from vestuario_mcp.services import Loja

__all__ = ["Loja", "build_server"]
__version__ = "0.1.0"
