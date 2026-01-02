from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from src.embeddings import embedding_model
from src.exceptions import RetrievalError, QdrantConnectionError
from src.logger import setup_logger
import config

logger = setup_logger(__name__)


class VectorRetriever:
    def __init__(self):
        try:
            logger.info("Connecting to Qdrant...")
            self.client = QdrantClient(
                url=config.QDRANT_URL,
                api_key=config.QDRANT_API_KEY
            )
            self.collection_name = config.COLLECTION_NAME
            
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant. Available collections: {len(collections.collections)}")
        except Exception as e:
            logger.error(f"Qdrant connection failed: {str(e)}")
            raise QdrantConnectionError(f"Could not connect to Qdrant: {str(e)}")
    
    def retrieve(self, query: str, top_k: int = None):
        """Retrieve top-k documents for query"""
        if top_k is None:
            top_k = config.TOP_K
        
        try:
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
            
            logger.debug(f"Retrieved {len(retrieved_docs)} documents with scores: "
                        f"{[d['score'] for d in retrieved_docs]}")
            return retrieved_docs
        except UnexpectedResponse as e:
            logger.error(f"Qdrant query failed: {str(e)}")
            raise RetrievalError(f"Vector search failed: {str(e)}")
        except Exception as e:
            logger.error(f"Retrieval error: {str(e)}")
            raise RetrievalError(f"Could not retrieve documents: {str(e)}")
    
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
