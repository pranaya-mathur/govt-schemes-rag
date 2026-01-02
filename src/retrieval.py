from qdrant_client import QdrantClient
from src.embeddings import embedding_model
import config


class VectorRetriever:
    def __init__(self):
        self.client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY
        )
        self.collection_name = config.COLLECTION_NAME
    
    def retrieve(self, query: str, top_k: int = None):
        """Retrieve top-k documents for query"""
        if top_k is None:
            top_k = config.TOP_K
        
        query_vector = embedding_model.embed_query(query)
        
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        retrieved_docs = []
        for point in response.points:
            retrieved_docs.append({
                "id": point.id,
                "score": point.score,
                "payload": point.payload
            })
        
        return retrieved_docs
    
    def format_for_judge(self, docs: list) -> str:
        """Format docs for relevance judgment"""
        lines = []
        for d in docs:
            p = d["payload"]
            lines.append(
                f"- {p.get('scheme_name')} (Theme: {p.get('theme')})"
            )
        return "\n".join(lines)
    
    def format_for_answer(self, docs: list) -> str:
        """Format docs for answer generation"""
        lines = []
        for d in docs:
            p = d["payload"]
            lines.append(
                f"Scheme: {p.get('scheme_name')}\n"
                f"Theme: {p.get('theme')}\n"
                f"Text: {p.get('text')}\n"
                f"Official URL: {p.get('official_url')}"
            )
        return "\n---\n".join(lines)
