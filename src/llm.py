from langchain_groq import ChatGroq
import config


def get_llm():
    """Initialize Groq LLM"""
    return ChatGroq(
        model=config.LLM_MODEL,
        temperature=config.TEMPERATURE
    )
