"""Custom exceptions for RAG system"""


class RAGException(Exception):
    """Base exception for RAG system"""
    pass


class EmbeddingError(RAGException):
    """Raised when embedding generation fails"""
    pass


class RetrievalError(RAGException):
    """Raised when vector retrieval fails"""
    pass


class LLMError(RAGException):
    """Raised when LLM call fails"""
    pass


class InvalidIntentError(RAGException):
    """Raised when intent classification fails"""
    pass


class QdrantConnectionError(RAGException):
    """Raised when Qdrant connection fails"""
    pass


class EmptyQueryError(RAGException):
    """Raised when query is empty"""
    pass


class NoRelevantDocsError(RAGException):
    """Raised when no relevant documents found after retries"""
    pass
