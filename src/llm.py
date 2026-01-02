from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOllama
import config


def get_ollama_llm():
    """Initialize Ollama LLM for adaptive tasks (intent, reflection)"""
    return ChatOllama(
        model=config.OLLAMA_MODEL,
        temperature=config.TEMPERATURE,
        base_url=config.OLLAMA_BASE_URL
    )


def get_groq_llm():
    """Initialize Groq LLM for heavy tasks (answer generation, judges)"""
    return ChatGroq(
        model=config.GROQ_MODEL,
        temperature=config.TEMPERATURE
    )


def get_chunking_llm():
    """Initialize Ollama LLM for data chunking (llama3.1:8b)"""
    return ChatOllama(
        model=config.CHUNKING_MODEL,
        temperature=config.TEMPERATURE,
        base_url=config.OLLAMA_BASE_URL
    )
