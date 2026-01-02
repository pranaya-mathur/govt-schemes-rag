from sentence_transformers import SentenceTransformer
import config


class EmbeddingModel:
    def __init__(self):
        self.model = SentenceTransformer(
            config.EMBEDDING_MODEL,
            device="cuda" if self._has_cuda() else "cpu"
        )
    
    def _has_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def embed_query(self, query: str):
        """Generate embedding for query text"""
        embedding = self.model.encode(
            query,
            normalize_embeddings=True  # cosine-safe
        )
        return embedding
    
    @property
    def dimension(self):
        """Return embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


# Global instance
embedding_model = EmbeddingModel()
