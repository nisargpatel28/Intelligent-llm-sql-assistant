"""
Automated Report Generation for Transaction Data
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class ReportGenerator:
    """Generates automated reports from transaction data"""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict]:
        """Load report templates"""
        return {
            "summary": {
                "title": "Transaction Summary Report",
                "sections": ["overview", "trends", "insights"],
                "charts": ["amount_distribution", "status_pie"]
            },
            "detailed": {
                "title": "Detailed Transaction Analysis Report",
                "sections": ["overview", "breakdown", "anomalies", "recommendations"],
                "charts": ["time_series", "amount_distribution", "status_breakdown"]
            },
            "trends": {
                "title": "Transaction Trends Report",
                "sections": ["overview", "temporal_analysis", "patterns"],
                "charts": ["trends_over_time", "weekly_patterns", "monthly_comparison"]
            }
        }