import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Model Configuration
EMBEDDING_MODEL = "BAAI/bge-m3"

# LLM Models - Hybrid Approach
# Ollama for adaptive/lightweight tasks (local, free)
OLLAMA_MODEL = "deepseek-r1:8b"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Groq for heavy lifting (cloud, fast)
GROQ_MODEL = "llama-3.3-70b-versatile"

# Chunking Model (for data pipeline)
CHUNKING_MODEL = "llama3.1:8b"  # Ollama

# Temperature
TEMPERATURE = 0.2

# Vector DB
COLLECTION_NAME = "myscheme_rag"
TOP_K = 5

# Intent Labels - Based on user query patterns
INTENT_LABELS = [
    "DISCOVERY",      # find/search/show me schemes
    "ELIGIBILITY",    # am I eligible/who can apply/age limit
    "BENEFITS",       # how much/subsidy amount/loan/funding
    "COMPARISON",     # compare/difference between/vs
    "PROCEDURE",      # how to apply/steps/process/documents
    "GENERAL"         # fallback
]

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
