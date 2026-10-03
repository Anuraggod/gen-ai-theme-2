"""
config.py - Centralized configuration settings for the Troubleshooting Engine.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

QUERIES_PATH = DATA_DIR / "queries.json"
SIIS_PATH = DATA_DIR / "siis_responses.json"
DEEPLINKS_PATH = DATA_DIR / "deeplinks.json"
SAMPLES_PATH = DATA_DIR / "samples"

# Semantic cache settings
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.82"))
SEMANTIC_CACHE_MAX_SIZE = int(os.getenv("SEMANTIC_CACHE_MAX_SIZE", "1000"))

# Service Metadata
SERVICE_NAME = "Smart Guided Troubleshooting Engine"
SERVICE_VERSION = "1.0.0"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
