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


def test_get_ticket_details_returns_none_for_unknown_ticket_or_email(tmp_path):
    database = SupportTicketDatabase(str(tmp_path / "support.db"))
    ticket_number = database.create_ticket(
        "customer@example.com", "My card was blocked", "debit_card")

    assert database.get_ticket_details("unknown-ticket", "customer@example.com") is None
    assert database.get_ticket_details(ticket_number, "other@example.com") is None
