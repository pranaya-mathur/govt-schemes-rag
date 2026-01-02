"""Configuration for data pipeline"""
import os
from dotenv import load_dotenv

load_dotenv()

# Ollama Configuration for Chunking
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHUNKING_MODEL = "llama3.1:8b"  # LLM Verdict model
TEMPERATURE = 0.2

# Embedding Model
EMBEDDING_MODEL = "BAAI/bge-m3"

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "myschemerag"

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
