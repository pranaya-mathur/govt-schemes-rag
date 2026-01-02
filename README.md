# Government Schemes RAG System

Multi-agent RAG system for querying **2153 Indian government schemes** from [myscheme.gov.in](https://www.myscheme.gov.in) using adaptive retrieval strategies with self-correction.

## 🎯 Features

- **Intent-based Routing** - Automatically classifies queries into 6 categories:
  - `DISCOVERY` - Finding relevant schemes
  - `ELIGIBILITY` - Checking who can apply
  - `BENEFITS` - Understanding subsidy amounts
  - `COMPARISON` - Comparing multiple schemes
  - `PROCEDURE` - Learning application process
  - `GENERAL` - Fallback for other queries

- **Self-RAG** - Judges retrieval relevance and refines queries when docs aren't sufficient

- **Corrective RAG** - Validates answer quality and re-retrieves if answers are vague/incomplete

- **BGE-M3 Embeddings** - 1024-dim multilingual embeddings optimized for retrieval

- **Qdrant Vector DB** - Fast similarity search over 10,812 chunks

## 🏛️ Architecture

```
┌─────────────────────────────────────────┐
│          User Query                      │
└───────────────┬──────────────────────────┘
                │
                │
     ┌──────────┴──────────┐
     │  Intent Classify  │
     └──────────┬──────────┘
                │
                │
     ┌──────────┴──────────┐
     │  Vector Retrieve  │
     └──────────┬──────────┘
                │
                │
     ┌──────────┴──────────┐
     │  Relevance Judge  │
     └──────────┬──────────┘
                │
        ┌───────┼───────┐
        │       │       │
   Not Relevant   Relevant
        │       │       │
        │       │       │
┌───────┴───┐ ┌─────┴─────┐
│  Refine    │ │  Generate  │
│  Query     │ │  Answer    │
└───────────┘ └─────┬─────┘
      │               │
      └───────────────┤
                      │
           ┌──────────┴──────────┐
           │  Quality Check      │
           └──────────┬──────────┘
                      │
              ┌───────┼───────┐
              │       │       │
         Inadequate   Good
              │       │       │
      ┌───────┴───┐   │
      │ Corrective │   │
      │ Re-retrieve│   │
      └───────────┘   │
            │         │
            └─────────┴─────────┐
            │  Final Answer  │
            └──────────────────┘
```

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/pranaya-mathur/govt-schemes-rag.git
cd govt-schemes-rag
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file:

```bash
GROQ_API_KEY=your_groq_api_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key
```

### Usage

```python
from src.graph import app

response = app.invoke({
    "query": "subsidy schemes for small entrepreneurs"
})

print(response["answer"])
```

Or use CLI:

```bash
python main.py
```

## 📊 Data Pipeline

The system uses **LLM-powered intelligent chunking** that:
- Chunks schemes by semantic themes (benefits, eligibility, procedure)
- Generates metadata-rich documents
- Indexes 10,812 chunks across 2153 schemes
- Uses BGE-M3 for multilingual support

## 🧪 Tech Stack

- **LangGraph** - Agentic workflow orchestration
- **LangChain** - LLM chains and prompts
- **Groq** - Fast LLM inference (Llama 3.3 70B)
- **Qdrant** - Vector database
- **BGE-M3** - Embedding model
- **Sentence Transformers** - Embedding generation

## 📝 Example Queries

```python
# Discovery
"What are the manufacturing subsidy schemes?"

# Eligibility  
"Can women entrepreneurs apply for PMEGP?"

# Benefits
"How much subsidy does Startup India provide?"

# Comparison
"Compare MSME schemes vs Startup India benefits"

# Procedure
"How do I apply for CGTMSE loan guarantee?"
```

## 🔧 Testing

```bash
python examples/test_queries.py
```

## 📝 License

MIT

---

Built with ❤️ for Indian entrepreneurs
