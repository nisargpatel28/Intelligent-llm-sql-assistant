import sqlite3

import pytest

from support_agent import SupportTicketDatabase


def test_get_ticket_details_requires_matching_email(tmp_path):
    database = SupportTicketDatabase(str(tmp_path / "support.db"))
    ticket_number = database.create_ticket(
        "Customer@example.com", "My card was blocked", "debit_card")

    ticket = database.get_ticket_details(ticket_number, "customer@example.com")

    assert ticket is not None
    assert ticket["ticket_number"] == ticket_number
    assert ticket["category"] == "debit_card"
    assert ticket["priority"] == "medium"
    assert ticket["status"] == "open"
    assert ticket["created_at"]
    assert ticket["updated_at"]


def test_get_ticket_details_returns_none_for_unknown_ticket_or_email(tmp_path):
    database = SupportTicketDatabase(str(tmp_path / "support.db"))
    ticket_number = database.create_ticket(
        "customer@example.com", "My card was blocked", "debit_card")

    assert database.get_ticket_details("unknown-ticket", "customer@example.com") is None
    assert database.get_ticket_details(ticket_number, "other@example.com") is None


def test_update_ticket_status_rejects_unknown_status_without_changing_ticket(tmp_path):
    database = SupportTicketDatabase(str(tmp_path / "support.db"))
    ticket_number = database.create_ticket(
        "customer@example.com", "My card was blocked", "debit_card")

    with pytest.raises(ValueError, match="Invalid ticket status 'pending'"):
        database.update_ticket_status(ticket_number, "pending")

    ticket = database.get_ticket_details(ticket_number, "customer@example.com")
    assert ticket is not None
    assert ticket["status"] == "open"


def test_update_ticket_status_accepts_supported_status(tmp_path):
    database = SupportTicketDatabase(str(tmp_path / "support.db"))
    ticket_number = database.create_ticket(
        "customer@example.com", "My card was blocked", "debit_card")

    conn = sqlite3.connect(database.db_path)
    conn.execute(
        "UPDATE support_tickets SET updated_at = '2000-01-01 00:00:00' "
        "WHERE ticket_number = ?",
        (ticket_number,),
    )
    conn.commit()
    conn.close()

    database.update_ticket_status(ticket_number, "in_progress")

    ticket = database.get_ticket_details(ticket_number, "customer@example.com")
    assert ticket is not None
    assert ticket["status"] == "in_progress"
    assert ticket["updated_at"] != "2000-01-01 00:00:00"
