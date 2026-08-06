"""
Agentic AI Support Router - Redirects queries to customer support via email
Uses LLM, RAG, and Vector DB for intelligent query classification and routing
"""

import google.generativeai as genai
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
import json
from typing import Dict, List, Tuple
import chromadb
from chromadb.config import Settings

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Support categories for classification
SUPPORT_CATEGORIES = {
    "bank_account": [
        "account balance",
        "account statement",
        "account verification",
        "account closure",
        "account details",
        "account settings"
    ],
    "debit_card": [
        "card blocked",
        "card replacement",
        "card declined",
        "card limit",
        "card activation",
        "card fraud",
        "card pin"
    ],
    "cross_border": [
        "international transfer",
        "cross-border payment",
        "forex",
        "wire transfer",
        "international wire",
        "currency exchange",
        "SWIFT"
    ],
    "kyc": [
        "kyc verification",
        "identity verification",
        "document verification",
        "kyc status",
        "kyc failed",
        "kyc update",
        "aml check"
    ]
}


class SupportTicketDatabase:
    """Manages support tickets in SQLite database"""

    def __init__(self, db_path='support_tickets.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize support tickets table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT UNIQUE,
                user_email TEXT NOT NULL,
                user_query TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_to TEXT,
                resolution_notes TEXT,
                email_sent BOOLEAN DEFAULT 0,
                email_sent_at TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()