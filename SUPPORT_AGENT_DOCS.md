# Agentic AI Support Router - Documentation

## Overview

The Support Agent is an intelligent agentic AI system that automatically classifies customer queries and routes them to the appropriate support channel. It uses:

- **LLM (Large Language Model)**: Google Gemini API for natural language understanding and query analysis
- **RAG (Retrieval-Augmented Generation)**: Vector database for enhanced query classification
- **Vector DB (ChromaDB)**: FAISS-backed vector store for semantic similarity matching
- **Email Notifications**: Automated support ticket creation and notification system

## Features

### 1. Intelligent Query Classification
The system analyzes incoming queries and classifies them into predefined categories:
- **Bank Account**: Account balance, statements, verification, closure, settings
- **Debit Card**: Card blocking, fraud, replacement, PIN issues
- **Cross-Border Transactions**: International transfers, forex, SWIFT transfers
- **KYC/Identity Verification**: Document verification, compliance checks

### 2. Automatic Ticket Creation
- Creates unique ticket numbers with timestamp (e.g., `TKT-20240627143022`)
- Stores ticket details in SQLite database
- Tracks ticket status, priority, and creation time

### 3. Email Notifications
- Sends notifications to support team when tickets are created
- Sends confirmation emails to customers
- Requires SMTP configuration (Gmail recommended)

### 4. RAG-Enhanced Classification
- Uses ChromaDB for vector similarity search
- Implements HNSW (Hierarchical Navigable Small World) algorithm
- Provides confidence scores for classifications

## Architecture

```
Customer Query
    ↓
[Support Agent]
    ↓
[LLM Analysis] → [Vector Classification]
    ↓
Decision: Route to Support or Handle via AI?
    ↓
├─ YES → Create Ticket → Send Emails → Update Database
└─ NO → Handle via AI Assistant
```

## Database Schema

### support_tickets table
```
- id: Auto-increment primary key
- ticket_number: Unique ticket identifier (TKT-YYYYMMDDHHMMSS)
- user_email: Customer email address
- user_query: Original customer query
- category: Classification category
- priority: "high" or "medium"
- status: "open", "in_progress", "resolved", "closed"
- created_at: Timestamp of ticket creation
- updated_at: Last update timestamp
- assigned_to: Support staff member assigned
- resolution_notes: Notes on ticket resolution
- email_sent: Boolean flag (1 = sent, 0 = not sent)
- email_sent_at: Timestamp of email notification
```

## Configuration

### Required Environment Variables

```
GOOGLE_API_KEY=<your_gemini_api_key>
```

### Optional Email Configuration

To enable email notifications, add:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SUPPORT_EMAIL=support@example.com
SUPPORT_EMAIL_PASSWORD=<app_password>
SUPPORT_TEAM_EMAIL=team@example.com
```

**Gmail Setup Instructions:**
1. Enable 2-Step Verification on your Google Account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the generated password in `SUPPORT_EMAIL_PASSWORD`

## Usage

### In Streamlit App (Tab 2: Support Routing)

```python
# The support agent is automatically initialized
support_agent = get_support_agent()

# Process a customer query
result = support_agent.process_query(
    user_query="My debit card was blocked",
    user_email="customer@example.com"
)

# result structure:
{
    "query": "My debit card was blocked",
    "routed_to_support": True,
    "ticket_number": "TKT-20240627143022",
    "category": "debit_card",
    "confidence": 0.92,
    "message": "✅ Your query has been escalated..."
}
```

### Direct Python Usage

```python
from support_agent import get_support_agent

agent = get_support_agent()
result = agent.process_query(
    user_query="I need to verify my identity for KYC",
    user_email="user@example.com"
)

print(f"Ticket: {result['ticket_number']}")
print(f"Routed to Support: {result['routed_to_support']}")
```

## How It Works

### Step 1: Query Analysis
The LLM analyzes the customer query against known support categories. It returns:
- `needs_support`: Boolean indicating if support is needed
- `category`: Classification category
- `confidence`: Confidence score (0-1)
- `reason`: Explanation of classification

### Step 2: Vector Classification (Backup)
If the initial analysis is uncertain, the system uses ChromaDB to find similar past queries:
- Computes embeddings for the customer query
- Searches similar queries in the vector store
- Uses cosine similarity for matching

### Step 3: Support Routing Decision
- If category is in support categories AND confidence > 0.5 → Route to support
- If routed: Create ticket, send emails, update database
- If not routed: Message returned to customer

### Step 4: Email Notifications
- **Support Team Email**: Contains ticket details and customer query
- **Customer Confirmation**: Ticket number and expected response time

## Support Categories & Keywords

### Bank Account
`'account balance', 'account statement', 'account verification', 'account closure', 'account details', 'account settings'`

### Debit Card
`'card blocked', 'card replacement', 'card declined', 'card limit', 'card activation', 'card fraud', 'card pin'`

### Cross-Border
`'international transfer', 'cross-border payment', 'forex', 'wire transfer', 'international wire', 'currency exchange', 'SWIFT'`

### KYC
`'kyc verification', 'identity verification', 'document verification', 'kyc status', 'kyc failed', 'kyc update', 'aml check'`

## Monitoring & Analytics

The app provides support statistics:
- **Open Tickets**: Currently unresolved tickets
- **Total Tickets**: All tickets created
- **Categories**: Number of unique categories with tickets

## Error Handling

### Email Not Configured
```
⚠️ Email credentials not configured. Ticket created but email not sent.
```
Tickets are still created and stored in the database, but email notifications won't be sent.

### API Quota Exceeded
Handled gracefully with user-friendly error messages directing to API quotas.

### Database Errors
Falls back to graceful degradation—features still work without statistics.

## Performance Considerations

### Vector DB Optimization
- Uses HNSW algorithm (fast approximate nearest neighbor search)
- Cosine similarity metric for semantic matching
- Persistent storage in `./support_vectors`

### Database Optimization
- Indexed on `ticket_number` (unique)
- Indexed on `category` and `status` for faster queries
- SQLite for lightweight deployment

## Future Enhancements

1. **Semantic Linking**: Connect related support tickets
2. **Knowledge Base**: Auto-generate responses from similar past tickets
3. **Multi-language Support**: Translate queries before classification
4. **Analytics Dashboard**: Visualize support metrics and trends
5. **Webhook Integration**: Send tickets to external CRM systems
6. **Agent Workflow**: Multi-step agentic flows for complex issues

## Troubleshooting

### Tickets not being created
- Check GOOGLE_API_KEY is set correctly
- Verify ChromaDB initialization (check `./support_vectors` directory)

### Emails not sending
- Verify SMTP credentials in `.env`
- For Gmail: Ensure App Password is used (not account password)
- Check firewall doesn't block SMTP port 587

### Low classification confidence
- Add more examples to vector database
- Adjust confidence threshold in `should_route_to_support()`
- Consider training on domain-specific data

## License

Same as main project - Check LICENSE file
