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
OLLAMA_MODEL = "deepseek-r1:8b"  # For intent, reflection, corrective queries
CHUNKING_MODEL = "llama3.1:8b"   # For data pipeline chunking

# Groq for heavy lifting (cloud, fast)
GROQ_MODEL = "llama-3.3-70b-versatile"  # For answer generation, judges

# LLM Parameters
TEMPERATURE = 0.2

# ============================================
# VECTOR DATABASE
# ============================================
COLLECTION_NAME = "myscheme_rag"
TOP_K = 5

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
# LOGGING
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = "logs"
