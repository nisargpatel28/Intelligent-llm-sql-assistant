"""
Conversation Manager for Multi-turn Conversations with Context Retention
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Message:
    """Represents a single message in the conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Optional[Dict] = None


class ConversationManager:
    """Manages conversation context and history for multi-turn interactions"""

    def __init__(self, db_path: str = "conversation.db", max_context_length: int = 50):
        self.db_path = db_path
        self.max_context_length = max_context_length
        self._init_database()

    def _init_database(self):
        """Initialize the conversation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                user_id TEXT NOT NULL,
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                session_id TEXT
            )
        """)

        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_timestamp
            ON conversations(user_id, timestamp)
        """)

        conn.commit()
        conn.close()

    def add_message(self, user_id: str, role: str, content: str,
                    metadata: Optional[Dict] = None, session_id: Optional[str] = None):
        """Add a message to the conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        cursor.execute("""
            INSERT INTO conversations (user_id, role, content, timestamp, metadata, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            message.role,
            message.content,
            message.timestamp.isoformat(),
            json.dumps(message.metadata),
            session_id
        ))

        # Clean up old messages to maintain context length
        self._cleanup_old_messages(cursor, user_id)

        conn.commit()
        conn.close()

    def _cleanup_old_messages(self, cursor: sqlite3.Cursor, user_id: str):
        """Remove old messages to keep context within limits"""
        cursor.execute("""
            DELETE FROM conversations
            WHERE user_id = ? AND message_id NOT IN (
                SELECT message_id FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
        """, (user_id, user_id, self.max_context_length))

    def get_context(self, user_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation context for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        limit_clause = f"LIMIT {limit}" if limit else ""

        cursor.execute(f"""
            SELECT role, content, timestamp, metadata
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            {limit_clause}
        """, (user_id,))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3]) if row[3] else {}
            })

        conn.close()

        # Return in chronological order (oldest first)
        return list(reversed(messages))

    def get_recent_context(self, user_id: str, hours: int = 24) -> List[Dict]:
        """Get context from the last N hours"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT role, content, timestamp, metadata
            FROM conversations
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (user_id, cutoff_time))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3]) if row[3] else {}
            })

        conn.close()
        return messages

    def clear_context(self, user_id: str):
        """Clear all conversation context for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM conversations WHERE user_id = ?", (user_id,))

        conn.commit()
        conn.close()

    def get_conversation_stats(self, user_id: str) -> Dict:
        """Get statistics about the user's conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
            FROM conversations
            WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row and row[0] > 0:
            return {
                "total_messages": row[0],
                "first_message": row[1],
                "last_message": row[2]
            }
        else:
            return {"total_messages": 0, "first_message": None, "last_message": None}

    def search_conversation(self, user_id: str, query: str) -> List[Dict]:
        """Search conversation history for specific content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT role, content, timestamp, metadata
            FROM conversations
            WHERE user_id = ? AND content LIKE ?
            ORDER BY timestamp DESC
        """, (user_id, f"%{query}%"))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3]) if row[3] else {}
            })

        conn.close()
        return messages