# Government Schemes RAG System

Multi-agent RAG system for querying Indian government schemes using adaptive retrieval strategies.

## Features

- **Intent-based routing** - Classifies queries into categories (discovery, eligibility, benefits, etc.)
- **Self-correcting retrieval** - Judges relevance and refines queries when needed
- **Multi-stage answer validation** - Ensures answer quality through corrective loops
- **Vector search** - Uses Qdrant with BGE-M3 embeddings

## Architecture

```
User Query → Intent Classification → Retrieval → Self-RAG Judge
                                           ↓
                              ┌─ Relevant ──→ Generate Answer
                              │                      ↓
                              │              Quality Check
                              │                      ↓
                              └─ Not Relevant → Query Refinement
```

## Setup

```bash
pip install -r requirements.txt
```

Create `.env` file:
```
GROQ_API_KEY=your_key_here
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
```

## Usage

Coming soon...
