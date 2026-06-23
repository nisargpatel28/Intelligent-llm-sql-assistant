# Advanced AI Features

This directory contains the implementation of advanced AI capabilities for the LLM SQL Assistant.

## Features

### 1. Multi-turn Conversations (`conversation/`)
- **Manager**: Handles conversation context and history storage
- Maintains context across multiple user interactions
- SQLite-based storage with automatic cleanup
- Supports metadata and session tracking

### 2. Predictive Query Suggestions (`suggestions/`)
- **Predictor**: Analyzes user query patterns and history
- Provides intelligent query suggestions
- Uses both pattern matching and AI-powered recommendations
- Learns from successful queries

### 3. Anomaly Detection (`anomaly_detection/`)
- **Detector**: Identifies unusual patterns in transaction data
- Combines statistical methods (Z-score, IQR) with ML (Isolation Forest)
- Configurable detection thresholds
- Provides detailed anomaly reports

### 4. Automated Report Generation (`report_generation/`)
- **Generator**: Creates comprehensive reports from transaction data
- Supports multiple report types (summary, detailed, trends)
- Includes data visualizations and AI-powered insights
- Exportable charts and formatted reports

## MCP Integration

The system includes Model Context Protocol (MCP) support for external service integration:

- **Server** (`../mcp/server/`): MCP server providing AI tools
- **Client** (`../mcp/client/`): Client for calling external MCP services
- **External Tools** (`../tools/external/`): Interfaces to external APIs

## Usage

### In Streamlit App
The AI features are integrated into the main Streamlit application under the "🤖 AI Features" tab.

### As Standalone Components
Each feature can be used independently:

```python
from ai_features.conversation.manager import ConversationManager
from ai_features.anomaly_detection.detector import AnomalyDetector

# Initialize components
conv_manager = ConversationManager()
anomaly_detector = AnomalyDetector()

# Use features
conv_manager.add_message("user123", "user", "Hello")
anomalies = anomaly_detector.detect_anomalies(transaction_data)
```

### MCP Server
Run the MCP server to provide AI capabilities to external clients:

```bash
python mcp/server/mcp_server.py
```

## Dependencies

- pandas
- numpy
- scikit-learn
- matplotlib
- seaborn
- requests
- asyncio-mcp (for MCP protocol)

## Configuration

Environment variables:
- `GOOGLE_API_KEY`: For Gemini AI features
- External service endpoints can be configured in the respective tool classes

## Data Storage

- Conversation history: `conversation.db`
- Query patterns: `query_history.db`
- Vector databases: `./support_vectors/` (for ChromaDB)

## API Endpoints

The MCP server exposes the following tools:
- `conversation_context`: Manage conversation context
- `query_suggestions`: Get query predictions
- `anomaly_detection`: Detect data anomalies
- `report_generation`: Generate automated reports

## Error Handling

All components include comprehensive error handling and fallback mechanisms. External service failures are logged and alternative local processing is used when available.