# Quick Start Guide - Agentic AI Support Router

## Installation Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

New packages added:
- `langchain` & `langchain-core`: AI orchestration framework
- `langchain-google-genai`: Google Gemini integration
- `chromadb`: Vector database for RAG
- `faiss-cpu`: Efficient vector similarity search
- `pydantic`: Data validation
- `email-validator`: Email address validation

### 2. Update Environment Variables

Copy and update the `.env` file with your API keys:

```bash
# Required
GOOGLE_API_KEY=your_key_here

# Optional (for email notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SUPPORT_EMAIL=your_email@gmail.com
SUPPORT_EMAIL_PASSWORD=your_app_password
SUPPORT_TEAM_EMAIL=support_team@yourcompany.com
```

**For Gmail with App Passwords:**
1. Go to https://myaccount.google.com/apppasswords
2. Select Mail and Windows Computer
3. Generate and copy the 16-character password
4. Paste it in `SUPPORT_EMAIL_PASSWORD`

### 3. Run the Application

```bash
streamlit run app.py
```

## Features Overview

### Tab 1: Financial Data Query (Original)
- Ask questions about financial transactions
- AI generates SQL queries automatically
- Results formatted in human-readable text

### Tab 2: Support Routing (NEW) 🎯
- Describe your issue or question
- System automatically classifies and routes to support if needed
- Get instant ticket number and confirmation

## How It Works

### Query Classification
The AI analyzes your query against 4 support categories:

1. **🏦 Bank Account**: Account balance, statements, verification, closures
2. **💳 Debit Card**: Blocked cards, fraud, replacements, PIN issues
3. **🌍 Cross-Border**: International transfers, forex, SWIFT
4. **🆔 KYC**: Identity verification, document checks, compliance

### Automatic Actions on Support Routing

1. ✅ **Ticket Creation**: Unique ticket number assigned (TKT-YYYYMMDDHHMMSS)
2. 📧 **Email Notifications**: 
   - Support team gets ticket details
   - Customer gets confirmation email
3. 💾 **Database Tracking**: Full ticket history in SQLite
4. 🔍 **Vector Classification**: Uses RAG for semantic matching

### Example Queries That Get Routed to Support

✅ Will be routed:
- "My debit card was declined at the ATM"
- "I need to verify my identity for KYC"
- "How do I make an international wire transfer?"
- "Can you help me close my account?"

❌ Won't be routed:
- "How many transactions did I have last week?"
- "What's my account balance?"
- "When was my last payment processed?"

## Support Agent Components

### 1. **SupportAgent**
Main orchestrator that:
- Analyzes queries using LLM
- Makes routing decisions
- Processes tickets

### 2. **VectorRAGClassifier**
Uses ChromaDB for:
- Semantic similarity matching
- Learning from past queries
- Confidence scoring

### 3. **SupportTicketDatabase**
Manages SQLite database:
- Creates tickets with unique IDs
- Tracks ticket status and history
- Stores customer information

### 4. **SupportEmailNotifier**
Handles email operations:
- Sends team notifications
- Sends customer confirmations
- Graceful handling if email not configured

## Database Files Created

- `support_tickets.db`: Support ticket storage
- `support_vectors/`: Vector embeddings for RAG

## Monitoring Support Tickets

The app shows real-time statistics:
- **Open Tickets**: Unresolved issues
- **Total Tickets**: All tickets created
- **Categories**: Number of issue types

## Troubleshooting

### "Email credentials not configured"
- Tickets are still created!
- Just configure `.env` with email settings to enable notifications

### "API Quota Exceeded"
- Check your Google API quota at https://console.cloud.google.com/
- Wait a few moments and try again

### Vector DB not initializing
- Ensure `./support_vectors` directory is writable
- Check disk space availability

## Testing the System

### Test Query 1: Debit Card Issue
```
Email: test@example.com
Query: "My debit card has been blocked, and I can't make purchases"
Expected: Routed to support with ticket creation
```

### Test Query 2: Simple Question
```
Email: test@example.com
Query: "How many transactions were completed today?"
Expected: Handled by AI, no support ticket
```

### Test Query 3: KYC Verification
```
Email: test@example.com
Query: "I need to update my KYC documents for verification"
Expected: Routed to support with HIGH priority
```

## Architecture Diagram

```
┌─────────────────────┐
│  Customer Query     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  LLM Analysis       │ ← Gemini API
│ (Category, Score)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Vector RAG Match    │ ← ChromaDB + FAISS
│ (Confidence Check)  │
└──────────┬──────────┘
           │
      ┌────┴─────┐
      │           │
      ▼           ▼
  Route to     Handle via
  Support        AI Only
      │           
      ▼           
  Create Ticket  
      │
      ├─→ SQLite Database
      ├─→ Email Notification (optional)
      └─→ Vector Store Update
```

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Update `.env` with your API keys
3. Run: `streamlit run app.py`
4. Try Tab 2 - Support Routing with test queries
5. Check `SUPPORT_AGENT_DOCS.md` for detailed documentation

## Support

For detailed technical documentation, see: [SUPPORT_AGENT_DOCS.md](SUPPORT_AGENT_DOCS.md)

## Key Features Summary

| Feature | Technology | Purpose |
|---------|------------|---------|
| LLM Analysis | Google Gemini API | Query understanding |
| Vector Classification | ChromaDB + FAISS | RAG-based similarity |
| Database | SQLite | Ticket persistence |
| Email | SMTP | Team notifications |
| Orchestration | LangChain | Agent workflow |

---

**Created:** February 27, 2026
**Status:** Production Ready ✅
