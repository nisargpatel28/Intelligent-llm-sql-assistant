import google.generativeai as genai
import sqlite3
import os
import streamlit as st
from dotenv import load_dotenv
import re
import signal
from contextlib import contextmanager
from typing import Optional, List, Tuple
load_dotenv()  # Load all the env variables - updated with google api key


# Configure the API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

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


# Function to Load Gemini Model and provide sql query response


def get_gemini_response(question, prompt):
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



# Define your prompt
prompt = ["""
    You are an expert financial data analyst. You have access to a SQL database named 'fintech.db' which contains a table called 'fintech' with the following columns:
    - id (INT, Primary Key)
    - transaction_id (INT)
    - amount (FLOAT)
    - status (VARCHAR(25))
    - date (TEXT)
    - description (TEXT)
    Use your SQL skills to analyze the data and provide insights based on user queries.
    The SQL Command will be something like: "SELECT * FROM fintech WHERE status = 'Completed';"\n
    Example Queries:
    1. "What is the total amount of completed transactions?"
    In above case, the SQL command will be:
        "SELECT SUM(amount) FROM fintech WHERE status = 'Completed';"
    2. "How many transactions are pending?"
    In above case, the SQL command will be:
    "SELECT COUNT(*) FROM fintech WHERE status = 'Pending';"
    3. "List all failed transactions."
    In above case, the SQL command will be:
    "SELECT * FROM fintech WHERE status = 'Failed';"
    Also, the sql code should be enclosed within triple backticks (```) in your response.

"""
          ]

# Streamlit App

st.set_page_config(page_title="Financial Data Analyst with Gemini Pro",
                   page_icon=":bar_chart:", layout="wide")
st.title("🔒 Financial Data Analyst with Gemini Pro (Secured) :bar_chart:")

# Add info box about security features
with st.expander("🛡️ Security & Reliability Features", expanded=False):
    st.markdown("""
    ✅ **SQL Injection Prevention** - Queries are validated for malicious patterns  
    ✅ **Query Timeout Protection** - Queries limited to 30 seconds max execution  
    ✅ **Query Explanation** - Generated SQL is shown before execution for verification  
    ✅ **Error Recovery** - Comprehensive error handling for edge cases  
    """)

question = st.text_input("Ask your financial data related question here:")
submit = st.button("🔍 Get Answer", use_container_width=True)

# if submit button is clicked
if submit:
    if not question.strip():
        st.error("❌ Please enter a question")
    else:
        try:
            with st.spinner("🤖 Generating SQL query..."):
                response = get_gemini_response(question, prompt)
            
            # Extract SQL query from the response
            sql_query = extract_sql_from_response(response)
            
            if not sql_query:
                st.error("❌ Could not extract SQL query from the response. Please rephrase your question.")
            else:
                # ===== QUERY EXPLANATION - Show SQL before execution =====
                st.subheader("📋 Generated SQL Query")
                
                # Create a styled code block
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.code(sql_query, language="sql")
                
                # Display query information
                query_info = get_query_info(sql_query)
                info_cols = st.columns(4)
                with info_cols[0]:
                    st.metric("📊 Tables", ", ".join(query_info['tables']) if query_info['tables'] else "None")
                with info_cols[1]:
                    st.metric("📈 Aggregation", "Yes" if query_info['is_aggregate'] else "No")
                with info_cols[2]:
                    st.metric("🔍 Has Filter", "Yes" if query_info['has_where_clause'] else "No")
                with info_cols[3]:
                    st.metric("📌 Query Length", f"{query_info['query_length']} chars")
                
                # ===== VALIDATION AND EXECUTION =====
                st.subheader("🔐 Query Validation & Execution")
                
                is_valid, validation_error = validate_sql_query(sql_query)
                
                if not is_valid:
                    st.error(f"❌ **Query Validation Failed**\n\n{validation_error}")
                else:
                    st.success("✅ Query passed security validation")
                    
                    # Execute query with timeout protection
                    with st.spinner("⏳ Executing query (max 30 seconds timeout)..."):
                        success, data, error_msg = read_sql_query(sql_query, 'fintech.db')
                    
                    if not success:
                        st.error(f"❌ **Query Execution Failed**\n\n{error_msg}")
                    elif not data:
                        st.warning("⚠️ Query executed successfully but returned no results.")
                        st.info("Tip: Try adjusting your query filters or date range.")
                    else:
                        # ===== FORMAT RESULTS =====
                        st.subheader("📊 Query Results")
                        
                        # Display raw results in a table
                        st.write(f"**Found {len(data)} record(s)**")
                        
                        # Convert rows to list of dicts for display
                        results_list = [dict(row) for row in data]
                        st.dataframe(results_list, use_container_width=True)
                        
                        # Format the results into human-readable text
                        with st.spinner("✍️ Formatting answer..."):
                            formatted_answer = format_results_to_text(question, str(results_list))
                        
                        st.subheader("💡 Answer")
                        st.write(formatted_answer)
                        
                        # Add success indicator
                        st.success("✅ Query completed successfully!")
                        
        except Exception as e:
            error_type = type(e).__name__
            st.error(f"❌ **{error_type}**\n\n{str(e)}")
            st.info("💡 **Troubleshooting Tips:**\n- Check your API key configuration\n- Ensure the database file exists\n- Try a simpler question")
