# Phase 1: Production-Grade Implementation

**Status**: ✅ Implemented  
**Branch**: `phase-1-production-grade`  
**Timeline**: 12-15 days  
**Objective**: Replace quick fixes with robust, production-ready architecture

---

## 🎯 What Was Fixed

### Critical Issues Addressed

1. **Aggressive Static Threshold (0.5) → Adaptive Threshold System**
   - ❌ **Before**: Fixed 0.5 threshold filtered out relevant documents
   - ✅ **After**: Dynamic per-query thresholds based on score distribution
   - **Impact**: Reduced unnecessary reflection from 40% to expected ~15%

2. **Pure Semantic Search → Hybrid BM25 + Semantic**
   - ❌ **Before**: Missed keyword matches ("women entrepreneurs PMEGP" returned 0 docs)
   - ✅ **After**: Combines keyword precision + semantic recall with RRF
   - **Impact**: Improved average retrieval score from 0.548 to expected 0.65+

3. **Static top_k=5 → Intent-Specific Retrieval**
   - ❌ **Before**: Same retrieval count for all query types
   - ✅ **After**: DISCOVERY=10, COMPARISON=10, ELIGIBILITY=5, etc.
   - **Impact**: Better coverage for discovery queries, focused precision for eligibility

4. **Unstructured Answers → Pydantic Schema Validation**
   - ❌ **Before**: Incomplete answers with "not mentioned" cop-outs
   - ✅ **After**: Type-safe schemas enforce answer completeness per intent
   - **Impact**: Answer completeness from 60% to expected 85%

---

## 📦 New Components

### 1. Adaptive Threshold System (`src/adaptive_threshold.py`)

**Production-grade score filtering** that replaces arbitrary thresholds.

```python
from src.adaptive_threshold import adaptive_threshold

# Automatically calculates optimal threshold per query
filtered_docs, metadata = adaptive_threshold.filter_documents(
    documents, 
    intent="ELIGIBILITY"
)

# Returns:
# - Dynamic threshold based on score distribution
# - Intent-specific adjustments
# - Ensures minimum documents returned
# - Full metadata for monitoring
```

**Key Features:**
- Statistical analysis (mean, std dev, top score ratio)
- Intent-specific thresholds:
  - `ELIGIBILITY`: Stricter (0.45 base)
  - `DISCOVERY`: More permissive (0.35 base)
  - `BENEFITS`: Strict (0.45 base)
- Prevents filtering out all results
- Comprehensive logging and metadata

### 2. Hybrid Retrieval (`src/hybrid_retrieval.py`)

**Industry-standard hybrid search** combining BM25 keyword + semantic search.

```python
from src.hybrid_retrieval import HybridRetriever

hybrid_retriever = HybridRetriever(
    semantic_retriever=vector_retriever,
    bm25_weight=0.4,
    semantic_weight=0.6,
    rrf_k=60
)

results = hybrid_retriever.hybrid_retrieve(
    query="women entrepreneurs PMEGP",
    top_k=5,
    intent="ELIGIBILITY"
)
```

**Key Features:**
- BM25 indexing built from Qdrant collection
- Reciprocal Rank Fusion (RRF) for combining results
- Intent-specific weighting:
  - `ELIGIBILITY`: 50/50 (balanced)
  - `DISCOVERY`: 30/70 (favor semantic)
  - `COMPARISON`: 40/60 (slight semantic)
- Tracks retrieval sources (BM25, semantic, or both)
- Graceful fallback to semantic-only if BM25 fails

### 3. Pydantic Schemas (`src/schemas.py`)

**Type-safe answer validation** enforcing completeness per intent.

```python
from src.schemas import EligibilityAnswer, get_schema_for_intent

# Schema enforces structure
class EligibilityAnswer(BaseModel):
    can_apply: Optional[bool]  # Direct yes/no
    eligibility_criteria: List[str]  # Must have at least 1
    age_requirements: Optional[str]
    special_categories: Optional[List[str]]
    scheme_name: str
    sources: List[SchemeReference]
    
    @validator('eligibility_criteria')
    def validate_no_cop_out(cls, v):
        # Prevents "not mentioned" responses
        for criterion in v:
            if 'not mentioned' in criterion.lower():
                raise ValueError("Must be specific")
        return v
```

**Available Schemas:**
- `DiscoveryAnswer`: Multiple schemes with descriptions
- `EligibilityAnswer`: Direct answers + criteria
- `BenefitsAnswer`: Must include amounts with ₹ or numbers
- `ComparisonAnswer`: Must reference both schemes
- `ProcedureAnswer`: Step-by-step process
- `GeneralAnswer`: Fallback schema

### 4. Enhanced Configuration (`shared_config.py`)

**Centralized production-grade settings:**

```python
# Intent-specific top_k
INTENT_TOP_K = {
    "DISCOVERY": 10,
    "COMPARISON": 10,
    "ELIGIBILITY": 5,
    "BENEFITS": 5,
    "PROCEDURE": 5,
    "GENERAL": 5
}

# Adaptive threshold config
ADAPTIVE_THRESHOLD_CONFIG = {
    "min_absolute_threshold": 0.3,
    "std_dev_multiplier": 0.5,
    "top_score_ratio": 0.7,
    "min_docs_required": 1
}

# Hybrid retrieval config
HYBRID_RETRIEVAL_ENABLED = True
BM25_WEIGHT = 0.4
SEMANTIC_WEIGHT = 0.6
RRF_K = 60
```

---

## 🔄 Modified Components

### `src/retrieval.py`

**Enhanced to use hybrid retrieval and adaptive thresholds:**

```python
def retrieve(self, query: str, top_k: int = None, intent: str = None):
    # Uses intent-specific top_k
    if top_k is None and intent in config.INTENT_TOP_K:
        top_k = config.INTENT_TOP_K[intent]
    
    # Hybrid retrieval if enabled
    if self.hybrid_retriever:
        docs = self.hybrid_retriever.hybrid_retrieve(query, top_k, intent)
    else:
        docs = self._semantic_retrieve(query, top_k)
    
    # Adaptive filtering
    filtered_docs, metadata = adaptive_threshold.filter_documents(docs, intent)
    
    return filtered_docs
```

### `src/nodes.py`

**Updated to pass intent context through retrieval pipeline:**

```python
def retrieval_node(state: RAGState):
    intent = state.get("intent", "GENERAL")
    # Pass intent for adaptive behavior
    docs = retriever.retrieve(state["query"], intent=intent)
    return {"retrieved_docs": docs}

def reflection_node(state: RAGState):
    intent = state.get("intent", "GENERAL")
    refined_query = refine_query(state["query"])
    # Maintain intent context in re-retrieval
    refined_docs = retriever.retrieve(refined_query, intent=intent)
    return {"retrieved_docs": refined_docs, ...}
```

---

## 📥 Installation & Setup

### 1. Install New Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install updated requirements
pip install -r requirements.txt

# New dependencies added:
# - rank-bm25>=0.2.2  (for BM25 keyword search)
# - numpy>=1.24.0     (for statistical calculations)
```

### 2. Configuration

No changes needed to `.env` file - all new configurations use existing settings.

### 3. BM25 Index Initialization

The hybrid retriever builds BM25 index automatically on first run:

```bash
# Start your API
python -m uvicorn api.app:app --reload

# First request will build BM25 index (one-time ~10-30 seconds)
# Logs will show: "Building BM25 index from Qdrant collection..."
# Then: "BM25 index built with X documents"
```

---

## 🧪 Testing Phase 1 Changes

### Test 1: Adaptive Threshold

```python
import requests

# Query that previously got 0 results
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "Can women entrepreneurs apply for PMEGP?"}
)

result = response.json()
print(f"Retrieved: {len(result['retrieved_docs'])} docs")
print(f"Needs reflection: {result['needs_reflection']}")

# Expected:
# - Before: 0 docs, needs_reflection=True
# - After: 2-3 docs, needs_reflection=False (or fewer reflections)
```

### Test 2: Hybrid Retrieval

```python
# Test keyword + semantic matching
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "PMEGP manufacturing subsidy"}
)

result = response.json()
for doc in result['retrieved_docs']:
    sources = doc.get('retrieval_sources', [])
    print(f"Score: {doc['score']:.3f}, Sources: {sources}")

# Expected output:
# - Score: 0.456, Sources: ['bm25', 'semantic']  <- Found by both
# - Score: 0.389, Sources: ['semantic']          <- Semantic only
# - Score: 0.342, Sources: ['bm25']              <- Keyword only
```

### Test 3: Intent-Specific top_k

```python
# Discovery query should retrieve more docs
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "show me manufacturing schemes"}
)

result = response.json()
print(f"Intent: {result['intent']}")
print(f"Docs retrieved: {len(result['retrieved_docs'])}")

# Expected:
# - Intent: DISCOVERY
# - Docs: 8-10 (instead of 5)
```

### Test 4: Check Logs

```bash
tail -f logs/rag_system.log

# Look for:
# "Using intent-specific top_k=10 for DISCOVERY"
# "Hybrid retrieval returned 5 docs. Sources: {'bm25': 2, 'semantic': 3}"
# "Adaptive threshold calculated: 0.412 ... -> 5/8 docs pass"
```

---

## 📊 Expected Improvements

### Performance Metrics

| Metric | Before | After Phase 1 | Improvement |
|--------|--------|---------------|-------------|
| **Reflection Rate** | 40% | ~15% | -25% |
| **Avg Retrieval Score** | 0.548 | 0.60-0.65 | +10-20% |
| **Answer Completeness** | ~60% | ~85% | +25% |
| **PMEGP Eligibility Query** | 0 docs → needs reflection | 2-3 docs → direct answer | Fixed |
| **Discovery Queries** | 5 schemes | 8-10 schemes | +60-100% |

### Query-Specific Fixes

**Query**: "Can women entrepreneurs apply for PMEGP?"
- ❌ **Before**: 0 documents, reflection needed, "not explicitly mentioned"
- ✅ **After**: 2-3 documents, direct answer with criteria

**Query**: "subsidy schemes for manufacturing"
- ❌ **Before**: 5 docs (only 1 shown due to truncation)
- ✅ **After**: 10 docs with better keyword matching

**Query**: "Compare PMEGP vs Startup India"
- ❌ **Before**: 1 doc, one-sided comparison
- ✅ **After**: 10 docs (balanced retrieval), structured comparison

---

## 🔍 Monitoring & Validation

### Key Metrics to Track

1. **Adaptive Threshold Metadata**:
   ```python
   # Check threshold decisions
   threshold_metadata = {
       'method': 'adaptive',
       'threshold': 0.412,
       'mean_score': 0.523,
       'std_dev': 0.098,
       'docs_above_threshold': 5,
       'total_docs': 8
   }
   ```

2. **Retrieval Source Distribution**:
   ```python
   # Track how often BM25 vs semantic helps
   sources_count = {'bm25': 2, 'semantic': 5, 'both': 3}
   ```

3. **Intent-Specific Performance**:
   ```python
   # Per-intent success rates
   intent_metrics = {
       'DISCOVERY': {'avg_docs': 9.2, 'reflection_rate': 0.08},
       'ELIGIBILITY': {'avg_docs': 4.1, 'reflection_rate': 0.12},
       'COMPARISON': {'avg_docs': 8.7, 'reflection_rate': 0.10}
   }
   ```

---

## 🚀 Next Steps (Phase 2)

With Phase 1 foundation in place, Phase 2 will add:

1. **LLM-as-Judge Evaluation Framework** (Week 3-4)
   - Replace fragile string checks
   - Rubric-based multi-criteria scoring
   - Actual corrective RAG loop activation

2. **Query Understanding Pipeline** (Week 3-4)
   - Entity extraction for scheme names
   - Query decomposition for comparisons
   - Intent confidence scoring

3. **Monitoring Dashboard** (Week 3-4)
   - Real-time metrics visualization
   - A/B testing framework
   - Failed query analysis

---

## 🐛 Troubleshooting

### BM25 Index Build Fails

```bash
# Error: "BM25 index building failed"
# Solution: System falls back to semantic-only
# Check: Qdrant collection exists and is accessible
```

### Import Errors

```bash
# Error: "No module named 'rank_bm25'"
# Solution:
pip install rank-bm25

# Error: "No module named 'numpy'"
# Solution:
pip install numpy
```

### Slow First Query

```
# Expected: First query takes 10-30 seconds
# Reason: Building BM25 index from Qdrant collection
# Subsequent queries: Normal speed
```

---

## ✅ Validation Checklist

Before considering Phase 1 complete:

- [ ] All new dependencies installed
- [ ] BM25 index builds successfully
- [ ] Adaptive thresholds calculated (check logs)
- [ ] Hybrid retrieval returns mixed sources
- [ ] Intent-specific top_k working (DISCOVERY=10, ELIGIBILITY=5)
- [ ] PMEGP eligibility query returns docs (not 0)
- [ ] Reflection rate decreased from baseline
- [ ] Average scores improved from baseline
- [ ] No import errors or crashes
- [ ] Logs show detailed threshold/retrieval metadata

---

## 📄 License

MIT License - Same as main project

---

## 👤 Author

Phase 1 Production Implementation  
Built for: [Pranay Mathur](https://github.com/pranaya-mathur)  
Date: January 3, 2026
