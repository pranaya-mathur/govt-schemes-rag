"""Data pipeline configuration - imports from shared_config.py
This file is kept for backward compatibility.
All new config should be added to shared_config.py
"""
import sys
import os

# Add parent directory to path to import shared_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_config import *

# Re-export all configuration for backward compatibility
__all__ = [
    'OLLAMA_BASE_URL',
    'CHUNKING_MODEL',
    'TEMPERATURE',
    'EMBEDDING_MODEL',
    'QDRANT_URL',
    'QDRANT_API_KEY',
    'COLLECTION_NAME',
    'THEME_CATEGORIES',
    'MAX_CHUNK_SIZE',
    'MIN_CHUNK_SIZE'
]
