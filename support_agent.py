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

}