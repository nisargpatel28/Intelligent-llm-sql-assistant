"""
Model Context Protocol (MCP) Server for LLM SQL Assistant
Provides AI capabilities as MCP tools for external clients
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp import Tool, types
from mcp.server import Server
from mcp.server.stdio import stdio_server
