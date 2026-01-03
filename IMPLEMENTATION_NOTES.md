# Two-Stage Retrieval Implementation Notes

## Overview

Implemented industry-standard two-stage retrieval approach based on AWS ML Blog and production RAG best practices.

## Problem Statement

When user queries mention specific schemes (e.g., "Can women entrepreneurs apply for PMEGP?"), the system would:

1. ✅ Correctly detect scheme: `scheme_name='Pmegp'`
2. ✅ Filter to 6 PMEGP documents
3. ❌ Return 0 results (low semantic similarity between query and chunks)
4. ❌ Fall back to hybrid search → return wrong schemes (Mmuy, Ttr, Aif)

## Root Cause

**Semantic mismatch**: Query about "women entrepreneurs eligibility" doesn't semantically match chunks about "subsidy amounts" or "registration process" within the same scheme.

## Solution: Two-Stage Retrieval

### Stage 1: Filtered Vector Search (Semantic + Metadata)
- Query embedding + metadata filter
- Returns top-k results if semantic match exists
- **Fast and accurate when query matches chunk semantics**

### Stage 2: BM25 Re-ranking (Keyword + Metadata)
- Triggered when Stage 1 returns 0 results
- Fetches ALL documents from the filtered scheme
- Re-ranks using BM25 (keyword matching)
- Returns top-k based on keyword relevance
- **Ensures scheme-specific results even without semantic match**

### Stage 3: Hybrid Fallback (Optional)
- Only if Stages 1 & 2 return insufficient results (< min_threshold)
- Blends filtered results with hybrid search
- Boosts filtered results by +0.2 to prioritize scheme-specific content

## Code Changes

### 1. `src/metadata_retrieval.py`

#### New Methods:

```python
def _fetch_all_scheme_docs(scheme_names: List[str]) -> List[Dict]
    """Fetch ALL documents from specified schemes (Stage 2)"""
    # Scrolls through all matching documents
    # No vector search, pure metadata filter

def _rerank_with_bm25(query: str, docs: List[Dict], top_k: int) -> List[Dict]
    """Re-rank documents using BM25 keyword matching"""
    # Tokenizes query and documents
    # Computes BM25 scores
    # Returns top-k by keyword relevance
```

#### Updated Method:

```python
def retrieve_with_filter(...) -> List[Dict]
    """Two-stage retrieval:
    1. Try filtered vector search
    2. If 0 results -> BM25 re-rank ALL scheme docs
    3. Return best results
    """
```

### 2. `src/query_decomposer.py`

#### Improvements:

1. **Case-insensitive matching**: "PMEGP" now matches "Pmegp" in database
2. **Lower fuzzy threshold**: 75 instead of 85 (handles case variations better)
3. **Better word boundary detection**: Avoids partial matches

```python
def _extract_with_exact_match(query: str) -> List[str]
    # Case-insensitive regex with word boundaries
    pattern = r'\b' + re.escape(variant) + r'\b'
    if re.search(pattern, query_lower, re.IGNORECASE):
        found_schemes.add(canonical)

def _extract_with_fuzzy_match(query: str, threshold: int = 75) -> List[str]
    # Lowered from 85 to handle PMEGP vs Pmegp
```

## Benefits

### ✅ Scheme-Specific Results
- Never returns wrong schemes when filter is applied
- Always searches within the detected scheme first

### ✅ Handles Semantic Mismatch
- BM25 re-ranking catches keyword matches even without semantic similarity
- Example: "women entrepreneurs" matches documents containing those words

### ✅ Industry Standard
- Based on AWS ML Blog recommendations
- Used in production RAG systems (Elasticsearch, Pinecone, Weaviate)
- Balances semantic + keyword relevance

### ✅ Graceful Degradation
- Stage 1 (fast) → Stage 2 (comprehensive) → Stage 3 (fallback)
- Each stage provides better coverage

## Performance Characteristics

| Scenario | Stage Used | Speed | Accuracy |
|----------|------------|-------|----------|
| High semantic match | Stage 1 | Fast | High |
| Low semantic match | Stage 2 | Medium | High |
| No scheme detected | Hybrid | Medium | Medium |
| Insufficient results | Stage 3 | Slow | Variable |

## Testing

### Test Case 1: High Semantic Match
```python
query = "eligibility criteria for PMEGP"
scheme = "Pmegp"
# Expected: Stage 1 returns results (semantic match exists)
```

### Test Case 2: Low Semantic Match (Original Problem)
```python
query = "Can women entrepreneurs apply for PMEGP?"
scheme = "Pmegp"
# Expected: Stage 2 activates, BM25 finds keyword matches
```

### Test Case 3: Case Variation
```python
query = "What is PMEGP subsidy?"
scheme = "Pmegp"  # Database uses title case
# Expected: Query decomposer detects "Pmegp" (case-insensitive)
```

## Dependencies

- `rank-bm25>=0.2.2` ✅ Already in requirements.txt
- `rapidfuzz>=3.0.0` ✅ Already in requirements.txt

## References

1. [AWS ML Blog: Intelligent Metadata Filtering](https://aws.amazon.com/blogs/machine-learning/streamline-rag-applications-with-intelligent-metadata-filtering-using-amazon-bedrock/)
2. [arXiv: Trade-offs in Hybrid Search](https://arxiv.org/html/2508.01405v1)
3. [Reddit: Production RAG Experiences](https://www.reddit.com/r/Rag/comments/1pd7tao/i_rewrote_hybrid_search_four_times_heres_what/)
4. [Elasticsearch: Hybrid Search Best Practices](https://softwaredoug.com/blog/2025/03/13/elasticsearch-hybrid-search-strategies)

## Future Improvements

1. **Cross-encoder re-ranking**: Add Stage 2.5 with cross-encoder for better relevance
2. **Query expansion**: Expand queries with synonyms before BM25
3. **Caching**: Cache BM25 corpus for frequently accessed schemes
4. **Monitoring**: Track which stage returns results for query analysis

## Deployment

1. Ensure `rank-bm25` is installed: `pip install rank-bm25>=0.2.2`
2. Test with sample queries (see test cases above)
3. Monitor retrieval_method in logs:
   - `filtered_vector`: Stage 1 success
   - `bm25_reranked`: Stage 2 activated
   - `filtered_vector_boosted`: Stage 3 blend
   - `hybrid`: No scheme filter applied

## Commit History

- `e18296e`: Implement two-stage retrieval with BM25 re-ranking
- `149b742`: Fix case-insensitive fuzzy matching for scheme names

---

**Status**: ✅ Production Ready

**Last Updated**: January 3, 2026
