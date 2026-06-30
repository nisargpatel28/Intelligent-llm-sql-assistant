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


def test_basic_functionality():
    """Test basic functionality of AI features"""
    try:
        from ai_features.conversation.manager import ConversationManager

        # Test conversation manager
        manager = ConversationManager()

        # Add a test message
        manager.add_message("test_user", "user", "Hello world")
        print("✓ Conversation manager: message added")

        # Get context
        context = manager.get_context("test_user")
        assert len(context) == 1
        assert context[0]["content"] == "Hello world"
        print("✓ Conversation manager: context retrieved")

        # Clear context
        manager.clear_context("test_user")
        context = manager.get_context("test_user")
        assert len(context) == 0
        print("✓ Conversation manager: context cleared")

        return True
    except Exception as e:
        print(f"✗ Functionality test error: {e}")
        return False


if __name__ == "__main__":
    print("Testing AI Features Implementation")
    print("=" * 40)

    success = True

    print("\n1. Testing imports...")
    if not test_imports():
        success = False

    print("\n2. Testing basic functionality...")
    if not test_basic_functionality():
        success = False

    print("\n" + "=" * 40)
    if success:
        print("✓ All tests passed! AI features are properly implemented.")
    else:
        print("✗ Some tests failed. Please check the implementation.")

    sys.exit(0 if success else 1)
