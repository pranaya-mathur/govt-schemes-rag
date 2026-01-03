# Government Schemes RAG System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Terraform](https://img.shields.io/badge/Terraform-AWS-purple.svg)](https://www.terraform.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://langchain-ai.github.io/langgraph/)

**Production-ready multi-agent RAG system** for querying **2,153 Indian government schemes** from [myscheme.gov.in](https://www.myscheme.gov.in) with self-correcting quality loops.

---

## 🎯 Why This Project Stands Out

### **Production-Grade Infrastructure** (90% of RAG projects lack this)

Unlike typical Jupyter notebook demos, this system includes:

✅ **FastAPI** with Swagger/ReDoc documentation  
✅ **Docker** containerization for reproducible deployments  
✅ **Terraform** infrastructure-as-code for AWS ECS  
✅ **CI/CD** ready with GitHub Actions support  
✅ **CloudWatch** logging and monitoring  
✅ **Custom exceptions** and error handling  
✅ **Health checks** and graceful degradation  

**Result**: Can scale to handle 1000s of queries/day in production.

### **Cost-Optimized Hybrid LLM Strategy**

| Task | Model | Provider | Cost |
|------|-------|----------|------|
| **Intent Classification** | deepseek-r1:8b | Ollama (local) | $0 |
| **Query Refinement** | deepseek-r1:8b | Ollama (local) | $0 |
| **Answer Generation** | llama-3.3-70b | Groq (cloud) | ~$3/mo |
| **Quality Judges** | llama-3.3-70b | Groq (cloud) | ~$2/mo |

**Total Operating Cost**: < $5/month for 1000s of queries

### **Real-World Domain Value**

- **2,153 government schemes** indexed and searchable
- **10,812 intelligently chunked** documents (theme-based)
- **Solves actual problem**: Citizens struggle to find schemes they qualify for
- **Monetization potential**: Government contracts, consulting, SaaS for NGOs

---

## 🏗️ System Architecture

### Simplified RAG Workflow

```
┌─────────────────────────────────────────┐
│          User Query                      │
└────────────────┬────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │  Intent Classify    │  [Ollama: deepseek-r1:8b]
      └──────────┬──────────┘
                 │
      ┌──────────┴──────────┐
      │  Vector Retrieve    │  [BGE-M3 + Qdrant]
      └──────────┬──────────┘
                 │
      ┌──────────┴──────────┐
      │  Relevance Judge    │  [Groq: llama-3.3-70b]
      │    (YES/NO)         │
      └──────────┬──────────┘
                 │
        ┌────────┼────────┐
      NO                YES
        │                │
  ┌─────┴─────┐    ┌────┴─────┐
  │  Refine   │    │ Generate │
  │  Query    │    │  Answer  │  [Groq: llama-3.3-70b]
  └───────────┘    └────┬─────┘
   [Ollama]             │
        └───────────────┤
                        │
             ┌──────────┴──────────┐
             │  Quality Judge      │  [Groq: llama-3.3-70b]
             │    (YES/NO)         │
             └──────────┬──────────┘
                   ┌────┼────┐
                 YES         NO
        ┌─────────┴───┐     │
        │ Corrective  │     │
        │ Re-retrieve │     │  [Ollama: deepseek-r1:8b]
        └─────────────┘     │
              └─────────────┴─────────┐
              │  Final Answer         │
              └───────────────────────┘
```

### Key Features

**🧠 Intelligent Query Routing**
- Automatic classification into 6 intent categories:
  - `DISCOVERY` - Finding relevant schemes
  - `ELIGIBILITY` - Checking who can apply
  - `BENEFITS` - Understanding subsidy amounts
  - `COMPARISON` - Comparing multiple schemes
  - `PROCEDURE` - Learning application process
  - `GENERAL` - Fallback queries

**🔄 Self-Correcting RAG**
- **Self-RAG**: Binary YES/NO relevance judgment → refine query if NO
- **Corrective RAG**: Binary YES/NO answer quality check → re-retrieve if YES (inadequate)
- **Adaptive Loops**: Up to 2 refinement cycles to ensure quality

**⚡ Performance**
- **BGE-M3 Embeddings**: 1024-dimensional multilingual embeddings
- **Qdrant Vector DB**: Fast similarity search over 10,812 chunks
- **Intent-Aware Retrieval**: Adaptive top_k based on query type
- **Smart Thresholds**: Different relevance thresholds per intent

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
# Groq (for answer generation and judges)
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
# Pull model
ollama pull deepseek-r1:8b

# Start server
ollama serve
```

### 4. Process Data (First Time Only)

See **[data_pipeline/README.md](data_pipeline/README.md)** for complete guide.

```bash
# Run complete pipeline: Load → Chunk → Index
python data_pipeline/run_pipeline.py path/to/schemes.json
```

### 5. Start API

```bash
python -m uvicorn api.app:app --reload
```

API available at: **http://localhost:8000**

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

## 🧪 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|----------|
| **Orchestration** | LangGraph | Multi-agent workflow |
| **LLM Framework** | LangChain | Prompt chaining |
| **Inference** | Ollama + Groq | Hybrid local/cloud |
| **Vector DB** | Qdrant | Fast similarity search |
| **Embeddings** | BGE-M3 | Multilingual 1024-dim |
| **API** | FastAPI | Production REST API |
| **Deployment** | Docker + Terraform | Cloud infrastructure |
| **Monitoring** | CloudWatch | Logging & metrics |

---

## 💾 Project Structure

```
govt-schemes-rag/
├── api/
│   ├── app.py              # FastAPI application
│   └── models.py           # Pydantic schemas
├── src/
│   ├── embeddings.py       # BGE-M3 wrapper
│   ├── retrieval.py        # Qdrant semantic search
│   ├── llm.py              # Hybrid LLM setup
│   ├── prompts.py          # Prompt templates
│   ├── nodes.py            # LangGraph nodes
│   ├── graph.py            # Workflow definition
│   ├── exceptions.py       # Custom exceptions
│   └── logger.py           # Logging config
├── data_pipeline/          # ⭐ Data processing
│   ├── chunking.py         # LLM-powered chunking
│   ├── indexing.py         # Qdrant indexing
│   ├── run_pipeline.py     # Complete pipeline
│   └── README.md           # Pipeline docs
├── terraform/              # AWS infrastructure
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── config.py
└── README.md
```

---

## 📊 Data Pipeline

Complete pipeline for processing government schemes:

```
Raw Schemes (JSON) → LLM Chunking → BGE-M3 Embeddings → Qdrant Index
```

### LLM-Powered Chunking

- **Model**: `llama3.1:8b` via Ollama
- **Strategy**: Theme-based intelligent splitting
- **Themes**: benefits, eligibility, application-steps, documents, contact, general
- **Output**: 10,812 chunks from 2,153 schemes

See **[data_pipeline/README.md](data_pipeline/README.md)** for detailed guide.

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

## 🎯 Key Differentiators

### vs. Typical RAG Projects

| Feature | This Project | Typical RAG Notebook |
|---------|-------------|----------------------|
| **Production API** | ✅ FastAPI | ❌ Jupyter cells |
| **Deployment** | ✅ Docker + Terraform | ❌ Local only |
| **Cost Optimization** | ✅ Hybrid LLM | ❌ Single provider |
| **Quality Loops** | ✅ Self-correcting | ❌ One-shot |
| **Monitoring** | ✅ CloudWatch | ❌ Print statements |
| **Error Handling** | ✅ Custom exceptions | ❌ Basic try-catch |
| **Scale** | ✅ 1000s queries/day | ❌ <100 queries |

### Real-World Impact

- **Problem**: 2,153 government schemes exist, but citizens can't find relevant ones
- **Solution**: Intelligent RAG system with 6 intent types and quality loops
- **Outcome**: < $5/month operating cost, production-ready deployment

---

## 📝 License

MIT License

---

## 💬 Contact

Built with ❤️ for Indian citizens by [Pranay Mathur](https://github.com/pranaya-mathur)

**Portfolio Project**: Demonstrates production MLOps engineering, cloud deployment, and cost-optimized AI systems.

---

**⭐ Star this repo if you find it useful!**
