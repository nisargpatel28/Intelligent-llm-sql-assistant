"""
Query Predictor for Predictive Query Suggestions
"""

import json
import sqlite3
from typing import Dict, List, Optional
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False