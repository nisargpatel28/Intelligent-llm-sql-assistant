try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None

import sqlite3
import os
import streamlit as st
from dotenv import load_dotenv
import re
import signal
from contextlib import contextmanager
from typing import Optional, List, Tuple
from support_agent import get_support_agent


# Import AI features
from ai_features.conversation.manager import ConversationManager
from ai_features.suggestions.predictor import QueryPredictor
from ai_features.anomaly_detection.detector import AnomalyDetector
from ai_features.report_generation.generator import ReportGenerator
from mcp.client.mcp_client import MCPClientManager
from tools.external.external_tools import external_tools_manager

load_dotenv()  # Load all the env variables - updated with google api key


# Configure the API key
if genai:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize support agent for ticket routing
support_agent = get_support_agent()

# Constants for query validation and timeout
QUERY_TIMEOUT_SECONDS = 30
ALLOWED_KEYWORDS = {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 
                    'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'JOIN', 
                    'INNER', 'LEFT', 'RIGHT', 'ON', 'AS', 'COUNT', 'SUM', 'AVG', 
                    'MIN', 'MAX', 'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
                    'CAST', 'BETWEEN', 'IS', 'NULL', 'ASC', 'DESC', 'UNION', 'ALL'}
DANGEROUS_KEYWORDS = {'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE',
                      'EXEC', 'EXECUTE', 'SCRIPT', 'PRAGMA', 'VACUUM', 'ATTACH', 'DETACH'}


# Timeout handler for query execution
class TimeoutException(Exception):
    """Raised when query execution exceeds timeout"""
    pass


@contextmanager
def time_limit(seconds: int):
    """Context manager to enforce timeout on database operations"""
    def signal_handler(signum, frame):
        raise TimeoutException(f"Query execution exceeded {seconds} seconds timeout")
    
    # Note: signal.alarm only works on Unix-like systems
    # For Windows compatibility, we'll use a different approach
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)  # Cancel the alarm


# ============== SECURITY & VALIDATION FUNCTIONS ==============

def validate_sql_query(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Validate SQL query for security and syntax issues.
    Returns: (is_valid, error_message)
    """
    if not sql or not isinstance(sql, str):
        return False, "Empty or invalid SQL query provided"
    
    sql_upper = sql.upper().strip()
    
    # Check for dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf'\b{keyword}\b', sql_upper):
            return False, f"⛔ Query contains forbidden operation: {keyword}. Only SELECT queries are allowed."
    
    # Check if it's a SELECT query
    if not sql_upper.startswith('SELECT'):
        return False, "❌ Only SELECT queries are allowed. No INSERT, UPDATE, DELETE, or DDL operations permitted."
    
    # Check for common SQL injection patterns
    injection_patterns = [
        r";\s*(DROP|DELETE|INSERT|UPDATE|ALTER|EXEC|EXECUTE)",  # Stacked queries
        r"'\s*OR\s*'1'\s*=\s*'1",  # Classic OR injection
        r"--\s*$",  # SQL comments at end
        r"/\*.*?\*/",  # Multi-line comments
        r"xp_",  # Extended stored procedures
        r"sp_",  # System stored procedures
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, "⚠️ Query contains suspicious patterns that may indicate SQL injection attempt."
    
    # Check for potential schema exploration attacks
    if re.search(r'\bINFORMATION_SCHEMA\b|\bsqlite_master\b|\bsysobjects\b', sql, re.IGNORECASE):
        return False, "⛔ Access to system tables is restricted for security."
    
    # Validate basic SQL syntax
    if sql_upper.count('(') != sql_upper.count(')'):
        return False, "❌ SQL syntax error: Unmatched parentheses"
    
    return True, None


def extract_sql_from_response(response: str) -> Optional[str]:
    """
    Extract SQL query from LLM response.
    Looks for SQL within triple backticks.
    """
    sql_match = re.search(r'```(?:sql)?\s*\n?(.*?)\n?```', response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        sql_query = sql_match.group(1).strip()
        return sql_query
    return None


def get_query_info(sql: str) -> dict:
    """
    Extract information about the query for display.
    """
    sql_upper = sql.upper()
    tables = re.findall(r'\bFROM\s+(\w+)\b|\bJOIN\s+(\w+)\b', sql_upper)
    tables = [t[0] or t[1] for t in tables]
    
    is_aggregate = any(func in sql_upper for func in ['COUNT(', 'SUM(', 'AVG(', 'MIN(', 'MAX('])
    has_where = 'WHERE' in sql_upper
    has_limit = 'LIMIT' in sql_upper
    
    return {
        'tables': list(set(tables)),
        'is_aggregate': is_aggregate,
        'has_where_clause': has_where,
        'has_limit': has_limit,
        'query_length': len(sql)
    }

# Initialize AI features
conversation_manager = ConversationManager()
query_predictor = QueryPredictor()
anomaly_detector = AnomalyDetector()
report_generator = ReportGenerator()
mcp_client = MCPClientManager()

# Function to Load Gemini Model and provide sql query response


def get_gemini_response(question, prompt):
    if not genai:
        raise Exception(
            "Gemini SDK not installed. Install google-generativeai to use this feature.")

    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content([prompt[0], question])
        return response.text
    except Exception as e:
        error_message = str(e)
        if "429" in error_message or "quota" in error_message.lower() or "exceeded" in error_message.lower():
            raise Exception(
                "⚠️ API Quota Exceeded: You have reached the rate limit for the Gemini API. Please wait a few moments and try again, or check your API plan and billing details at https://ai.dev/usage")
        else:
            raise Exception(f"API Error: {error_message}")


# Function to format SQL results into human-readable text


def format_results_to_text(question, sql_results):
    if not genai:
        return f"Auto answer fallback: {question} (no Gemini SDK available)"

    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        format_prompt = f"""
    The user asked: "{question}"

    The SQL query returned the following results:
    {sql_results}

    Please provide a clear, human-readable answer based on these results.
    Format the answer in a conversational way without showing raw data tuples.
    """
        response = model.generate_content(format_prompt)
        return response.text
    except Exception as e:
        error_message = str(e)
        if "429" in error_message or "quota" in error_message.lower() or "exceeded" in error_message.lower():
            raise Exception(
                "⚠️ API Quota Exceeded: You have reached the rate limit for the Gemini API. Please wait a few moments and try again, or check your API plan and billing details at https://ai.dev/usage")
        else:
            raise Exception(f"API Error: {error_message}")


# Function to retrieve data from the sql database with timeout and error handling


def read_sql_query(sql: str, db: str) -> Tuple[bool, List, Optional[str]]:
    """
    Execute SQL query with timeout protection and comprehensive error handling.
    Returns: (success, results, error_message)
    """
    # Validate query first
    is_valid, error_msg = validate_sql_query(sql)
    if not is_valid:
        return False, [], error_msg
    
    try:
        conn = sqlite3.connect(db, timeout=QUERY_TIMEOUT_SECONDS)
        # Set row factory to return dictionaries
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Execute with timeout - use timeout on SQLite connection
        cursor.execute(f"PRAGMA busy_timeout = {QUERY_TIMEOUT_SECONDS * 1000};")
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        conn.commit()
        conn.close()
        
        # Check for empty results
        if not rows:
            return True, [], None
        
        return True, rows, None
        
    except sqlite3.OperationalError as e:
        error_msg = str(e)
        if "table" in error_msg.lower() and "does not exist" in error_msg.lower():
            return False, [], f"❌ Table not found. Please check the table name in your query."
        elif "syntax error" in error_msg.lower():
            return False, [], f"❌ SQL syntax error: {error_msg}"
        elif "no such column" in error_msg.lower():
            return False, [], f"❌ Column not found: {error_msg}"
        else:
            return False, [], f"❌ Database error: {error_msg}"
            
    except sqlite3.DatabaseError as e:
        return False, [], f"❌ Database corruption or lock issue: {str(e)}"
        
    except TimeoutException as e:
        return False, [], f"⏱️ Query execution timeout: {str(e)}"
        
    except Exception as e:
        return False, [], f"❌ Unexpected error: {str(e)}"

def read_sql_query(sql, db, params=None):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    rows = cursor.fetchall()
    conn.commit()
    conn.close()
    return rows


def introspect_schema(db, table='fintech'):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    rows = cursor.fetchall()
    conn.close()
    return [row[1] for row in rows]

# SQL injection defense:
# whitelist table/column names
# regex check for ; DROP|UPDATE|DELETE|ALTER etc


def enforce_safe_query(sql_query, allowed_tables, allowed_columns, row_limit=1000):
    normalized = sql_query.strip()
    lowered = normalized.lower()

    if not lowered.startswith("select"):
        raise Exception("Only SELECT queries are allowed in this interface.")

    if ";" in normalized and not normalized.rstrip().endswith(";"):
        raise Exception("Unsafe SQL: semicolons are not permitted in queries.")

    if re.search(r"\b(drop|delete|update|alter|insert|truncate|replace)\b", normalized, re.IGNORECASE):
        raise Exception("Unsafe SQL: DDL/DML commands are not allowed")

    # Whitelist specific table names
    for table in re.findall(r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", normalized, re.IGNORECASE):
        if table.lower() not in allowed_tables:
            raise Exception(f"Table '{table}' is not in the allowed whitelist")

    # Validate column names in SELECT (basic check)
    select_match = re.search(r"select\s+(.*?)\s+from\b",
                             normalized, re.IGNORECASE | re.DOTALL)
    if select_match:
        selected = select_match.group(1).strip()
        if selected != "*":
            for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", selected):
                lower_token = token.lower()
                if lower_token in ["as", "distinct", "count", "sum", "avg", "min", "max", "group", "by", "order", "desc", "asc"]:
                    continue
                if lower_token not in allowed_columns:
                    raise Exception(
                        f"Column '{token}' is not in the allowed whitelist")

    # Enforce row cap limit
    if not re.search(r"\blimit\b", lowered):
        normalized += f" LIMIT {row_limit}"

    return normalized


def format_conversation_history(history):
    """Format prior conversation turns into a short text block for prompt context."""
    if not history:
        return ""
    lines = []
    for msg in history:
        speaker = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"    {speaker}: {msg['content']}")
    return "\n".join(lines)


def build_prompt(schema_columns, table='fintech', conversation_history=None):
    columns_info = "\n".join([f"    - {c}" for c in schema_columns])
    history_block = ""
    if conversation_history:
        history_block = f"""
    Recent conversation history (use this to resolve follow-up questions like "that", "those", or "again"):
{conversation_history}
"""
    return [f"""
    You are an expert financial data analyst. You have access to a SQL database named 'fintech.db' which contains a table called '{table}' with the following columns:\n{columns_info}
    Use your SQL skills to analyze the data and provide insights based on user queries.
    The SQL Command should be a SELECT query and should use this exact table and columns.\n
    Carefully generate the SQL statement only; do not include data values in natural language text.
    Wrap generated SQL in triple backticks (```), optionally with language tag `sql`.
{history_block}
    Example Queries:\n
    1. \"What is the total amount of completed transactions?\"\n    SQL:\n        \"SELECT SUM(amount) FROM fintech WHERE status = 'Completed' LIMIT 1000;\"\n
    2. \"How many transactions are pending?\"\n    SQL:\n        \"SELECT COUNT(*) FROM fintech WHERE status = 'Pending' LIMIT 1000;\"\n
    3. \"List all failed transactions.\"\n    SQL:\n        \"SELECT * FROM fintech WHERE status = 'Failed' LIMIT 1000;\"\n
    Enforce safe SQL generation and do not include dangerous operations (DROP/DELETE/UPDATE/ALTER/INSERT).\n
"""
            ]

# Streamlit App


st.set_page_config(page_title="Financial Data Analyst with Gemini Pro",
                   page_icon=":bar_chart:", layout="wide")

# Create tabs for different features
tab1, tab2, tab3 = st.tabs(
    ["📊 Data Query", "🎯 Support Routing", "🤖 AI Features"])

with tab1:
    st.title("Financial Data Analyst with Gemini Pro :bar_chart:")

    query_user_id = st.text_input(
        "User ID (for conversation memory):", value="default_user", key="query_user_id")

    history = conversation_manager.get_context(query_user_id, limit=10)
    if history:
        with st.expander(f"💬 Conversation history ({len(history)} messages)"):
            for msg in history:
                st.markdown(f"**{msg['role'].title()}:** {msg['content']}")
            if st.button("Clear Conversation", key="clear_query_conversation"):
                conversation_manager.clear_context(query_user_id)
                st.rerun()

    question = st.text_input("Ask your financial data related question here:")
    query_params = st.text_input(
        "Optional query parameters (comma-separated)", "")
    submit = st.button("Get Answer")

    # if submit button is clicked
    if submit:
        if not question:
            st.error("Please enter a question before submitting")
        else:
            try:
                schema_columns = introspect_schema('fintech.db')
                conversation_history = format_conversation_history(history)
                prompt = build_prompt(schema_columns, conversation_history=conversation_history)
                response = get_gemini_response(question, prompt)
                print("Gemini Pro Response:", response)

                # Extract SQL query from the response (between triple backticks)
                sql_match = re.search(r'```(.*?)```', response, re.DOTALL)
                if sql_match:
                    sql_query = sql_match.group(1).strip()
                    # Remove 'sql' language identifier if present
                    sql_query = re.sub(
                        r'^sql\n', '', sql_query, flags=re.IGNORECASE)

                    safe_sql = enforce_safe_query(sql_query, {"fintech"}, [
                                                  c.lower() for c in schema_columns])
                    params = [p.strip()
                              for p in query_params.split(",") if p.strip()]
                    query_params_tuple = tuple(params) if params else None

                    data = read_sql_query(
                        safe_sql, 'fintech.db', params=query_params_tuple)

                    # Format the results into human-readable text
                    formatted_answer = format_results_to_text(question, data)
                    st.subheader("Answer:")
                    st.write(formatted_answer)

                    st.subheader("Executed SQL")
                    st.code(safe_sql, language='sql')

                    conversation_manager.add_message(query_user_id, "user", question)
                    conversation_manager.add_message(
                        query_user_id, "assistant", formatted_answer, metadata={"sql": safe_sql})

                else:
                    st.warning(
                        "Could not extract SQL query from the response. Generating fallback answer.")
                    fallback_text = format_results_to_text(
                        question, "No SQL results available due to missing SQL extraction.")
                    st.subheader("Fallback Answer")
                    st.write(fallback_text)

                    conversation_manager.add_message(query_user_id, "user", question)
                    conversation_manager.add_message(query_user_id, "assistant", fallback_text)
            except Exception as e:
                st.error(str(e))

with tab2:
    st.title("Agentic AI Support Router")
    st.markdown("""
    This intelligent routing system automatically classifies your query and escalates it to our support team if needed.

    **Categories that trigger automatic support routing:**
    - Bank Account Issues(balance, statements, verification, closure)
    - Debit Card Issues(blocked cards, fraud, PIN, replacements)
    - Cross-Border Transactions(international transfers, forex, SWIFT)
    - KYC/Identity Verification(document verification, compliance)
    """)

    st.subheader("Describe Your Issue")
    customer_email = st.text_input(
        "Your Email Address:", placeholder="customer@example.com")
    support_query = st.text_area("Describe your issue or question:",
                                 placeholder="E.g., 'My debit card was blocked and I need immediate assistance'",
                                 height=100)

    if st.button("Analyze & Route Query", key="support_submit"):
        if not customer_email or not support_query:
            st.error("Please provide both your email and query description")
        else:
            with st.spinner("🤖 Analyzing your query with AI..."):
                try:
                    # Process query through support agent
                    result = support_agent.process_query(
                        support_query, customer_email)

                    # Display results
                    st.divider()

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Category Detected",
                                  result["category"].replace("_", " ").title())
                    with col2:
                        st.metric("Confidence Score",
                                  f"{result['confidence']*100:.1f}%")

                    if result["routed_to_support"]:
                        st.success("✅ Query Routed to Support Team")
                        st.info(f"""
                        ** Ticket Number:** `{result['ticket_number']}`

                        {result['message']}
                        """)

                        # Show ticket details
                        with st.expander("📋 View Ticket Details"):
                            st.markdown(f"""
                            - **Category:** {result['category'].replace('_', ' ').title()}
                            - **Priority:** High
                            - **Status:** Open
                            - **Created:** {st.session_state.get('ticket_time', 'Just now')}
                            """)
                    else:
                        st.info(f"✨ {result['message']}")
                        st.info(
                            "💡 **Note:** If you believe your query needs support assistance, please contact our team directly.")

                except Exception as e:
                    st.error(f"Error processing query: {str(e)}")

    # Show support statistics
    st.divider()
    st.subheader("📈 Support Statistics")
    try:
        conn = sqlite3.connect('support_tickets.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM support_tickets WHERE status = 'open'")
        open_tickets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM support_tickets")
        total_tickets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT category) FROM support_tickets")
        categories_count = cursor.fetchone()[0]

        conn.close()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Open Tickets", open_tickets)
        with col2:
            st.metric("Total Tickets", total_tickets)
        with col3:
            st.metric("Categories", categories_count)

    except Exception as e:
        st.info(
            "📊 No support tickets yet. Statistics will appear after first ticket is created.")

with tab3:
    st.title("🤖 Advanced AI Features")
    st.markdown("""
    Explore our cutting-edge AI capabilities for enhanced financial data analysis.
    """)

    # Sub-tabs for different AI features
    ai_tab1, ai_tab2, ai_tab3, ai_tab4 = st.tabs([
        "💬 Multi-turn Conversations",
        "🔮 Query Suggestions",
        "🔍 Anomaly Detection",
        "📊 Automated Reports"
    ])

    with ai_tab1:
        st.header("💬 Multi-turn Conversation Management")
        st.markdown(
            "Maintain context across multiple interactions for more natural conversations.")

        user_id = st.text_input(
            "User ID for conversation:", value="default_user", key="conv_user_id")
        action = st.selectbox(
            "Action:", ["add", "get", "clear"], key="conv_action")

        if action == "add":
            message = st.text_area("Message to add:", key="conv_message")
            if st.button("Add Message", key="add_msg_btn"):
                conversation_manager.add_message(user_id, "user", message)
                st.success("Message added to conversation context!")
        elif action == "get":
            if st.button("Get Context", key="get_context_btn"):
                context = conversation_manager.get_context(user_id)
                st.json(context)
        elif action == "clear":
            if st.button("Clear Context", key="clear_context_btn"):
                conversation_manager.clear_context(user_id)
                st.success("Conversation context cleared!")

    with ai_tab2:
        st.header("🔮 Predictive Query Suggestions")
        st.markdown(
            "Get intelligent query suggestions based on your history and current input.")

        user_id_suggest = st.text_input(
            "User ID:", value="default_user", key="suggest_user_id")
        current_query = st.text_input(
            "Current query (optional):", key="current_query")

        if st.button("Get Suggestions", key="get_suggestions_btn"):
            suggestions = query_predictor.get_suggestions(
                user_id_suggest, current_query)
            if suggestions:
                st.subheader("Suggested Queries:")
                for i, suggestion in enumerate(suggestions, 1):
                    confidence_pct = int(suggestion.get('confidence', 0) * 100)
                    st.write(
                        f"{i}. **{suggestion['query']}** (Confidence: {confidence_pct}%)")
                    st.caption(
                        f"Type: {suggestion.get('type', 'unknown')} | Reason: {suggestion.get('reason', 'N/A')}")
            else:
                st.info("No suggestions available.")

    with ai_tab3:
        st.header("🔍 Transaction Anomaly Detection")
        st.markdown(
            "Detect unusual patterns and anomalies in your transaction data.")

        # Get sample data for demonstration
        try:
            sample_data = read_sql_query(
                "SELECT * FROM fintech LIMIT 100", 'fintech.db')
            if sample_data:
                st.subheader("Sample Transaction Data:")
                st.dataframe(sample_data[:10])  # Show first 10 rows

                threshold = st.slider(
                    "Anomaly Detection Threshold:", 0.5, 0.99, 0.95, key="anomaly_threshold")

                if st.button("Detect Anomalies", key="detect_anomalies_btn"):
                    with st.spinner("Analyzing for anomalies..."):
                        results = anomaly_detector.detect_anomalies(
                            sample_data, threshold)

                    if results.get("anomalies"):
                        st.subheader("🚨 Detected Anomalies:")
                        for anomaly in results["anomalies"][:5]:  # Show top 5
                            st.error(f"""
                            **Transaction ID:** {anomaly.get('transaction_id', 'N/A')}
                            **Amount:** ${anomaly.get('amount', 0):.2f}
                            **Reason:** {anomaly.get('reason', 'Unknown')}
                            **Method:** {anomaly.get('method', 'Unknown')}
                            """)
                    else:
                        st.success("No anomalies detected in the data.")

                    # Show statistics
                    if results.get("stats"):
                        st.subheader("📊 Data Statistics:")
                        stats = results["stats"]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Transactions",
                                      stats.get("transaction_count", 0))
                        with col2:
                            st.metric("Total Amount",
                                      f"${stats.get('total_amount', 0):,.2f}")
                        with col3:
                            st.metric("Average Amount",
                                      f"${stats.get('average_amount', 0):,.2f}")
            else:
                st.warning("No transaction data available for analysis.")
        except Exception as e:
            st.error(f"Error loading transaction data: {str(e)}")

    with ai_tab4:
        st.header("📊 Automated Report Generation")
        st.markdown(
            "Generate comprehensive reports from your transaction data.")

        report_type = st.selectbox(
            "Report Type:", ["summary", "detailed", "trends"], key="report_type")

        # Date filters
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date (optional)", key="report_start_date")
        with col2:
            end_date = st.date_input(
                "End Date (optional)", key="report_end_date")

        filters = {}
        if start_date:
            filters["date_from"] = start_date.isoformat()
        if end_date:
            filters["date_to"] = end_date.isoformat()

        if st.button("Generate Report", key="generate_report_btn"):
            try:
                # Get data for report
                data = read_sql_query("SELECT * FROM fintech", 'fintech.db')

                with st.spinner("Generating report..."):
                    report = report_generator.generate_report(
                        report_type, data, filters)

                if "error" in report:
                    st.error(f"Report generation failed: {report['error']}")
                else:
                    st.subheader(
                        f"📋 {report.get('title', 'Generated Report')}")

                    # Display report sections
                    if "sections" in report:
                        for section_name, section_data in report["sections"].items():
                            st.subheader(f"**{section_name.title()}**")
                            if isinstance(section_data, list):
                                for item in section_data:
                                    st.write(f"• {item}")
                            elif isinstance(section_data, dict):
                                st.json(section_data)
                            else:
                                st.write(section_data)

                    # Display charts if available
                    if "charts" in report and report["charts"]:
                        st.subheader("📊 Visualizations")
                        for chart_name, chart_data in report["charts"].items():
                            if chart_data and "data:image" in chart_data:
                                st.image(chart_data)
                            else:
                                st.write(f"Chart: {chart_name} - {chart_data}")

            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
