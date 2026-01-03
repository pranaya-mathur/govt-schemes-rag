"""Shared configuration for all modules - Single source of truth"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# API KEYS & ENDPOINTS
# ============================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ============================================
# EMBEDDING CONFIGURATION
# ============================================
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIMENSION = 1024  # BGE-M3 dimension

# ============================================
# LLM MODELS - Hybrid Approach
# ============================================
# Ollama for adaptive/lightweight tasks (local, free)
OLLAMA_MODEL = "phi3.5:3.8b"  # For intent, reflection, corrective queries
CHUNKING_MODEL = "llama3.1:8b"   # For data pipeline chunking

# Groq for heavy lifting (cloud, fast)
GROQ_MODEL = "llama-3.3-70b-versatile"  # For answer generation, judges

# LLM Parameters
TEMPERATURE = 0.2

# ============================================
# VECTOR DATABASE
# ============================================
COLLECTION_NAME = "myscheme_rag"

# Default top_k
TOP_K = 5

# Intent-specific top_k values (Production-Grade)
INTENT_TOP_K = {
    "DISCOVERY": 10,      # Need more schemes for discovery
    "COMPARISON": 10,     # Need both entities well-represented
    "ELIGIBILITY": 5,     # Need focused, precise results
    "BENEFITS": 5,        # Need specific benefit information
    "PROCEDURE": 5,       # Need clear step-by-step info
    "GENERAL": 5          # Default moderate retrieval
}

# Adaptive threshold configuration (replaces static MIN_SIMILARITY_SCORE)
# See src/adaptive_threshold.py for implementation
ADAPTIVE_THRESHOLD_CONFIG = {
    "min_absolute_threshold": 0.3,     # Never go below this
    "std_dev_multiplier": 0.5,         # Threshold = mean - (std * this)
    "top_score_ratio": 0.7,            # Minimum ratio of top score
    "min_docs_required": 1             # Always return at least 1 doc if available
}

# Legacy static threshold (deprecated, kept for backward compatibility)
MIN_SIMILARITY_SCORE = 0.5  # Will be replaced by adaptive threshold

# ============================================
# HYBRID RETRIEVAL CONFIGURATION
# ============================================
HYBRID_RETRIEVAL_ENABLED = True
BM25_WEIGHT = 0.4           # Weight for keyword search
SEMANTIC_WEIGHT = 0.6       # Weight for semantic search
RRF_K = 60                  # Reciprocal Rank Fusion parameter

# ============================================
# INTENT CLASSIFICATION
# ============================================
INTENT_LABELS = [
    "DISCOVERY",      # find/search/show me schemes
    "ELIGIBILITY",    # am I eligible/who can apply/age limit
    "BENEFITS",       # how much/subsidy amount/loan/funding
    "COMPARISON",     # compare/difference between/vs
    "PROCEDURE",      # how to apply/steps/process/documents
    "GENERAL"         # fallback
]

# ============================================
# DATA PIPELINE CONFIGURATION
# ============================================
# Theme Categories for Chunking
THEME_CATEGORIES = [
    "benefits",
    "eligibility",
    "application-steps",
    "documents",
    "contact",
    "general"
]

# Chunking Parameters
MAX_CHUNK_SIZE = 500  # tokens
MIN_CHUNK_SIZE = 50   # tokens

# ============================================
# RAG WORKFLOW LIMITS
# ============================================
MAX_REFLECTION_ITERATIONS = 2  # Self-RAG query refinement limit
MAX_CORRECTION_ITERATIONS = 2  # Corrective RAG limit

# ============================================
# ANSWER GENERATION
# ============================================
# Structured output with schema validation
STRUCTURED_OUTPUT_ENABLED = True
MAX_ANSWER_RETRY = 2  # Retry generation if schema validation fails

# ============================================
# LOGGING
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = "logs"
