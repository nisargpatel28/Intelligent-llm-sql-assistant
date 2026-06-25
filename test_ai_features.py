#!/usr/bin/env python3
"""
Test script for AI features basic functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test basic imports without heavy dependencies"""
    try:
        # Test conversation manager (minimal dependencies)
        from ai_features.conversation.manager import ConversationManager
        print("✓ Conversation manager imported successfully")

        # Test MCP components
        from mcp.client.mcp_client import MCPClientManager
        print("✓ MCP client imported successfully")

        from tools.external.external_tools import external_tools_manager
        print("✓ External tools manager imported successfully")

        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False
