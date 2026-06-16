"""
Query Predictor for Predictive Query Suggestions
"""

import json
import sqlite3
from typing import Dict, List, Optional
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class QueryPredictor:
    """Predicts query suggestions based on user history and patterns"""

    def __init__(self, db_path: str = "query_history.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the query history database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success BOOLEAN DEFAULT 1,
                execution_time REAL,
                result_count INTEGER
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_query
            ON query_history(user_id, query)
        """)

        conn.commit()
        conn.close()

    def record_query(self, user_id: str, query: str, success: bool = True,
                     execution_time: Optional[float] = None, result_count: Optional[int] = None):
        """Record a query execution for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO query_history (user_id, query, timestamp, success, execution_time, result_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            query.lower().strip(),
            datetime.now().isoformat(),
            success,
            execution_time,
            result_count
        ))

        conn.commit()
        conn.close()