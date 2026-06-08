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

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess data for reporting"""
        processed = df.copy()

        # Convert date column
        if 'date' in processed.columns:
            processed['date'] = pd.to_datetime(
                processed['date'], errors='coerce')
            processed['month'] = processed['date'].dt.to_period('M')
            processed['week'] = processed['date'].dt.to_period('W')
            processed['day_of_week'] = processed['date'].dt.day_name()

        # Convert amount to numeric
        processed['amount'] = pd.to_numeric(
            processed['amount'], errors='coerce')

        return processed

    def _generate_summary_report(self, df: pd.DataFrame) -> Dict:
        """Generate a summary report"""
        report = {
            "title": "Transaction Summary Report",
            "generated_at": datetime.now().isoformat(),
            "period": self._get_date_range(df),
            "sections": {}
        }

        # Overview section
        report["sections"]["overview"] = {
            "total_transactions": len(df),
            "total_amount": float(df['amount'].sum()),
            "average_amount": float(df['amount'].mean()),
            "unique_statuses": df['status'].value_counts().to_dict() if 'status' in df.columns else {}
        }

        # Trends section
        if 'date' in df.columns:
            daily_totals = df.groupby(df['date'].dt.date)['amount'].sum()
            report["sections"]["trends"] = {
                "daily_average": float(daily_totals.mean()),
                "peak_day": str(daily_totals.idxmax()),
                "peak_amount": float(daily_totals.max())
            }

        # Insights section
        report["sections"]["insights"] = self._generate_insights(df)

        # Charts
        report["charts"] = self._generate_charts(
            df, ["amount_distribution", "status_pie"])

        return report

    def _generate_detailed_report(self, df: pd.DataFrame) -> Dict:
        """Generate a detailed analysis report"""
        report = {
            "title": "Detailed Transaction Analysis Report",
            "generated_at": datetime.now().isoformat(),
            "period": self._get_date_range(df),
            "sections": {}
        }

        # Overview
        report["sections"]["overview"] = self._generate_summary_report(df)[
            "sections"]["overview"]

        # Breakdown by status
        if 'status' in df.columns:
            status_breakdown = df.groupby('status').agg({
                'amount': ['count', 'sum', 'mean', 'min', 'max']
            }).round(2)
            report["sections"]["breakdown"] = {
                "by_status": status_breakdown.to_dict(),
                "large_transactions": df.nlargest(10, 'amount')[['amount', 'status', 'date']].to_dict('records')
            }

        # Anomalies (simplified detection)
        anomalies = self._detect_simple_anomalies(df)
        report["sections"]["anomalies"] = anomalies

        # Recommendations
        report["sections"]["recommendations"] = self._generate_recommendations(
            df, anomalies)

        # Charts
        report["charts"] = self._generate_charts(
            df, ["time_series", "amount_distribution", "status_breakdown"])

        return report

    def _generate_trends_report(self, df: pd.DataFrame) -> Dict:
        """Generate a trends analysis report"""
        report = {
            "title": "Transaction Trends Report",
            "generated_at": datetime.now().isoformat(),
            "period": self._get_date_range(df),
            "sections": {}
        }

        if 'date' not in df.columns:
            report["error"] = "Date column required for trends analysis"
            return report

        # Overview
        report["sections"]["overview"] = {
            "total_transactions": len(df),
            "date_range": self._get_date_range(df),
            "avg_daily_transactions": float(len(df) / max(1, (df['date'].max() - df['date'].min()).days))
        }

        # Temporal analysis
        temporal = {}

        # Monthly trends
        monthly = df.groupby('month')['amount'].agg(['count', 'sum', 'mean'])
        temporal["monthly"] = monthly.to_dict()

        # Weekly patterns
        weekly = df.groupby('day_of_week')['amount'].agg(
            ['count', 'sum', 'mean'])
        temporal["weekly"] = weekly.to_dict()

        # Hourly patterns (if time data available)
        if df['date'].dt.time.notna().any():
            hourly = df.groupby(df['date'].dt.hour)[
                'amount'].agg(['count', 'sum'])
            temporal["hourly"] = hourly.to_dict()

        report["sections"]["temporal_analysis"] = temporal

        # Patterns
        report["sections"]["patterns"] = self._analyze_patterns(df)

        # Charts
        report["charts"] = self._generate_charts(
            df, ["trends_over_time", "weekly_patterns", "monthly_comparison"])

        return report

    def _generate_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate AI-powered insights"""
        insights = []

        try:
            # Basic statistical insights
            total_amount = df['amount'].sum()
            avg_amount = df['amount'].mean()
            max_amount = df['amount'].max()

            insights.append(f"Total transaction volume: ${total_amount:,.2f}")
            insights.append(f"Average transaction amount: ${avg_amount:,.2f}")
            insights.append(f"Largest transaction: ${max_amount:,.2f}")

            if 'status' in df.columns:
                status_counts = df['status'].value_counts()
                most_common_status = status_counts.index[0]
                insights.append(
                    f"Most common transaction status: {most_common_status} ({status_counts[most_common_status]} transactions)")

            # AI-powered insights if available
            if GEMINI_AVAILABLE and len(df) > 10:
                ai_insights = self._get_ai_insights(df)
                insights.extend(ai_insights)

        except Exception as e:
            insights.append(f"Error generating insights: {str(e)}")

        return insights

    def _get_ai_insights(self, df: pd.DataFrame) -> List[str]:
        """Get AI-generated insights using Gemini"""
        try:
            # Prepare data summary for AI
            summary = {
                "total_transactions": len(df),
                "total_amount": float(df['amount'].sum()),
                "avg_amount": float(df['amount'].mean()),
                "status_distribution": df['status'].value_counts().to_dict() if 'status' in df.columns else {},
                "date_range": self._get_date_range(df)
            }

            prompt = f"""
            Analyze this transaction data summary and provide 3-5 key business insights:

            {json.dumps(summary, indent=2)}

            Focus on:
            - Transaction patterns
            - Potential business implications
            - Areas for improvement
            - Risk indicators

            Return only a JSON array of insight strings.
            """

            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)

            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            insights = json.loads(response_text)
            return insights if isinstance(insights, list) else []

        except Exception as e:
            print(f"Error getting AI insights: {e}")
            return []

    def _detect_simple_anomalies(self, df: pd.DataFrame) -> Dict:
        """Simple anomaly detection for reports"""
        anomalies = {"high_value": [], "unusual_patterns": []}

        try:
            # High value transactions (top 5%)
            threshold = df['amount'].quantile(0.95)
            high_value = df[df['amount'] >= threshold][[
                'amount', 'status', 'date']].head(10)
            anomalies["high_value"] = high_value.to_dict('records')

            # Check for unusual status patterns
            if 'status' in df.columns:
                status_counts = df['status'].value_counts()
                total = len(df)
                unusual_statuses = []

                for status, count in status_counts.items():
                    percentage = (count / total) * 100
                    if percentage < 1:  # Less than 1% of transactions
                        unusual_statuses.append({
                            "status": status,
                            "count": int(count),
                            "percentage": round(percentage, 2)
                        })

                anomalies["unusual_patterns"] = unusual_statuses

        except Exception as e:
            anomalies["error"] = str(e)

        return anomalies

    def _generate_recommendations(self, df: pd.DataFrame, anomalies: Dict) -> List[str]:
        """Generate recommendations based on data analysis"""
        recommendations = []

        try:
            # Basic recommendations
            if len(anomalies.get("high_value", [])) > 0:
                recommendations.append(
                    "Monitor high-value transactions for fraud prevention")

            if 'status' in df.columns:
                failed_count = len(df[df['status'] == 'Failed'])
                if failed_count > len(df) * 0.1:  # More than 10% failed
                    recommendations.append(
                        "Investigate high failure rate in transactions")

            # AI-powered recommendations
            if GEMINI_AVAILABLE:
                ai_recs = self._get_ai_recommendations(df, anomalies)
                recommendations.extend(ai_recs)

        except Exception as e:
            recommendations.append(
                f"Error generating recommendations: {str(e)}")

        return recommendations

    def _get_ai_recommendations(self, df: pd.DataFrame, anomalies: Dict) -> List[str]:
        """Get AI-generated recommendations"""
        try:
            context = {
                "total_transactions": len(df),
                "anomaly_count": len(anomalies.get("high_value", [])),
                "status_distribution": df['status'].value_counts().to_dict() if 'status' in df.columns else {}
            }

            prompt = f"""
            Based on this transaction analysis context, provide 2-3 actionable business recommendations:

            {json.dumps(context, indent=2)}

            Focus on operational improvements, risk management, and business optimization.
            Return only a JSON array of recommendation strings.
            """

            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)

            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            recommendations = json.loads(response_text)
            return recommendations if isinstance(recommendations, list) else []

        except Exception as e:
            print(f"Error getting AI recommendations: {e}")
            return []

    def _analyze_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze transaction patterns"""
        patterns = {}

        try:
            # Peak hours/days
            if df['date'].dt.hour.notna().any():
                hourly_volume = df.groupby(df['date'].dt.hour).size()
                peak_hour = hourly_volume.idxmax()
                patterns["peak_hour"] = int(peak_hour)

            daily_volume = df.groupby(df['date'].dt.day_name()).size()
            peak_day = daily_volume.idxmax()
            patterns["peak_day"] = peak_day

            # Seasonal patterns
            monthly_volume = df.groupby(df['date'].dt.month).size()
            patterns["monthly_distribution"] = monthly_volume.to_dict()

        except Exception as e:
            patterns["error"] = str(e)

        return patterns

    def _generate_charts(self, df: pd.DataFrame, chart_types: List[str]) -> Dict:
        """Generate base64 encoded charts"""
        charts = {}

        try:
            for chart_type in chart_types:
                if chart_type == "amount_distribution":
                    charts["amount_distribution"] = self._create_amount_distribution_chart(
                        df)
                elif chart_type == "status_pie":
                    charts["status_pie"] = self._create_status_pie_chart(df)
                elif chart_type == "time_series":
                    charts["time_series"] = self._create_time_series_chart(df)
                elif chart_type == "trends_over_time":
                    charts["trends_over_time"] = self._create_trends_chart(df)
                # Add more chart types as needed

        except Exception as e:
            charts["error"] = str(e)

        return charts

    def _create_amount_distribution_chart(self, df: pd.DataFrame) -> str:
        """Create amount distribution histogram"""
        plt.figure(figsize=(10, 6))
        plt.hist(df['amount'], bins=50, alpha=0.7,
                 color='blue', edgecolor='black')
        plt.title('Transaction Amount Distribution')
        plt.xlabel('Amount ($)')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)

        return self._encode_plot_to_base64()

    def _create_status_pie_chart(self, df: pd.DataFrame) -> str:
        """Create status distribution pie chart"""
        if 'status' not in df.columns:
            return ""

        plt.figure(figsize=(8, 8))
        status_counts = df['status'].value_counts()
        plt.pie(status_counts.values,
                labels=status_counts.index, autopct='%1.1f%%')
        plt.title('Transaction Status Distribution')

        return self._encode_plot_to_base64()

    def _create_time_series_chart(self, df: pd.DataFrame) -> str:
        """Create time series chart"""
        if 'date' not in df.columns:
            return ""

        plt.figure(figsize=(12, 6))
        daily_totals = df.groupby(df['date'].dt.date)['amount'].sum()
        plt.plot(daily_totals.index, daily_totals.values,
                 marker='o', linestyle='-')
        plt.title('Daily Transaction Totals')
        plt.xlabel('Date')
        plt.ylabel('Total Amount ($)')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)

        return self._encode_plot_to_base64()