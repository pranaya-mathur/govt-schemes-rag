import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Model Configuration
EMBEDDING_MODEL = "BAAI/bge-m3"
LLM_MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.2

# Vector DB
COLLECTION_NAME = "myschemerag"
TOP_K = 5

# Intent Labels
INTENT_LABELS = {
    "DISCOVERY",  # find schemes
    "ELIGIBILITY",  # who can apply
    "BENEFITS",  # money/subsidy amount
    "COMPARISON",  # compare schemes
    "PROCEDURE",  # how to apply
    "GENERAL"  # fallback
}
