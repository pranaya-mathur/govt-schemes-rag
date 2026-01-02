# Data Pipeline

Complete pipeline for processing government schemes data into Qdrant vector database.

## Overview

```
Raw Schemes (JSON) → LLM Chunking → BGE-M3 Embeddings → Qdrant Index
```

## Components

### 1. **chunking.py**
- **LLM-Powered Intelligent Chunking**
- Uses `ChatOllama` with `llama3.1:8b`
- Theme-based splitting: benefits, eligibility, application-steps, documents, contact, general
- Returns enriched chunks with metadata

### 2. **indexing.py**
- **Qdrant Vector Database Indexing**
- Uses BGE-M3 embeddings (1024-dim)
- Batch upload with progress tracking
- Collection management

### 3. **run_pipeline.py**
- **Complete Pipeline Runner**
- Load → Chunk → Index
- Progress tracking and statistics

## Setup

### Prerequisites

1. **Start Ollama** (for chunking):
```bash
# Pull model
ollama pull llama3.1:8b

# Start Ollama server
ollama serve
```

2. **Environment Variables** (in `.env`):
```bash
OLLAMA_BASE_URL=http://localhost:11434
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
```

## Usage

### Run Complete Pipeline

```bash
python data_pipeline/run_pipeline.py path/to/schemes.json --output chunks.json
```

### Individual Steps

#### 1. Chunking Only

```python
from data_pipeline.chunking import LLMChunker

chunker = LLMChunker()
chunks = chunker.chunk_scheme(scheme_data)
```

#### 2. Indexing Only

```python
from data_pipeline.indexing import QdrantIndexer

indexer = QdrantIndexer()
indexer.create_collection()
indexer.index_chunks(chunks)
```

## Input Format

### schemes.json

```json
[
  {
    "scheme_name": "PMEGP",
    "official_url": "https://www.kviconline.gov.in/pmegp",
    "ministry": "Ministry of MSME",
    "text": "Full scheme description with benefits, eligibility, procedure..."
  },
  ...
]
```

## Output Format

### Chunks

Each chunk contains:
```json
{
  "scheme_name": "PMEGP",
  "official_url": "https://www.kviconline.gov.in/pmegp",
  "ministry": "Ministry of MSME",
  "theme": "benefits",
  "text": "Get 25-35% subsidy on project cost..."
}
```

### Qdrant Points

Each point has:
- **Vector**: 1024-dim BGE-M3 embedding
- **Payload**: All chunk metadata (scheme_name, theme, text, etc.)

## Configuration

Edit `data_pipeline/config.py`:

```python
# Model
CHUNKING_MODEL = "llama3.1:8b"
EMBEDDING_MODEL = "BAAI/bge-m3"

# Chunking
THEME_CATEGORIES = ["benefits", "eligibility", "application-steps", ...]
MAX_CHUNK_SIZE = 500  # tokens
MIN_CHUNK_SIZE = 50   # tokens

# Qdrant
COLLECTION_NAME = "myschemerag"
```

## Performance

**Example**: 2,153 schemes from myscheme.gov.in

- **Chunking Time**: ~30-45 minutes (LLM-based)
- **Chunks Created**: 10,812
- **Indexing Time**: ~5 minutes
- **Average Chunks per Scheme**: 5.02

## Troubleshooting

### Ollama Not Running
```bash
# Start Ollama
ollama serve

# Verify
curl http://localhost:11434/api/tags
```

### Qdrant Connection Error
- Check QDRANT_URL and QDRANT_API_KEY in `.env`
- Verify network connectivity

### Out of Memory
- Reduce batch size in `indexing.py`
- Process schemes in smaller batches

## Next Steps

After pipeline completes:
1. Verify collection: `indexer.get_collection_info()`
2. Test retrieval: Run `src/retrieval.py`
3. Start API: `python -m uvicorn api.app:app`
