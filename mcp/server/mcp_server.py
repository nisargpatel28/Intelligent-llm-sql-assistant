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


class LLMAssistantMCPServer:
    """MCP Server providing AI capabilities for the LLM SQL Assistant"""

    def __init__(self):
        self.server = Server("llm-sql-assistant")
        self.conversation_manager = ConversationManager()
        self.query_predictor = QueryPredictor()
        self.anomaly_detector = AnomalyDetector()
        self.report_generator = ReportGenerator()

    async def handle_conversation_context(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle multi-turn conversation context management"""
        user_id = arguments.get("user_id", "default")
        message = arguments.get("message", "")
        action = arguments.get("action", "add")  # add, get, clear

        try:
            if action == "add":
                self.conversation_manager.add_message(user_id, "user", message)
                return [types.TextContent(type="text", text="Message added to conversation context")]

            elif action == "get":
                context = self.conversation_manager.get_context(user_id)
                return [types.TextContent(type="text", text=json.dumps(context, indent=2))]

            elif action == "clear":
                self.conversation_manager.clear_context(user_id)
                return [types.TextContent(type="text", text="Conversation context cleared")]

            else:
                return [types.TextContent(type="text", text=f"Unknown action: {action}")]

        except Exception as e:
            logger.error(f"Error in conversation context: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def handle_query_suggestions(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle predictive query suggestions"""
        user_id = arguments.get("user_id", "default")
        current_query = arguments.get("current_query", "")
        context = arguments.get("context", {})

        try:
            suggestions = self.query_predictor.get_suggestions(
                user_id, current_query, context)
            return [types.TextContent(type="text", text=json.dumps(suggestions, indent=2))]

        except Exception as e:
            logger.error(f"Error in query suggestions: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def handle_anomaly_detection(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle anomaly detection in transaction data"""
        data = arguments.get("data", [])
        threshold = arguments.get("threshold", 0.95)

        try:
            anomalies = self.anomaly_detector.detect_anomalies(data, threshold)
            return [types.TextContent(type="text", text=json.dumps(anomalies, indent=2))]

        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def handle_report_generation(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle automated report generation"""
        report_type = arguments.get("report_type", "summary")
        data = arguments.get("data", [])
        filters = arguments.get("filters", {})

        try:
            report = self.report_generator.generate_report(
                report_type, data, filters)
            return [types.TextContent(type="text", text=json.dumps(report, indent=2))]

        except Exception as e:
            logger.error(f"Error in report generation: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def setup_tools(self):
        """Set up MCP tools"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="conversation_context",
                    description="Manage multi-turn conversation context for users",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User identifier"},
                            "message": {"type": "string", "description": "Message to add to context"},
                            "action": {"type": "string", "enum": ["add", "get", "clear"], "description": "Action to perform"}
                        },
                        "required": ["user_id", "action"]
                    }
                ),
                Tool(
                    name="query_suggestions",
                    description="Get predictive query suggestions based on user history and context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User identifier"},
                            "current_query": {"type": "string", "description": "Current partial query"},
                            "context": {"type": "object", "description": "Additional context for suggestions"}
                        },
                        "required": ["user_id"]
                    }
                ),
                Tool(
                    name="anomaly_detection",
                    description="Detect anomalies in transaction data using statistical methods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "data": {"type": "array", "description": "Transaction data array"},
                            "threshold": {"type": "number", "description": "Anomaly detection threshold (0-1)"}
                        },
                        "required": ["data"]
                    }
                ),
                Tool(
                    name="report_generation",
                    description="Generate automated reports from transaction data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "report_type": {"type": "string", "enum": ["summary", "detailed", "trends"], "description": "Type of report to generate"},
                            "data": {"type": "array", "description": "Data for report generation"},
                            "filters": {"type": "object", "description": "Filters to apply to data"}
                        },
                        "required": ["report_type", "data"]
                    }
                )
            ]
