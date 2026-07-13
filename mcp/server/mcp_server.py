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

# Import our AI features
from ai_features.conversation.manager import ConversationManager
from ai_features.suggestions.predictor import QueryPredictor
from ai_features.anomaly_detection.detector import AnomalyDetector
from ai_features.report_generation.generator import ReportGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

