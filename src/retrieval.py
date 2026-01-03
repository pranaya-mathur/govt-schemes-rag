from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from src.embeddings import embedding_model
from src.exceptions import RetrievalError, QdrantConnectionError
from src.logger import setup_logger
from src.adaptive_threshold import adaptive_threshold
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
            
            # Initialize hybrid retriever if enabled
            self.hybrid_retriever = None
            if config.HYBRID_RETRIEVAL_ENABLED:
                try:
                    from src.hybrid_retrieval import HybridRetriever
                    self.hybrid_retriever = HybridRetriever(
                        semantic_retriever=self,
                        bm25_weight=config.BM25_WEIGHT,
                        semantic_weight=config.SEMANTIC_WEIGHT,
                        rrf_k=config.RRF_K
                    )
                    logger.info("Hybrid retrieval enabled with BM25 + Semantic search")
                except Exception as e:
                    logger.warning(f"Hybrid retrieval initialization failed: {e}. Falling back to semantic-only.")
                    self.hybrid_retriever = None
            
        except Exception as e:
            logger.error(f"Qdrant connection failed: {str(e)}")
            raise QdrantConnectionError(f"Could not connect to Qdrant: {str(e)}")
    
    def retrieve(self, query: str, top_k: int = None, intent: str = None):
        """
        Retrieve top-k documents for query with adaptive filtering
        
        Args:
            query: Search query
            top_k: Number of documents to retrieve (uses intent-specific if not specified)
            intent: Query intent for adaptive top_k and threshold
        
        Returns:
            List of retrieved documents with metadata
        """
        # Use intent-specific top_k if available
        if top_k is None:
            if intent and intent in config.INTENT_TOP_K:
                top_k = config.INTENT_TOP_K[intent]
                logger.debug(f"Using intent-specific top_k={top_k} for {intent}")
            else:
                top_k = config.TOP_K
        
        # Use hybrid retrieval if available, otherwise fall back to semantic
        if self.hybrid_retriever:
            docs = self.hybrid_retriever.hybrid_retrieve(query, top_k, intent)
        else:
            docs = self._semantic_retrieve(query, top_k)
        
        # Apply adaptive threshold filtering
        filtered_docs, threshold_metadata = adaptive_threshold.filter_documents(
            docs, intent
        )
        
        # Log threshold decision
        logger.info(
            f"Retrieved {len(filtered_docs)}/{len(docs)} documents "
            f"(threshold={threshold_metadata.get('threshold', 0):.3f}, "
            f"method={threshold_metadata.get('method', 'unknown')})"
        )
        
        return filtered_docs
    
    def _semantic_retrieve(self, query: str, top_k: int):
        """Internal method for pure semantic retrieval"""
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
            
            logger.debug(
                f"Semantic search returned {len(retrieved_docs)} documents with scores: "
                f"{[round(d['score'], 3) for d in retrieved_docs[:5]]}"
            )
            
            return retrieved_docs
            
        except UnexpectedResponse as e:
            logger.error(f"Qdrant query failed: {str(e)}")
            raise RetrievalError(f"Vector search failed: {str(e)}")
        except Exception as e:
            logger.error(f"Retrieval error: {str(e)}")
            raise RetrievalError(f"Could not retrieve documents: {str(e)}")
    
    def format_for_judge(self, docs: list) -> str:
        """Format docs for relevance judgment - Include content preview for better judgment"""
        if not docs:
            return "No documents retrieved."
        
        lines = []
        for i, d in enumerate(docs, 1):
            p = d["payload"]
            # Truncate text to first 300 chars for preview
            text = p.get('text', '')
            text_preview = text[:300] + "..." if len(text) > 300 else text
            
            lines.append(
                f"{i}. Scheme: {p.get('scheme_name', 'Unknown')}\n"
                f"   Theme: {p.get('theme', 'Unknown')}\n"
                f"   Similarity Score: {d.get('score', 0):.3f}\n"
                f"   Content Preview: {text_preview}"
            )
        return "\n\n".join(lines)
    
    def format_for_answer(self, docs: list) -> str:
        """Format docs for answer generation - Full context with metadata"""
        if not docs:
            return "No relevant documents found."
        
        lines = []
        for i, d in enumerate(docs, 1):
            p = d["payload"]
            
            # Build formatted document
            doc_text = f"Document {i} (Relevance: {d.get('score', 0):.3f})\n"
            doc_text += f"Scheme Name: {p.get('scheme_name', 'Unknown')}\n"
            doc_text += f"Theme: {p.get('theme', 'Unknown')}\n"
            
            # Add ministry if available
            if p.get('ministry'):
                doc_text += f"Ministry: {p.get('ministry')}\n"
            
            doc_text += f"\nContent:\n{p.get('text', 'No content available')}\n"
            
            # Add official URL
            if p.get('official_url'):
                doc_text += f"\nOfficial URL: {p.get('official_url')}"
            
            lines.append(doc_text)
        
        return "\n" + "="*80 + "\n".join(["\n" + line for line in lines])
