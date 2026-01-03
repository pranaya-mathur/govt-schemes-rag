from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from src.embeddings import embedding_model
from src.exceptions import RetrievalError, QdrantConnectionError
from src.logger import setup_logger
from src.adaptive_threshold import adaptive_threshold
from src.query_decomposer import get_query_decomposer
from src.metadata_retrieval import MetadataRetriever
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
            
            # Initialize query decomposer for scheme extraction
            self.query_decomposer = get_query_decomposer()
            logger.info("Query decomposer initialized")
            
            # Initialize metadata retriever
            self.metadata_retriever = MetadataRetriever(self.client, self.collection_name)
            logger.info("Metadata retriever initialized")
            
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
        """Intelligent retrieval with automatic routing
        
        Routing Logic:
        1. Decompose query to detect scheme names
        2. If scheme(s) detected -> Use metadata-filtered retrieval (guaranteed accuracy)
        3. If no scheme -> Use hybrid retrieval (discovery mode)
        4. Apply adaptive threshold as final quality gate
        
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
        
        # Step 1: Decompose query to detect schemes
        decomposition = self.query_decomposer.decompose(query)
        detected_schemes = decomposition['detected_schemes']
        retrieval_mode = decomposition['retrieval_mode']
        
        logger.info(
            f"Query decomposition: mode={retrieval_mode}, "
            f"schemes={detected_schemes}"
        )
        
        # Step 2: Route to appropriate retrieval strategy
        if retrieval_mode == 'filtered' and detected_schemes:
            # Use metadata-filtered retrieval for scheme-specific queries
            docs, metadata_info = self._retrieve_with_metadata(
                query, detected_schemes, top_k, intent
            )
            
            # Add metadata info to docs for transparency
            for doc in docs:
                doc['decomposition'] = {
                    'detected_schemes': detected_schemes,
                    'retrieval_mode': retrieval_mode,
                    'metadata_info': metadata_info
                }
        else:
            # Use hybrid retrieval for discovery/general queries
            docs = self._retrieve_hybrid(query, top_k, intent)
            
            for doc in docs:
                doc['decomposition'] = {
                    'detected_schemes': [],
                    'retrieval_mode': 'hybrid',
                    'metadata_info': None
                }
        
        # Step 3: Apply adaptive threshold filtering
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
    
    def _retrieve_with_metadata(
        self,
        query: str,
        scheme_names: list,
        top_k: int,
        intent: str = None
    ) -> tuple:
        """Metadata-filtered retrieval with fallback
        
        Args:
            query: Search query
            scheme_names: List of detected scheme names
            top_k: Number of results
            intent: Query intent for theme optimization
            
        Returns:
            Tuple of (docs, metadata_info)
        """
        # Map intent to theme for targeted retrieval
        theme = self._intent_to_theme(intent)
        
        logger.info(
            f"Metadata-filtered retrieval: schemes={scheme_names}, "
            f"theme={theme}, top_k={top_k}"
        )
        
        # Special handling for COMPARISON intent
        if intent == 'COMPARISON' and len(scheme_names) >= 2:
            return self._retrieve_comparison(query, scheme_names, top_k)
        
        # Standard filtered retrieval with fallback
        docs, metadata_info = self.metadata_retriever.retrieve_with_fallback(
            query=query,
            scheme_names=scheme_names,
            top_k=top_k,
            theme=theme,
            hybrid_retriever=self.hybrid_retriever,
            min_filtered_results=3  # Trigger fallback if < 3 filtered results
        )
        
        return docs, metadata_info
    
    def _retrieve_comparison(
        self,
        query: str,
        scheme_names: list,
        top_k: int
    ) -> tuple:
        """Specialized retrieval for comparison queries
        
        Ensures balanced representation of all schemes being compared.
        
        Args:
            query: Comparison query
            scheme_names: List of schemes to compare
            top_k: Total number of results
            
        Returns:
            Tuple of (docs, metadata_info)
        """
        logger.info(f"Comparison retrieval for: {scheme_names}")
        
        # Retrieve equal docs per scheme
        docs_per_scheme = max(3, top_k // len(scheme_names))
        
        results_by_scheme = self.metadata_retriever.retrieve_multi_scheme_comparison(
            query=query,
            scheme_names=scheme_names,
            docs_per_scheme=docs_per_scheme
        )
        
        # Flatten and sort by score
        all_docs = []
        for scheme, docs in results_by_scheme.items():
            all_docs.extend(docs)
        
        all_docs.sort(key=lambda x: x['score'], reverse=True)
        final_docs = all_docs[:top_k]
        
        metadata_info = {
            'comparison_mode': True,
            'schemes': scheme_names,
            'docs_per_scheme': {scheme: len(docs) for scheme, docs in results_by_scheme.items()}
        }
        
        logger.info(
            f"Comparison retrieval returned {len(final_docs)} docs: "
            f"{metadata_info['docs_per_scheme']}"
        )
        
        return final_docs, metadata_info
    
    def _retrieve_hybrid(self, query: str, top_k: int, intent: str = None):
        """Hybrid retrieval (BM25 + Semantic) for discovery queries
        
        Args:
            query: Search query
            top_k: Number of results
            intent: Query intent
            
        Returns:
            List of retrieved documents
        """
        logger.info(f"Hybrid retrieval: query='{query[:50]}...', top_k={top_k}")
        
        if self.hybrid_retriever:
            docs = self.hybrid_retriever.hybrid_retrieve(query, top_k, intent)
        else:
            # Fallback to semantic-only
            docs = self._semantic_retrieve(query, top_k)
        
        return docs
    
    def _intent_to_theme(self, intent: str) -> str:
        """Map query intent to document theme for targeted retrieval
        
        Args:
            intent: Query intent
            
        Returns:
            Theme string or None for all themes
        """
        intent_theme_map = {
            'ELIGIBILITY': 'eligibility',
            'BENEFITS': 'benefits',
            'PROCEDURE': 'application-steps',
            # Others don't map to specific themes
        }
        
        return intent_theme_map.get(intent)
    
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
            
            # Include retrieval method for transparency
            retrieval_method = d.get('retrieval_method', 'unknown')
            
            lines.append(
                f"{i}. Scheme: {p.get('scheme_name', 'Unknown')}\n"
                f"   Theme: {p.get('theme', 'Unknown')}\n"
                f"   Similarity Score: {d.get('score', 0):.3f}\n"
                f"   Retrieval Method: {retrieval_method}\n"
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
            
            # Add retrieval method for transparency
            if d.get('retrieval_method'):
                doc_text += f"Retrieval Method: {d.get('retrieval_method')}\n"
            
            doc_text += f"\nContent:\n{p.get('text', 'No content available')}\n"
            
            # Add official URL
            if p.get('official_url'):
                doc_text += f"\nOfficial URL: {p.get('official_url')}"
            
            lines.append(doc_text)
        
        return "\n" + "="*80 + "\n".join(["\n" + line for line in lines])
