import app
import json
import os
import sqlite3
import sys
import tempfile
from datetime import date

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_enforce_safe_query_adds_limit():
    safe = app.enforce_safe_query("SELECT id, amount FROM fintech", {"fintech"}, {
                                  "id", "amount", "status", "date", "description"})
    assert "LIMIT 1000" in safe


def test_enforce_safe_query_appends_limit_before_trailing_semicolon():
    safe = app.enforce_safe_query(
        "SELECT id FROM fintech;", {"fintech"}, {"id"}
    )
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE TABLE fintech (id INTEGER)")
        conn.execute("INSERT INTO fintech VALUES (1)")
        assert conn.execute(safe).fetchall() == [(1,)]
    finally:
        conn.close()


def test_enforce_safe_query_allows_semicolon_inside_string():
    safe = app.enforce_safe_query(
        "SELECT description FROM fintech "
        "WHERE description = 'Payment; pending'",
        {"fintech"},
        {"description"},
    )
    assert "LIMIT 1000" in safe


def test_enforce_safe_query_rejects_multiple_statements():
    with pytest.raises(Exception, match="semicolons are not permitted"):
        app.enforce_safe_query(
            "SELECT id FROM fintech; SELECT amount FROM fintech;",
            {"fintech"},
            {"id", "amount"},
        )


def test_enforce_safe_query_rejects_non_select():
    with pytest.raises(Exception, match="Only SELECT queries are allowed"):
        app.enforce_safe_query("DELETE FROM fintech", {
                               "fintech"}, {"id", "amount"})

def test_enforce_safe_query_rejects_unsafe_statement():
    with pytest.raises(Exception, match="Unsafe SQL: DDL/DML commands are not allowed"):
        app.enforce_safe_query(
            "SELECT * FROM fintech; DROP TABLE fintech;", {"fintech"}, {"id", "amount"})


def test_enforce_safe_query_rejects_bad_table():
    with pytest.raises(Exception, match="Table 'users' is not in the allowed whitelist"):
        app.enforce_safe_query("SELECT * FROM users",
                               {"fintech"}, {"id", "amount"})


def test_enforce_safe_query_rejects_bad_column():
    with pytest.raises(Exception, match="Column 'password' is not in the allowed whitelist"):
        app.enforce_safe_query("SELECT password FROM fintech", {
                               "fintech"}, {"id", "amount"})


def test_validate_sql_query_ignores_parentheses_inside_string_values():
    is_valid, error = app.validate_sql_query(
        "SELECT description FROM fintech "
        "WHERE description = 'Please call (now'"
    )

    assert is_valid is True
    assert error is None


def test_validate_sql_query_rejects_unmatched_sql_parenthesis():
    is_valid, error = app.validate_sql_query(
        "SELECT (amount FROM fintech"
    )

    assert is_valid is False
    assert error == "❌ SQL syntax error: Unmatched parentheses"


@pytest.mark.parametrize(
    "response",
    [
        "```sql\r\nSELECT amount FROM fintech\r\n```",
        "```SQL\nSELECT amount FROM fintech\n```",
        "```\nSELECT amount FROM fintech\n```",
    ],
)
def test_extract_sql_from_response_handles_fenced_sql(response):
    assert app.extract_sql_from_response(response) == "SELECT amount FROM fintech"


def test_read_sql_query_with_params_and_introspect_schema():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE fintech (id INTEGER PRIMARY KEY, amount FLOAT, status TEXT)")
        cursor.execute(
            "INSERT INTO fintech (amount, status) VALUES (?, ?)", (123.45, 'Completed'))
        conn.commit()
        conn.close()

        columns = app.introspect_schema(db_path, 'fintech')
        assert 'id' in columns and 'amount' in columns and 'status' in columns

        rows = app.read_sql_query(
            "SELECT amount FROM fintech WHERE status = ?", db_path, params=('Completed',))
        assert rows == [{"amount": 123.45}]


def test_read_sql_query_rejects_dml(tmp_path):
    db_path = str(tmp_path / "support.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE fintech (amount FLOAT)")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        app.read_sql_query("DELETE FROM fintech", db_path)


def test_read_sql_query_closes_connection_when_execution_fails(monkeypatch):
    class FailingCursor:
        def execute(self, sql, params=None):
            raise sqlite3.OperationalError("query failed")

    class TrackedConnection:
        closed = False

        def cursor(self):
            return FailingCursor()

        def set_progress_handler(self, callback, instruction_interval):
            pass

        def close(self):
            self.closed = True

    connection = TrackedConnection()
    monkeypatch.setattr(
        app.sqlite3, "connect", lambda db, timeout: connection
    )

    with pytest.raises(sqlite3.OperationalError, match="query failed"):
        app.read_sql_query("SELECT value FROM items", "unused.db")

    assert connection.closed


def test_read_sql_query_interrupts_long_running_query(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "QUERY_TIMEOUT_SECONDS", 1)
    clock_values = iter([10, 12])
    monkeypatch.setattr(app.time, "monotonic", lambda: next(clock_values))

    query = (
        "WITH RECURSIVE numbers(value) AS ("
        "VALUES(0) UNION ALL SELECT value + 1 FROM numbers "
        "WHERE value < 10000) SELECT sum(value) FROM numbers"
    )

    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        app.read_sql_query(query, str(tmp_path / "timeout.db"))


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        (date(2024, 6, 1), date(2024, 6, 30)),
        (date(2024, 6, 15), date(2024, 6, 15)),
        (None, date(2024, 6, 30)),
        (date(2024, 6, 1), None),
    ],
)
def test_validate_report_date_range_accepts_valid_or_partial_ranges(
    start_date, end_date
):
    app._validate_report_date_range(start_date, end_date)


def test_validate_report_date_range_rejects_start_after_end():
    with pytest.raises(
        ValueError, match="Start date must be on or before end date"
    ):
        app._validate_report_date_range(date(2024, 7, 1), date(2024, 6, 30))


def test_format_results_to_text_fallback_when_no_genai():
    # Simulate no SDK by temporarily patching app.genai
    original_genai = app.genai
    app.genai = None
    try:
        result = app.format_results_to_text('How much?', [(123, )])
        assert 'Auto answer fallback' in result
    finally:
        app.genai = original_genai


def test_format_results_to_text_reports_empty_results_without_calling_gemini(
    monkeypatch,
):
    class UnexpectedGeminiCall:
        def GenerativeModel(self, model_name):
            raise AssertionError("Gemini should not be called for empty results")

    monkeypatch.setattr(app, "genai", UnexpectedGeminiCall())

    result = app.format_results_to_text("Find missing records", [])

    assert result == "No results were found for your query."


def test_format_results_as_json_serializes_query_rows():
    results = app.pd.DataFrame(
        [{"transaction_id": 7, "amount": 12.5, "status": "Completed"}]
    )

    serialized = app.format_results_as_json(results)

    assert json.loads(serialized) == [
        {"transaction_id": 7, "amount": 12.5, "status": "Completed"}
    ]
