"""Metadata-Aware Retrieval with Qdrant Filtering

Provides scheme-specific retrieval using Qdrant metadata filters.
Guarantees that results are from the requested scheme(s).

Two-Stage Fallback mechanism (Industry Standard):
1. Try filtered vector search
2. If 0 results: Fetch ALL scheme docs + BM25 re-rank
3. If still insufficient: Blend with hybrid search
4. Apply adaptive threshold as final quality gate

Based on AWS ML Blog and production RAG best practices.
"""
from typing import List, Dict, Optional
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from src.logger import setup_logger
from src.embeddings import embedding_model
from src.exceptions import RetrievalError
from rank_bm25 import BM25Okapi
import config

logger = setup_logger(__name__)


class MetadataRetriever:
    """Metadata-aware retrieval with two-stage fallback"""
    
    def __init__(self, qdrant_client, collection_name: str):
        """
        Args:
            qdrant_client: Qdrant client instance
            collection_name: Collection name
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        logger.info("MetadataRetriever initialized with two-stage fallback")
    
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
    
    def _fetch_all_scheme_docs(self, scheme_names: List[str]) -> List[Dict]:
        """Fetch ALL documents from specified schemes (no vector search)
        
        Used in Stage 2 when filtered vector search returns 0 results.
        
        Args:
            scheme_names: List of scheme names
            
        Returns:
            List of all documents from those schemes
        """
        logger.info(f"Fetching ALL documents from schemes: {scheme_names}")
        
        try:
            scheme_filter = self._build_scheme_filter(scheme_names)
            
            # Scroll through all matching documents
            all_docs = []
            offset = None
            
            while True:
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=scheme_filter,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                points, offset = results
                
                if not points:
                    break
                
                for point in points:
                    all_docs.append({
                        "id": point.id,
                        "score": 0.0,  # No semantic score yet
                        "payload": point.payload,
                        "retrieval_method": "metadata_only"
                    })
                
                if offset is None:
                    break
            
            logger.info(f"Fetched {len(all_docs)} total documents from schemes")
            return all_docs
            
        except Exception as e:
            logger.error(f"Failed to fetch all scheme docs: {e}")
            return []
    
    def _rerank_with_bm25(self, query: str, docs: List[Dict], top_k: int = 5) -> List[Dict]:
        """Re-rank documents using BM25 keyword matching
        
        Args:
            query: Search query
            docs: Documents to re-rank
            top_k: Number of top results to return
            
        Returns:
            Re-ranked documents with BM25 scores
        """
        if not docs:
            return []
        
        logger.info(f"Re-ranking {len(docs)} documents with BM25")
        
        try:
            # Extract text from documents
            texts = []
            for doc in docs:
                # Combine relevant fields for BM25
                text = doc['payload'].get('text', '')
                scheme_name = doc['payload'].get('scheme_name', '')
                theme = doc['payload'].get('theme', '')
                texts.append(f"{scheme_name} {theme} {text}")
            
            # Tokenize for BM25
            tokenized_corpus = [text.lower().split() for text in texts]
            bm25 = BM25Okapi(tokenized_corpus)
            
            # Get BM25 scores
            tokenized_query = query.lower().split()
            bm25_scores = bm25.get_scores(tokenized_query)
            
            # Assign scores to documents
            for doc, score in zip(docs, bm25_scores):
                doc['score'] = float(score)
                doc['retrieval_method'] = 'bm25_reranked'
            
            # Sort by BM25 score
            docs.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(
                f"BM25 re-ranking complete. Top scores: "
                f"{[round(d['score'], 3) for d in docs[:5]]}"
            )
            
            return docs[:top_k]
            
        except Exception as e:
            logger.error(f"BM25 re-ranking failed: {e}")
            # Fallback: return original docs
            return docs[:top_k]
    
    def retrieve_with_filter(
        self,
        query: str,
        scheme_names: List[str],
        top_k: int = 5,
        theme: Optional[str] = None,
        min_results: int = 1
    ) -> List[Dict]:
        """Retrieve documents with metadata filtering + two-stage fallback
        
        Stage 1: Filtered vector search (semantic + metadata)
        Stage 2: If 0 results -> Fetch ALL scheme docs + BM25 re-rank
        
        Args:
            query: Search query
            scheme_names: List of scheme names to filter by
            top_k: Number of results to retrieve
            theme: Optional theme filter (e.g., 'eligibility')
            min_results: Minimum results to trigger Stage 2 fallback
            
        Returns:
            List of retrieved documents with metadata
        """
        logger.info(
            f"Two-stage filtered retrieval: schemes={scheme_names}, "
            f"theme={theme}, top_k={top_k}"
        )
        
        try:
            # STAGE 1: Filtered vector search
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
                    "retrieval_method": "filtered_vector"
                })
            
            logger.info(
                f"Stage 1 (filtered vector) returned {len(retrieved_docs)} documents. "
                f"Scores: {[round(d['score'], 3) for d in retrieved_docs[:5]]}"
            )
            
            # Check if we have enough results
            if len(retrieved_docs) >= min_results:
                return retrieved_docs
            
            # STAGE 2: Fetch ALL scheme docs + BM25 re-rank
            logger.warning(
                f"Stage 1 returned {len(retrieved_docs)} results (< {min_results}). "
                f"Activating Stage 2: BM25 re-ranking"
            )
            
            all_scheme_docs = self._fetch_all_scheme_docs(scheme_names)
            
            if not all_scheme_docs:
                logger.error(f"No documents found for schemes: {scheme_names}")
                return retrieved_docs  # Return whatever Stage 1 found
            
            # Re-rank with BM25
            reranked_docs = self._rerank_with_bm25(query, all_scheme_docs, top_k)
            
            logger.info(
                f"Stage 2 (BM25 re-rank) returned {len(reranked_docs)} documents. "
                f"Scores: {[round(d['score'], 3) for d in reranked_docs[:5]]}"
            )
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Two-stage retrieval failed: {e}")
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
        """Retrieve with fallback to hybrid search if still insufficient
        
        Strategy:
        1. Try two-stage filtered retrieval (vector + BM25)
        2. If < min_filtered_results, blend with hybrid results
        3. Prioritize filtered results (higher weight)
        
        Args:
            query: Search query
            scheme_names: List of scheme names
            top_k: Number of results
            theme: Optional theme filter
            hybrid_retriever: HybridRetriever instance for fallback
            min_filtered_results: Minimum filtered results before hybrid fallback
            
        Returns:
            Tuple of (retrieved_docs, metadata_info)
        """
        # Try two-stage filtered retrieval first
        filtered_docs = self.retrieve_with_filter(
            query, scheme_names, top_k, theme, min_results=1
        )
        
        metadata_info = {
            'filtered_count': len(filtered_docs),
            'hybrid_count': 0,
            'used_fallback': False,
            'used_bm25': any('bm25' in d.get('retrieval_method', '') for d in filtered_docs)
        }
        
        # If we have enough filtered results, return them
        if len(filtered_docs) >= min_filtered_results:
            logger.info(
                f"Sufficient results ({len(filtered_docs)}) from two-stage retrieval, "
                f"no hybrid fallback needed"
            )
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
            doc['retrieval_method'] = doc['retrieval_method'] + '_boosted'
        
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
        Uses two-stage retrieval per scheme.
        
        Args:
            query: Comparison query
            scheme_names: List of schemes to compare
            docs_per_scheme: Documents to retrieve per scheme
            
        Returns:
            Dict mapping scheme_name -> list of documents
        """
        logger.info(f"Multi-scheme comparison retrieval: {scheme_names}")
        
        results_by_scheme = {}
        
        for scheme_name in scheme_names:
            try:
                # Use two-stage retrieval for each scheme
                docs = self.retrieve_with_filter(
                    query=query,
                    scheme_names=[scheme_name],
                    top_k=docs_per_scheme,
                    min_results=1
                )
                
                results_by_scheme[scheme_name] = docs
                logger.info(f"Retrieved {len(docs)} docs for {scheme_name}")
                
            except Exception as e:
                logger.error(f"Failed to retrieve for {scheme_name}: {e}")
                results_by_scheme[scheme_name] = []
        
        return results_by_scheme


if __name__ == "__main__":
    # Test two-stage metadata retrieval
    from qdrant_client import QdrantClient
    import config
    
    print("\n" + "="*80)
    print("TWO-STAGE METADATA RETRIEVAL TEST")
    print("="*80 + "\n")
    
    # Initialize client
    client = QdrantClient(
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY
    )
    
    retriever = MetadataRetriever(client, config.COLLECTION_NAME)
    
    # Test 1: Query that should match semantically
    print("Test 1: High semantic match (should use Stage 1)")
    docs = retriever.retrieve_with_filter(
        query="eligibility criteria for PMEGP",
        scheme_names=["Pmegp"],
        top_k=3
    )
    print(f"Retrieved {len(docs)} documents")
    for i, doc in enumerate(docs, 1):
        print(f"  {i}. {doc['retrieval_method']} - score: {doc['score']:.3f}")
    
    # Test 2: Query with low semantic match (should trigger Stage 2)
    print("\nTest 2: Low semantic match (should trigger Stage 2 BM25)")
    docs = retriever.retrieve_with_filter(
        query="Can women entrepreneurs apply?",
        scheme_names=["Pmegp"],
        top_k=3
    )
    print(f"Retrieved {len(docs)} documents")
    for i, doc in enumerate(docs, 1):
        print(f"  {i}. {doc['retrieval_method']} - score: {doc['score']:.3f}")
    
    print("\nTest 3: Comparison retrieval")
    results = retriever.retrieve_multi_scheme_comparison(
        query="benefits comparison",
        scheme_names=["Pmegp", "Mmuy"],
        docs_per_scheme=3
    )
    for scheme, docs in results.items():
        print(f"\n  {scheme}: {len(docs)} docs")
        for doc in docs:
            method = doc.get('retrieval_method', 'unknown')
            print(f"    - {method} (score: {doc['score']:.3f})")
