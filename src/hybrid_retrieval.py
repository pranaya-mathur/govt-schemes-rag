"""Hybrid retrieval combining BM25 (keyword) and semantic search

Implements industry-standard hybrid search with:
- BM25 for lexical/keyword matching
- Semantic search via embeddings
- Reciprocal Rank Fusion (RRF) for combining results
- Intent-specific weighting
- Score normalization for adaptive threshold compatibility
"""
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict
from rank_bm25 import BM25Okapi
from src.logger import setup_logger

logger = setup_logger(__name__)


class HybridRetriever:
    """Hybrid retriever combining keyword and semantic search"""
    
    def __init__(
        self,
        semantic_retriever,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6,
        rrf_k: int = 60
    ):
        """
        Args:
            semantic_retriever: Vector retriever instance
            bm25_weight: Weight for BM25 scores (default 0.4)
            semantic_weight: Weight for semantic scores (default 0.6)
            rrf_k: RRF parameter (default 60, standard value)
        """
        self.semantic_retriever = semantic_retriever
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        self.rrf_k = rrf_k
        
        # Build BM25 index
        self._build_bm25_index()
        
        logger.info(
            f"Hybrid retriever initialized with BM25:{bm25_weight}, "
            f"Semantic:{semantic_weight}, RRF k={rrf_k}"
        )
    
    def _build_bm25_index(self):
        """Build BM25 index from Qdrant collection"""
        try:
            logger.info("Building BM25 index from Qdrant collection...")
            
            # Scroll through all documents in collection
            all_docs = []
            offset = None
            
            while True:
                results = self.semantic_retriever.client.scroll(
                    collection_name=self.semantic_retriever.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                points, offset = results
                
                if not points:
                    break
                
                for point in points:
                    payload = point.payload
                    # Combine scheme name and text for better keyword matching
                    scheme_name = payload.get('scheme_name', '')
                    text = payload.get('text', '')
                    theme = payload.get('theme', '')
                    
                    # Create searchable text
                    searchable_text = f"{scheme_name} {theme} {text}"
                    
                    all_docs.append({
                        'id': point.id,
                        'text': searchable_text,
                        'payload': payload
                    })
                
                if offset is None:
                    break
            
            # Tokenize documents for BM25
            self.doc_corpus = all_docs
            tokenized_corpus = [
                doc['text'].lower().split() 
                for doc in all_docs
            ]
            
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.info(f"BM25 index built with {len(all_docs)} documents")
            
        except Exception as e:
            logger.error(f"BM25 index building failed: {e}")
            # Fallback to semantic-only if BM25 fails
            self.bm25 = None
            self.doc_corpus = []
    
    def _bm25_search(self, query: str, top_k: int) -> List[Dict]:
        """Perform BM25 keyword search"""
        if not self.bm25 or not self.doc_corpus:
            logger.warning("BM25 index not available, skipping keyword search")
            return []
        
        try:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            
            # Get top-k results
            top_indices = np.argsort(scores)[::-1][:top_k * 2]  # Get more for fusion
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include non-zero scores
                    results.append({
                        'id': self.doc_corpus[idx]['id'],
                        'score': float(scores[idx]),
                        'payload': self.doc_corpus[idx]['payload'],
                        'source': 'bm25'
                    })
            
            logger.debug(f"BM25 search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def _get_intent_weights(self, intent: str) -> Tuple[float, float]:
        """
        Get intent-specific weights for BM25 vs semantic
        
        Different intents benefit from different balances:
        - ELIGIBILITY: More keyword (contains specific terms)
        - DISCOVERY: More semantic (conceptual matching)
        """
        intent_weights = {
            'ELIGIBILITY': (0.5, 0.5),   # Balanced - need exact criteria
            'DISCOVERY': (0.3, 0.7),     # More semantic - broad search
            'BENEFITS': (0.5, 0.5),      # Balanced - need specific amounts
            'COMPARISON': (0.4, 0.6),    # Slightly more semantic
            'PROCEDURE': (0.45, 0.55),   # Balanced with slight semantic
            'GENERAL': (0.4, 0.6)        # Default: favor semantic
        }
        
        return intent_weights.get(intent, (self.bm25_weight, self.semantic_weight))
    
    def _reciprocal_rank_fusion(
        self, 
        bm25_results: List[Dict], 
        semantic_results: List[Dict],
        bm25_weight: float,
        semantic_weight: float
    ) -> List[Dict]:
        """
        Combine results using Reciprocal Rank Fusion (RRF) with score normalization
        
        RRF formula: score(d) = sum over all rankings of 1/(k + rank(d))
        where k is a constant (typically 60)
        
        Normalized to 0.0-1.0 range for adaptive threshold compatibility
        """
        # Build rank maps with original semantic scores for reference
        doc_scores = defaultdict(lambda: {
            'rrf_score': 0, 
            'sources': set(), 
            'data': None,
            'semantic_score': 0
        })
        
        # Add BM25 rankings
        for rank, doc in enumerate(bm25_results):
            doc_id = doc['id']
            rrf_score = bm25_weight / (self.rrf_k + rank + 1)
            doc_scores[doc_id]['rrf_score'] += rrf_score
            doc_scores[doc_id]['sources'].add('bm25')
            doc_scores[doc_id]['data'] = doc
        
        # Add semantic rankings and preserve original scores
        for rank, doc in enumerate(semantic_results):
            doc_id = doc['id']
            rrf_score = semantic_weight / (self.rrf_k + rank + 1)
            doc_scores[doc_id]['rrf_score'] += rrf_score
            doc_scores[doc_id]['sources'].add('semantic')
            doc_scores[doc_id]['semantic_score'] = doc.get('score', 0)
            if doc_scores[doc_id]['data'] is None:
                doc_scores[doc_id]['data'] = doc
        
        # Calculate max possible RRF score (doc appears first in both)
        max_rrf_score = (bm25_weight + semantic_weight) / (self.rrf_k + 1)
        
        # Normalize RRF scores and blend with semantic scores
        for doc_id in doc_scores:
            raw_rrf = doc_scores[doc_id]['rrf_score']
            normalized_rrf = raw_rrf / max_rrf_score  # Now in 0.0-1.0 range
            semantic_score = doc_scores[doc_id]['semantic_score']
            
            # Blend: 70% normalized RRF (for ranking) + 30% semantic (for absolute quality)
            # This preserves RRF ranking benefits while maintaining score scale
            final_score = (0.7 * normalized_rrf) + (0.3 * semantic_score)
            doc_scores[doc_id]['rrf_score'] = final_score
        
        # Sort by blended score
        ranked_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1]['rrf_score'],
            reverse=True
        )
        
        # Format results
        results = []
        for doc_id, info in ranked_docs:
            doc_data = info['data']
            doc_data['score'] = info['rrf_score']  # Use normalized blended score
            doc_data['retrieval_sources'] = list(info['sources'])
            results.append(doc_data)
        
        # Fixed f-string syntax
        top_score = results[0]['score'] if results else 0
        logger.debug(
            f"RRF normalization: max_rrf={max_rrf_score:.4f}, "
            f"top_score={top_score:.3f}"
        )
        
        return results
    
    def hybrid_retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        intent: str = None
    ) -> List[Dict]:
        """
        Perform hybrid retrieval combining BM25 and semantic search
        
        Args:
            query: Search query
            top_k: Number of results to return
            intent: Optional query intent for weighting adjustment
        
        Returns:
            List of retrieved documents with normalized scores (0.0-1.0)
        """
        logger.info(f"Hybrid retrieval for query: '{query[:50]}...' (intent={intent})")
        
        # Get intent-specific weights
        bm25_w, semantic_w = self._get_intent_weights(intent)
        logger.debug(f"Using weights - BM25: {bm25_w}, Semantic: {semantic_w}")
        
        # Perform both searches
        bm25_results = self._bm25_search(query, top_k)
        # Call internal _semantic_retrieve() to avoid recursion
        semantic_results = self.semantic_retriever._semantic_retrieve(query, top_k * 2)
        
        # If BM25 failed, fall back to semantic only
        if not bm25_results:
            logger.warning("BM25 returned no results, using semantic-only")
            return semantic_results[:top_k]
        
        # Combine using RRF with normalization
        combined_results = self._reciprocal_rank_fusion(
            bm25_results,
            semantic_results,
            bm25_w,
            semantic_w
        )
        
        # Return top-k
        final_results = combined_results[:top_k]
        
        # Log retrieval sources and score range
        sources_count = defaultdict(int)
        for doc in final_results:
            for source in doc.get('retrieval_sources', []):
                sources_count[source] += 1
        
        # Fixed f-string syntax  
        if final_results:
            score_range = f"{final_results[0]['score']:.3f}-{final_results[-1]['score']:.3f}"
        else:
            score_range = "N/A"
        
        logger.info(
            f"Hybrid retrieval returned {len(final_results)} docs. "
            f"Sources: {dict(sources_count)}, Score range: {score_range}"
        )
        
        return final_results
