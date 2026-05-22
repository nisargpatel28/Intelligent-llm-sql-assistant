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

    def generate_report(self, report_type: str, data: List[Dict], filters: Optional[Dict] = None) -> Dict:
        """
        Generate a comprehensive report from transaction data

        Args:
            report_type: Type of report ('summary', 'detailed', 'trends')
            data: Transaction data
            filters: Optional filters to apply

        Returns:
            Dictionary containing report data, insights, and visualizations
        """
        if not data:
            return {"error": "No data provided for report generation"}

        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Apply filters if provided
            if filters:
                df = self._apply_filters(df, filters)

            if df.empty:
                return {"error": "No data remains after applying filters"}

            # Preprocess data
            df = self._preprocess_data(df)

            # Generate report based on type
            if report_type == "summary":
                return self._generate_summary_report(df)
            elif report_type == "detailed":
                return self._generate_detailed_report(df)
            elif report_type == "trends":
                return self._generate_trends_report(df)
            else:
                return {"error": f"Unknown report type: {report_type}"}

        except Exception as e:
            return {"error": str(e)}

    def _apply_filters(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """Apply filters to the dataframe"""
        filtered_df = df.copy()

        # Date range filter
        if 'date_from' in filters:
            filtered_df = filtered_df[filtered_df['date']
                                      >= filters['date_from']]
        if 'date_to' in filters:
            filtered_df = filtered_df[filtered_df['date']
                                      <= filters['date_to']]

        # Amount range filter
        if 'amount_min' in filters:
            filtered_df = filtered_df[filtered_df['amount']
                                      >= filters['amount_min']]
        if 'amount_max' in filters:
            filtered_df = filtered_df[filtered_df['amount']
                                      <= filters['amount_max']]

        # Status filter
        if 'status' in filters:
            if isinstance(filters['status'], list):
                filtered_df = filtered_df[filtered_df['status'].isin(
                    filters['status'])]
            else:
                filtered_df = filtered_df[filtered_df['status']
                                          == filters['status']]

        return filtered_df