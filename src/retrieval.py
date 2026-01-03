from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Filter, FieldCondition, MatchAny
from src.embeddings import embedding_model
from src.exceptions import RetrievalError, QdrantConnectionError
from src.logger import setup_logger
import config

logger = setup_logger(__name__)


class VectorRetriever:
    """Simplified vector retriever with semantic search + metadata filtering"""
    
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
    
    def retrieve(self, query: str, top_k: int = None, intent: str = None):
        """Main retrieval method with intent-aware top_k
        
        Args:
            query: Search query
            top_k: Number of documents to retrieve (uses intent-specific if not specified)
            intent: Query intent for adaptive top_k
        
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
        
        # Perform semantic search
        docs = self._semantic_retrieve(query, top_k)
        
        # Apply simple score threshold filtering
        filtered_docs = self._filter_by_threshold(docs, intent)
        
        logger.info(f"Retrieved {len(filtered_docs)}/{len(docs)} documents after filtering")
        
        return filtered_docs
    
    def _semantic_retrieve(self, query: str, top_k: int):
        """Pure semantic retrieval using BGE-M3 embeddings"""
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
                    "payload": point.payload,
                    "retrieval_method": "semantic"
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
    
    def _filter_by_threshold(self, docs: list, intent: str = None) -> list:
        """Simple threshold filtering based on intent
        
        Args:
            docs: Retrieved documents with scores
            intent: Query intent for adaptive threshold
            
        Returns:
            Filtered documents above threshold
        """
        # Intent-specific thresholds
        thresholds = {
            'ELIGIBILITY': 0.45,   # Lower threshold for eligibility queries
            'BENEFITS': 0.45,      # Lower threshold for benefits queries
            'COMPARISON': 0.40,    # Lower threshold for comparison queries
            'DISCOVERY': 0.50,     # Medium threshold for discovery
            'PROCEDURE': 0.45,     # Lower threshold for procedure
            'GENERAL': 0.50        # Default threshold
        }
        
        threshold = thresholds.get(intent, 0.50)
        
        # Filter documents above threshold
        filtered = [doc for doc in docs if doc['score'] >= threshold]
        
        # Ensure at least top 3 docs are returned if available
        if len(filtered) < 3 and len(docs) >= 3:
            filtered = docs[:3]
            logger.debug(f"Applied minimum 3 docs rule (threshold={threshold})")
        
        logger.debug(f"Threshold filtering: {len(filtered)}/{len(docs)} docs passed (threshold={threshold})")
        
        return filtered
    
    def retrieve_with_metadata_filter(self, query: str, scheme_names: list, top_k: int = None, theme: str = None):
        """Metadata-filtered retrieval for specific schemes
        
        Args:
            query: Search query
            scheme_names: List of scheme names to filter by
            top_k: Number of results
            theme: Optional theme filter
            
        Returns:
            List of filtered documents
        """
        if top_k is None:
            top_k = config.TOP_K
        
        try:
            query_vector = embedding_model.embed_query(query)
            
            # Build metadata filter
            filter_conditions = []
            
            # Scheme name filter with fuzzy matching support
            if scheme_names:
                # Normalize scheme names (lowercase, remove special chars)
                normalized_schemes = [
                    s.lower().replace('-', ' ').replace('_', ' ').strip()
                    for s in scheme_names
                ]
                
                filter_conditions.append(
                    FieldCondition(
                        key="scheme_name",
                        match=MatchAny(any=normalized_schemes)
                    )
                )
            
            # Theme filter
            if theme:
                filter_conditions.append(
                    FieldCondition(
                        key="theme",
                        match=MatchAny(any=[theme])
                    )
                )
            
            # Execute query with filters
            filter_obj = Filter(must=filter_conditions) if filter_conditions else None
            
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=filter_obj,
                limit=top_k * 2,  # Retrieve more to account for filtering
                with_payload=True
            )
            
            retrieved_docs = []
            for point in response.points:
                retrieved_docs.append({
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload,
                    "retrieval_method": "metadata_filtered"
                })
            
            # Return top_k results
            final_docs = retrieved_docs[:top_k]
            
            logger.info(
                f"Metadata-filtered retrieval: {len(final_docs)} docs "
                f"(schemes={scheme_names}, theme={theme})"
            )
            
            return final_docs
            
        except Exception as e:
            logger.error(f"Metadata-filtered retrieval failed: {str(e)}")
            # Fallback to regular semantic search
            logger.info("Falling back to semantic search")
            return self._semantic_retrieve(query, top_k)
    
    def format_for_judge(self, docs: list) -> str:
        """Format docs for relevance judgment"""
        if not docs:
            return "No documents retrieved."
        
        lines = []
        for i, d in enumerate(docs, 1):
            p = d["payload"]
            # Truncate text to first 200 chars for preview
            text = p.get('text', '')
            text_preview = text[:200] + "..." if len(text) > 200 else text
            
            lines.append(
                f"{i}. Scheme: {p.get('scheme_name', 'Unknown')}\n"
                f"   Theme: {p.get('theme', 'Unknown')}\n"
                f"   Score: {d.get('score', 0):.3f}\n"
                f"   Preview: {text_preview}"
            )
        return "\n\n".join(lines)
    
    def format_for_answer(self, docs: list) -> str:
        """Format docs for answer generation - Full context"""
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
