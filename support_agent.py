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

    def create_ticket(self, user_email: str, user_query: str, category: str, priority: str = "medium") -> str:
        """Create a new support ticket"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        ticket_number = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute("""
            INSERT INTO support_tickets (ticket_number, user_email, user_query, category, priority)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket_number, user_email, user_query, category, priority))

        conn.commit()
        conn.close()

        return ticket_number

    def update_ticket_status(self, ticket_number: str, status: str):
        """Update ticket status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE support_tickets 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE ticket_number = ?
        """, (status, ticket_number))

        conn.commit()
        conn.close()

    def mark_email_sent(self, ticket_number: str):
        """Mark ticket as having email sent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE support_tickets 
            SET email_sent = 1, email_sent_at = CURRENT_TIMESTAMP
            WHERE ticket_number = ?
        """, (ticket_number,))

        conn.commit()
        conn.close()


class VectorRAGClassifier:
    """Vector-based query classifier using ChromaDB for RAG"""

    def __init__(self):
        # Initialize ChromaDB with persistent storage
        chroma_path = "./support_vectors"
        os.makedirs(chroma_path, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="support_queries",
            metadata={"hnsw:space": "cosine"}
        )

        self.init_vectors()

    def init_vectors(self):
        """Initialize vectors with support categories and examples"""
        if self.collection.count() == 0:
            for category, keywords in SUPPORT_CATEGORIES.items():
                for idx, keyword in enumerate(keywords):
                    self.collection.add(
                        ids=[f"{category}_{idx}"],
                        metadatas=[{"category": category}],
                        documents=[keyword]
                    )

    def mark_email_sent(self, ticket_number: str):
        """Mark ticket as having email sent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE support_tickets 
            SET email_sent = 1, email_sent_at = CURRENT_TIMESTAMP
            WHERE ticket_number = ?
        """, (ticket_number,))

        conn.commit()
        conn.close()


class VectorRAGClassifier:
    """Vector-based query classifier using ChromaDB for RAG"""

    def __init__(self):
        # Initialize ChromaDB with persistent storage
        chroma_path = "./support_vectors"
        os.makedirs(chroma_path, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="support_queries",
            metadata={"hnsw:space": "cosine"}
        )

        self.init_vectors()

    def classify_query(self, query: str, top_k: int = 1) -> Tuple[str, float]:
        """Classify query to determine support category"""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

        if results['metadatas'] and len(results['metadatas']) > 0:
            category = results['metadatas'][0][0]['category']
            distance = results['distances'][0][0]
            # Convert distance to similarity score (0-1)
            similarity = max(0, 1 - distance)
            return category, similarity

        return "general", 0.0


class SupportEmailNotifier:
    """Handles sending support ticket emails"""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SUPPORT_EMAIL")
        self.sender_password = os.getenv("SUPPORT_EMAIL_PASSWORD")
        self.support_team_email = os.getenv("SUPPORT_TEAM_EMAIL")

    def send_ticket_notification(self, ticket: Dict) -> bool:
        """Send email notification to support team about new ticket"""
        try:
            if not self.sender_email or not self.support_team_email:
                print(
                    "⚠️ Email credentials not configured. Ticket created but email not sent.")
                return False

            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.support_team_email
            msg['Subject'] = f"New Support Ticket: {ticket['ticket_number']} - {ticket['category'].upper()}"

            body = f"""
New Support Ticket Created

Ticket Number: {ticket['ticket_number']}
Category: {ticket['category']}
Priority: {ticket['priority']}
Created: {ticket['created_at']}

Customer Email: {ticket['user_email']}

Customer Query:
{ticket['user_query']}

---
Please log in to the dashboard to review and respond to this ticket.
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()

            print(
                f"✅ Email notification sent for ticket {ticket['ticket_number']}")
            return True

        except Exception as e:
            print(f"❌ Error sending email: {str(e)}")
            return False

    def send_customer_confirmation(self, ticket: Dict) -> bool:
        """Send confirmation email to customer"""
        try:
            if not self.sender_email:
                return False

            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ticket['user_email']
            msg['Subject'] = f"Support Ticket Created: {ticket['ticket_number']}"

            body = f"""
Dear Customer,

Thank you for contacting us. Your support ticket has been created and assigned to our team.

Ticket Number: {ticket['ticket_number']}
Category: {ticket['category']}
Status: Open

Your query has been marked as {ticket['priority']} priority and will be addressed shortly.
Our support team will reach out to you within 24 hours.

Best regards,
FinTech Support Team
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            print(f"❌ Error sending confirmation email: {str(e)}")
            return False


class SupportAgent:
    """Main agent that orchestrates query routing and ticket creation"""

    def __init__(self):
        self.classifier = VectorRAGClassifier()
        self.db = SupportTicketDatabase()
        self.emailer = SupportEmailNotifier()
        self.support_categories_set = set(SUPPORT_CATEGORIES.keys())


