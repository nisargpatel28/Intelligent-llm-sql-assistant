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

    def get_suggestions(self, user_id: str, current_query: str = "",
                        context: Optional[Dict] = None) -> List[Dict]:
        """Get query suggestions based on user history and current input"""
        suggestions = []

        # Get pattern-based suggestions
        pattern_suggestions = self._get_pattern_suggestions(
            user_id, current_query)
        suggestions.extend(pattern_suggestions)

        # Get frequency-based suggestions
        frequency_suggestions = self._get_frequency_suggestions(
            user_id, current_query)
        suggestions.extend(frequency_suggestions)

        # Get AI-powered suggestions if available
        if GEMINI_AVAILABLE and context:
            ai_suggestions = self._get_ai_suggestions(
                user_id, current_query, context)
            suggestions.extend(ai_suggestions)

        # Remove duplicates and sort by relevance
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            key = suggestion.get('query', '').lower()
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)

        # Sort by confidence score
        unique_suggestions.sort(key=lambda x: x.get(
            'confidence', 0), reverse=True)

        return unique_suggestions[:10]  # Return top 10 suggestions

    def _get_pattern_suggestions(self, user_id: str, current_query: str) -> List[Dict]:
        """Get suggestions based on query patterns"""
        suggestions = []

        if not current_query.strip():
            return suggestions

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find queries that start with similar patterns
        current_lower = current_query.lower()
        cursor.execute("""
            SELECT DISTINCT query, COUNT(*) as frequency
            FROM query_history
            WHERE user_id = ? AND query LIKE ?
            GROUP BY query
            ORDER BY frequency DESC
            LIMIT 5
        """, (user_id, f"{current_lower}%"))

        for row in cursor.fetchall():
            suggestions.append({
                'query': row[0],
                'type': 'pattern',
                'confidence': min(row[1] / 10, 1.0),  # Normalize frequency
                'reason': 'Based on similar query patterns'
            })

        conn.close()
        return suggestions