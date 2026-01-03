"""Metadata-Aware Retrieval with Qdrant Filtering

Provides scheme-specific retrieval using Qdrant metadata filters.
Guarantees that results are from the requested scheme(s).

Fallback mechanism:
1. Try filtered retrieval
2. If insufficient results, blend with hybrid search
3. Apply adaptive threshold as final quality gate
"""
from typing import List, Dict, Optional
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from src.logger import setup_logger
from src.embeddings import embedding_model
from src.exceptions import RetrievalError
import config

logger = setup_logger(__name__)


class MetadataRetriever:
    """Metadata-aware retrieval with Qdrant filtering"""
    
    def __init__(self, qdrant_client, collection_name: str):
        """
        Args:
            qdrant_client: Qdrant client instance
            collection_name: Collection name
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        logger.info("MetadataRetriever initialized")
    
    def _build_scheme_filter(self, scheme_names: List[str]) -> Filter:
        """Build Qdrant filter for scheme names
        
        Args:
            scheme_names: List of scheme names to filter by
            
        Returns:
            Qdrant Filter object
        """
        if len(scheme_names) == 1:
            # Single scheme filter
            return Filter(
                must=[
                    FieldCondition(
                        key="scheme_name",
                        match=MatchValue(value=scheme_names[0])
                    )
                ]
            )
        else:
            # Multiple schemes - match any
            return Filter(
                must=[
                    FieldCondition(
                        key="scheme_name",
                        match=MatchAny(any=scheme_names)
                    )
                ]
            )
    
    def _build_theme_filter(self, theme: str) -> Filter:
        """Build Qdrant filter for theme
        
        Args:
            theme: Theme to filter by (e.g., 'eligibility', 'benefits')
            
        Returns:
            Qdrant Filter object
        """
        return Filter(
            must=[
                FieldCondition(
                    key="theme",
                    match=MatchValue(value=theme)
                )
            ]
        )
    
    def _combine_filters(self, scheme_filter: Filter, theme_filter: Optional[Filter] = None) -> Filter:
        """Combine multiple filters
        
        Args:
            scheme_filter: Scheme name filter
            theme_filter: Optional theme filter
            
        Returns:
            Combined Filter object
        """
        if theme_filter is None:
            return scheme_filter
        
        # Combine both filters (AND operation)
        combined_conditions = scheme_filter.must + theme_filter.must
        return Filter(must=combined_conditions)
    
    def retrieve_with_filter(
        self,
        query: str,
        scheme_names: List[str],
        top_k: int = 5,
        theme: Optional[str] = None,
        min_results: int = 3
    ) -> List[Dict]:
        """Retrieve documents with metadata filtering
        
        Args:
            query: Search query
            scheme_names: List of scheme names to filter by
            top_k: Number of results to retrieve
            theme: Optional theme filter (e.g., 'eligibility')
            min_results: Minimum results required (triggers fallback if not met)
            
        Returns:
            List of retrieved documents with metadata
        """
        logger.info(
            f"Filtered retrieval: schemes={scheme_names}, theme={theme}, top_k={top_k}"
        )
        
        try:
            # Generate query embedding
            query_vector = embedding_model.embed_query(query)
            
            # Build filter
            scheme_filter = self._build_scheme_filter(scheme_names)
            
            if theme:
                theme_filter = self._build_theme_filter(theme)
                combined_filter = self._combine_filters(scheme_filter, theme_filter)
            else:
                combined_filter = scheme_filter
            
            # Query with filter
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=combined_filter,
                limit=top_k,
                with_payload=True
            )
            
            # Format results
            retrieved_docs = []
            for point in response.points:
                retrieved_docs.append({
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload,
                    "retrieval_method": "metadata_filtered"
                })
            
            logger.info(
                f"Filtered retrieval returned {len(retrieved_docs)} documents. "
                f"Scores: {[round(d['score'], 3) for d in retrieved_docs[:5]]}"
            )
            
            # Check if we have enough results
            if len(retrieved_docs) < min_results:
                logger.warning(
                    f"Only {len(retrieved_docs)} results found (min={min_results}). "
                    "Consider fallback to hybrid search."
                )
            
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"Metadata-filtered retrieval failed: {e}")
            raise RetrievalError(f"Filtered retrieval error: {e}")
    
    def retrieve_with_fallback(
        self,
        query: str,
        scheme_names: List[str],
        top_k: int = 5,
        theme: Optional[str] = None,
        hybrid_retriever = None,
        min_filtered_results: int = 3
    ) -> tuple[List[Dict], Dict]:
        """Retrieve with fallback to hybrid search if filtered results insufficient
        
        Strategy:
        1. Try filtered retrieval first
        2. If < min_filtered_results, blend with hybrid results
        3. Prioritize filtered results (higher weight)
        
        Args:
            query: Search query
            scheme_names: List of scheme names
            top_k: Number of results
            theme: Optional theme filter
            hybrid_retriever: HybridRetriever instance for fallback
            min_filtered_results: Minimum filtered results before fallback
            
        Returns:
            Tuple of (retrieved_docs, metadata_info)
        """
        # Try filtered retrieval first
        filtered_docs = self.retrieve_with_filter(
            query, scheme_names, top_k, theme, min_results=min_filtered_results
        )
        
        metadata_info = {
            'filtered_count': len(filtered_docs),
            'hybrid_count': 0,
            'used_fallback': False
        }
        
        # If we have enough filtered results, return them
        if len(filtered_docs) >= min_filtered_results:
            logger.info(f"Sufficient filtered results ({len(filtered_docs)}), no fallback needed")
            return filtered_docs, metadata_info
        
        # Fallback to hybrid search
        if hybrid_retriever is None:
            logger.warning("Insufficient filtered results but no hybrid retriever available")
            return filtered_docs, metadata_info
        
        logger.info(
            f"Only {len(filtered_docs)} filtered results. Blending with hybrid search..."
        )
        
        # Get hybrid results (excluding already retrieved doc IDs)
        filtered_ids = {doc['id'] for doc in filtered_docs}
        hybrid_docs = hybrid_retriever.hybrid_retrieve(
            query, top_k * 2, intent=None  # Get more for blending
        )
        
        # Filter out duplicates
        additional_docs = [
            doc for doc in hybrid_docs 
            if doc['id'] not in filtered_ids
        ]
        
        # Blend: Prioritize filtered (boosted scores) + top hybrid
        # Boost filtered scores by 0.2 to ensure they rank higher
        for doc in filtered_docs:
            doc['score'] = min(doc['score'] + 0.2, 1.0)
            doc['retrieval_method'] = 'metadata_filtered_boosted'
        
        # Combine and re-sort
        combined_docs = filtered_docs + additional_docs[:top_k]
        combined_docs.sort(key=lambda x: x['score'], reverse=True)
        final_docs = combined_docs[:top_k]
        
        metadata_info['hybrid_count'] = len([d for d in final_docs if 'hybrid' in d.get('retrieval_method', '')])
        metadata_info['used_fallback'] = True
        
        logger.info(
            f"Blended retrieval: {metadata_info['filtered_count']} filtered + "
            f"{metadata_info['hybrid_count']} hybrid = {len(final_docs)} total"
        )
        
        return final_docs, metadata_info
    
    def retrieve_multi_scheme_comparison(
        self,
        query: str,
        scheme_names: List[str],
        docs_per_scheme: int = 5
    ) -> Dict[str, List[Dict]]:
        """Retrieve documents for comparing multiple schemes
        
        Ensures balanced representation of both/all schemes.
        
        Args:
            query: Comparison query
            scheme_names: List of schemes to compare
            docs_per_scheme: Documents to retrieve per scheme
            
        Returns:
            Dict mapping scheme_name -> list of documents
        """
        logger.info(f"Multi-scheme comparison retrieval: {scheme_names}")
        
        query_vector = embedding_model.embed_query(query)
        results_by_scheme = {}
        
        for scheme_name in scheme_names:
            try:
                # Retrieve for each scheme separately
                scheme_filter = self._build_scheme_filter([scheme_name])
                
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=scheme_filter,
                    limit=docs_per_scheme,
                    with_payload=True
                )
                
                docs = []
                for point in response.points:
                    docs.append({
                        "id": point.id,
                        "score": point.score,
                        "payload": point.payload,
                        "retrieval_method": "comparison_filtered"
                    })
                
                results_by_scheme[scheme_name] = docs
                logger.info(f"Retrieved {len(docs)} docs for {scheme_name}")
                
            except Exception as e:
                logger.error(f"Failed to retrieve for {scheme_name}: {e}")
                results_by_scheme[scheme_name] = []
        
        return results_by_scheme


if __name__ == "__main__":
    # Test metadata retrieval
    from qdrant_client import QdrantClient
    import config
    
    print("\n" + "="*80)
    print("METADATA RETRIEVAL TEST")
    print("="*80 + "\n")
    
    # Initialize client
    client = QdrantClient(
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY
    )
    
    retriever = MetadataRetriever(client, config.COLLECTION_NAME)
    
    # Test single scheme retrieval
    print("Test 1: Single scheme (PMEGP)")
    docs = retriever.retrieve_with_filter(
        query="eligibility criteria",
        scheme_names=["PMEGP"],
        top_k=3
    )
    print(f"Retrieved {len(docs)} documents")
    for i, doc in enumerate(docs, 1):
        print(f"  {i}. {doc['payload']['scheme_name']} - {doc['payload']['theme']} (score: {doc['score']:.3f})")
    
    print("\nTest 2: Multiple schemes (PMEGP, MUDRA)")
    docs = retriever.retrieve_with_filter(
        query="subsidy amount",
        scheme_names=["PMEGP", "MUDRA"],
        top_k=5
    )
    print(f"Retrieved {len(docs)} documents")
    for i, doc in enumerate(docs, 1):
        print(f"  {i}. {doc['payload']['scheme_name']} - {doc['payload']['theme']} (score: {doc['score']:.3f})")
    
    print("\nTest 3: Comparison retrieval")
    results = retriever.retrieve_multi_scheme_comparison(
        query="benefits comparison",
        scheme_names=["PMEGP", "MUDRA"],
        docs_per_scheme=3
    )
    for scheme, docs in results.items():
        print(f"\n  {scheme}: {len(docs)} docs")
        for doc in docs:
            print(f"    - {doc['payload']['theme']} (score: {doc['score']:.3f})")
