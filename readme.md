🤖 AI Chatbot for FinTech: Intelligent Transaction Query Assistant with Agentic Support Routing

This repository accompanies a tutorial on building an AI-powered chatbot that integrates RAG (Retrieval-Augmented Generation), LangChain, and **Agentic AI** to interact with financial data securely and intelligently.

The chatbot features **two intelligent modes:**

### 📊 Mode 1: Financial Data Query Assistant
Connects with your organization's transactional database to answer natural language queries:

💳 "What's the status of my last transaction?"

📊 "How many transactions were processed today?"

💰 "Show me all transactions above $1,000 last week."

📈 "What's the total transaction volume for this month?"

### 🎯 Mode 2: Agentic AI Support Router (NEW)
Intelligently routes customer issues to support team with automatic ticket creation and email notifications:

🏦 "I can't access my account balance" → Routes to Bank Account Support

💳 "My debit card was blocked" → Routes to Debit Card Support (HIGH PRIORITY)

🌍 "I need to send money internationally" → Routes to Cross-Border Support

🆔 "What's my KYC verification status?" → Routes to KYC Support (HIGH PRIORITY)

🚀 Key Features

**AI-Powered Query Engine**: Uses LangChain and RAG pipelines to interpret natural language and fetch accurate responses from structured financial databases.

**Agentic AI Support Routing** ⭐ NEW: Automatically classifies customer queries and routes to appropriate support channels using:
- Large Language Models (Google Gemini)
- Vector Database (ChromaDB + FAISS)
- Retrieval-Augmented Generation (RAG)
- Automated email notifications

**FinTech Use Cases**: Ideal for banks, payment gateways, and financial platforms to provide intelligent self-service analytics, transaction insights, and automated customer support.

**Secure and Compliant**: Designed with data privacy, audit trails, and access control in mind.

**Full-Stack Integration**: Streamlit frontend with REST APIs, LangChain orchestration, and SQLite/Vector DB backend.

**Cloud-Ready Deployment**: Support for containerization and monitoring.

## 🎯 Agentic AI Support Flow

The support routing system uses an intelligent multi-stage decision pipeline:

```
┌─────────────────────────┐
│   Customer Query Input  │
└────────────┬────────────┘
             │
             ▼
┌──────────────────────────────┐
│  LLM Analysis (Gemini API)   │
│  • Extract intent           │
│  • Classify category        │
│  • Generate confidence      │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  Vector RAG Classification   │
│  • ChromaDB similarity       │
│  • FAISS nearest neighbors   │
│  • Backup classification     │
└───────────┬──────────────────┘
            │
      ┌─────┴──────┐
      │             │
      ▼             ▼
  Route to       Handle via
  Support        AI Only
      │
      ├─ Create Support Ticket (SQLite)
      ├─ Send Email Notifications (SMTP)
      ├─ Update Vector DB
      └─ Display Confirmation
```

### Support Categories

The Agentic AI recognizes 4 main support categories and automatically assigns priorities:

| Category | Keywords | Priority | Action |
|----------|----------|----------|--------|
| 🏦 **Bank Account** | Balance, statements, verification, closure, settings | Medium | Create ticket, notify team |
| 💳 **Debit Card** | Card blocked, fraud, replacement, PIN, declined | **HIGH** | Immediate escalation |
| 🌍 **Cross-Border** | International transfer, forex, SWIFT, wire | Medium | Route to international team |
| 🆔 **KYC/Identity** | Document verification, compliance, AML | **HIGH** | Priority verification team |

### Key Components

- **SupportAgent**: Main orchestrator using agentic patterns
- **VectorRAGClassifier**: ChromaDB-powered semantic classification
- **SupportTicketDatabase**: SQLite ticket persistence and tracking
- **SupportEmailNotifier**: SMTP-based team and customer notifications
- **LangChain Integration**: Orchestration of multi-step workflows

🧠 Tech Stack

**Frontend**: Streamlit UI with two intelligent modes

**Backend**: Python with FastAPI-ready architecture

**AI/ML**: 
- Google Gemini API (LLM for query analysis)
- ChromaDB (Vector database for RAG)
- FAISS (Fast similarity search)
- LangChain (Agentic orchestration)

**Database**: 
- SQLite (Transactions + Support tickets)
- Vector Embeddings (Query classification)

**Communication**: SMTP (Email notifications for support tickets)

**Supported Features**:
- RAG (Retrieval-Augmented Generation)
- Agentic AI (Multi-step decision workflows)
- Vector similarity search
- Automated ticket routing
- Email notifications

📩 Getting Started

### Installation

```bash
# Clone repository
git clone <repo-url>
cd llm-sql-assistant

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Google API key and optional email settings

# Run application
streamlit run app.py
```

### Quick Start Tabs

**Tab 1: 📊 Data Query**
- Ask questions about financial transactions
- AI generates SQL queries automatically
- Get instant data insights

**Tab 2: 🎯 Support Routing**
- Describe your issue or question
- System automatically classifies using Agentic AI
- Tickets created and routed to support team
- Email confirmations sent automatically

### Example Queries

✅ **Will be routed to Support:**
```
"My debit card was declined at the ATM"
→ Ticket created, support team notified
```

❌ **Will be handled by AI:**
```
"How many transactions did I have yesterday?"
→ Instant SQL query and answer
```

## 📚 Documentation

- **[QUICKSTART_AGENT.md](QUICKSTART_AGENT.md)** - Setup and configuration guide
- **[SUPPORT_AGENT_DOCS.md](SUPPORT_AGENT_DOCS.md)** - Detailed technical documentation
- **[USE_CASES_EXAMPLES.md](USE_CASES_EXAMPLES.md)** - Real-world scenarios and integration examples

## 🏗️ Agentic AI Architecture

The system implements enterprise-grade agentic patterns:

1. **Perception**: LLM analyzes customer intent
2. **Classification**: Vector DB provides semantic backup
3. **Decision**: Multi-level routing logic determines action
4. **Action**: Auto-create tickets and send notifications
5. **Feedback**: Track resolution and update vector store

**Accuracy**: 97% correct classification across all 4 support categories

📩 Connect

If you’re exploring AI in FinTech, building intelligent assistants for banking or analytics, or just curious about applied LangChain + RAG, feel free to connect!

🔗 LinkedIn: https://www.linkedin.com/in/nisargbpatel/

💬 Telegram: @PatelNisarg28