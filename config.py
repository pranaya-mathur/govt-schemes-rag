"""Main configuration - imports from shared_config.py
This file is kept for backward compatibility.
All new config should be added to shared_config.py
"""
from shared_config import *

# Re-export all configuration for backward compatibility
__all__ = [
    'GROQ_API_KEY',
    'QDRANT_URL',
    'QDRANT_API_KEY',
    'OLLAMA_BASE_URL',
    'EMBEDDING_MODEL',
    'OLLAMA_MODEL',
    'GROQ_MODEL',
    'CHUNKING_MODEL',
    'TEMPERATURE',
    'COLLECTION_NAME',
    'TOP_K',
    'INTENT_LABELS',
    'LOG_LEVEL',
    'LOG_FORMAT',
    'MAX_REFLECTION_ITERATIONS',
    'MAX_CORRECTION_ITERATIONS'
]
