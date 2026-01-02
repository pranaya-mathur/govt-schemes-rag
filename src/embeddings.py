from sentence_transformers import SentenceTransformer
from src.exceptions import EmbeddingError
from src.logger import setup_logger
import config

logger = setup_logger(__name__)


class EmbeddingModel:
    def __init__(self):
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(
                config.EMBEDDING_MODEL,
                device="cuda" if self._has_cuda() else "cpu"
            )
            logger.info(f"Model loaded on {'GPU' if self._has_cuda() else 'CPU'}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise EmbeddingError(f"Could not initialize embedding model: {str(e)}")
    
    def _has_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def embed_query(self, query: str):
        """Generate embedding for query text"""
        if not query or not query.strip():
            raise EmbeddingError("Cannot embed empty query")
        
        try:
            embedding = self.model.encode(
                query,
                normalize_embeddings=True
            )
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")
    
    @property
    def dimension(self):
        """Return embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


# Global instance
embedding_model = EmbeddingModel()
