# Government Schemes RAG System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Terraform](https://img.shields.io/badge/Terraform-AWS-purple.svg)](https://www.terraform.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://langchain-ai.github.io/langgraph/)

Production-ready multi-agent RAG system for querying **2,153 Indian government schemes** from [myscheme.gov.in](https://www.myscheme.gov.in) with adaptive retrieval and self-correction.

---

## 🎯 Features

### 🧠 Intelligent Routing
Automatic query classification into 6 intent categories:
- `DISCOVERY` - Finding relevant schemes
- `ELIGIBILITY` - Checking who can apply  
- `BENEFITS` - Understanding subsidy amounts
- `COMPARISON` - Comparing multiple schemes
- `PROCEDURE` - Learning application process
- `GENERAL` - Fallback queries

### 🔄 Self-Correcting RAG
- **Self-RAG**: Judges retrieval relevance, refines queries when docs aren't sufficient
- **Corrective RAG**: Validates answer quality, re-retrieves if answers are vague/incomplete
- **Adaptive Loops**: Multiple refinement cycles until quality threshold met

### ⚡ Performance
- **BGE-M3 Embeddings**: 1024-dim multilingual embeddings
- **Qdrant Vector DB**: Fast similarity search over 10,812 chunks
- **Hybrid LLM Strategy**: Ollama (local) + Groq (cloud) for optimal cost/performance
- **LangGraph Orchestration**: Efficient state machine for multi-agent workflow

### 🏛️ Production Ready
- **FastAPI** with Swagger/ReDoc docs
- **Docker** containerization
- **Terraform** for AWS ECS deployment
- **CloudWatch** logging and monitoring
- **Custom exceptions** and error handling
- **Health checks** and graceful degradation

---

## 🏗️ System Architecture

### Hybrid LLM Strategy

| Task | Model | Provider | Reason |
|------|-------|----------|--------|
| **Data Chunking** | llama3.1:8b | Ollama (local) | One-time job, cost-effective |
| **Intent Classification** | deepseek-r1:8b | Ollama (local) | Lightweight, fast |
| **Query Refinement** | deepseek-r1:8b | Ollama (local) | Adaptive, frequent |
| **Answer Generation** | llama-3.3-70b | Groq (cloud) | High quality, fast inference |
| **Relevance Judging** | llama-3.3-70b | Groq (cloud) | Critical path, accuracy |

### RAG Workflow

```
┌─────────────────────────────────────────┐
│          User Query                      │
└────────────────┬────────────────────────┘
                │
     ┌──────────┴──────────┐
     │  Intent Classify  │  [Ollama: deepseek-r1:8b]
     └──────────┬──────────┘
                │
     ┌──────────┴──────────┐
     │  Vector Retrieve  │  [BGE-M3 + Qdrant]
     └──────────┬──────────┘
                │
     ┌──────────┴──────────┐
     │  Relevance Judge  │  [Groq: llama-3.3-70b]
     └──────────┬──────────┘
                │
        ┌───────┼───────┐
   Not Relevant   Relevant
        │       │       │
┌───────┴───┐ ┌─────┴─────┐
│  Refine   │ │  Generate │
│  Query    │ │  Answer   │  [Groq: llama-3.3-70b]
└───────────┘ └─────┬─────┘
  [Ollama]          │
      └─────────────┤
                    │
         ┌──────────┴──────────┐
         │  Quality Check      │  [Groq: llama-3.3-70b]
         └──────────┬──────────┘
              ┌─────┼─────┐
         Inadequate   Good
      ┌───────┴───┐   │
      │ Corrective│   │
      │ Re-retrieve   │  [Ollama: deepseek-r1:8b]
      └───────────┘   │
            └─────────┴─────────┐
            │  Final Answer  │
            └──────────────────┘
```

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
git clone https://github.com/pranaya-mathur/govt-schemes-rag.git
cd govt-schemes-rag
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cat > .env << EOF
# Groq (for answer generation)
GROQ_API_KEY=your_groq_key

# Qdrant (vector database)
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key

# Ollama (for adaptive tasks)
OLLAMA_BASE_URL=http://localhost:11434

# Logging
LOG_LEVEL=INFO
EOF
```

### 3. Start Ollama

```bash
# Pull models
ollama pull deepseek-r1:8b
ollama pull llama3.1:8b

# Start server
ollama serve
```

### 4. Process Data (First Time Only)

See **[data_pipeline/README.md](data_pipeline/README.md)** for complete data processing guide.

```bash
# Run complete pipeline: Load -> Chunk -> Index
python data_pipeline/run_pipeline.py path/to/schemes.json
```

### 5. Start API

```bash
python -m uvicorn api.app:app --reload
```

API available at: http://localhost:8000

### 6. Docker Deployment

```bash
docker-compose up -d
```

---

## 📝 API Usage

### Query Endpoint

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "subsidy schemes for small entrepreneurs",
    "top_k": 5
  }'
```

### Example Queries

```python
import requests

queries = [
    "What are the manufacturing subsidy schemes?",      # DISCOVERY
    "Can women entrepreneurs apply for PMEGP?",         # ELIGIBILITY
    "How much subsidy does Startup India provide?",    # BENEFITS
    "Compare MSME schemes vs Startup India",           # COMPARISON
    "How do I apply for CGTMSE loan guarantee?"        # PROCEDURE
]

for query in queries:
    response = requests.post(
        "http://localhost:8000/query",
        json={"query": query}
    )
    result = response.json()
    print(f"Intent: {result['intent']}")
    print(f"Answer: {result['answer']}\n")
```

### Response Format

```json
{
  "query": "subsidy schemes for small entrepreneurs",
  "intent": "DISCOVERY",
  "answer": "Here are relevant schemes...",
  "retrieved_docs": [
    {
      "id": "123",
      "score": 0.87,
      "scheme_name": "PMEGP",
      "theme": "benefits",
      "text": "...",
      "official_url": "https://..."
    }
  ],
  "needs_reflection": false,
  "needs_correction": false
}
```

---

## 📊 Data Pipeline

Complete pipeline for processing government schemes:

```
Raw Schemes (JSON) → LLM Chunking → BGE-M3 Embeddings → Qdrant Index
```

### LLM-Powered Chunking

- **Model**: `llama3.1:8b` via ChatOllama
- **Strategy**: Theme-based intelligent splitting
- **Themes**: benefits, eligibility, application-steps, documents, contact, general
- **Output**: 10,812 chunks from 2,153 schemes

### Indexing

- **Embeddings**: BGE-M3 (1024-dim)
- **Vector DB**: Qdrant
- **Distance**: Cosine similarity

See **[data_pipeline/README.md](data_pipeline/README.md)** for detailed guide.

---

## 🧪 Tech Stack

| Component | Technology |
|-----------|------------|
| **Orchestration** | LangGraph |
| **LLM Framework** | LangChain |
| **Inference** | Groq (llama-3.3-70b) + Ollama (deepseek-r1:8b, llama3.1:8b) |
| **Vector DB** | Qdrant |
| **Embeddings** | BGE-M3 (sentence-transformers) |
| **API** | FastAPI |
| **Containerization** | Docker |
| **Infrastructure** | Terraform (AWS ECS) |
| **Monitoring** | CloudWatch |

---

## 💾 Project Structure

```
govt-schemes-rag/
├── api/
│   ├── app.py              # FastAPI application
│   └── models.py           # Pydantic schemas
├── src/
│   ├── embeddings.py       # BGE-M3 wrapper
│   ├── retrieval.py        # Qdrant client
│   ├── llm.py             # Hybrid LLM setup
│   ├── prompts.py         # Prompt templates
│   ├── nodes.py           # LangGraph nodes
│   ├── graph.py           # Workflow definition
│   ├── exceptions.py      # Custom exceptions
│   └── logger.py          # Logging config
├── data_pipeline/          # ⭐ Data processing
│   ├── chunking.py         # LLM-powered chunking
│   ├── indexing.py         # Qdrant indexing
│   ├── run_pipeline.py     # Complete pipeline
│   ├── config.py           # Pipeline config
│   └── README.md           # Pipeline docs
├── terraform/
│   ├── main.tf            # AWS infrastructure
│   ├── variables.tf       # Terraform variables
│   └── outputs.tf         # Infrastructure outputs
├── examples/
│   └── test_queries.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── config.py
├── main.py
├── DEPLOYMENT.md          # Deployment guide
└── README.md
```

---

## 🔧 Development

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### View Logs

```bash
tail -f logs/rag_system.log
```

### Run Tests

```bash
python examples/test_queries.py
```

---

## 📦 Deployment

For complete deployment instructions:
- Local development setup
- Docker deployment
- AWS ECS with Terraform
- Monitoring and scaling

See **[DEPLOYMENT.md](DEPLOYMENT.md)**

---

## 📝 Documentation

- **[README.md](README.md)** - Main documentation (this file)
- **[data_pipeline/README.md](data_pipeline/README.md)** - Data processing guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide

---

## 📝 License

MIT License

---

## 💬 Contact

Built with ❤️ for Indian entrepreneurs by [Pranay Mathur](https://github.com/pranaya-mathur)

---

**⭐ Star this repo if you find it useful!**
