# Government Schemes RAG System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Terraform](https://img.shields.io/badge/Terraform-AWS-purple.svg)](https://www.terraform.io/)

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
- **LangGraph Orchestration**: Efficient state machine for multi-agent workflow
- **Groq Inference**: Sub-second LLM responses with Llama 3.3 70B

### 🏛️ Production Ready
- **FastAPI** with Swagger/ReDoc docs
- **Docker** containerization
- **Terraform** for AWS ECS deployment
- **CloudWatch** logging and monitoring
- **Custom exceptions** and error handling
- **Health checks** and graceful degradation

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────┐
│          User Query                      │
└────────────────┬────────────────────────┘
                │
     ┌──────────┴──────────┐
     │  Intent Classify  │
     └──────────┬──────────┘
                │
     ┌──────────┴──────────┐
     │  Vector Retrieve  │
     └──────────┬──────────┘
                │
     ┌──────────┴──────────┐
     │  Relevance Judge  │
     └──────────┬──────────┘
                │
        ┌───────┼───────┐
   Not Relevant   Relevant
        │       │       │
┌───────┴───┐ ┌─────┴─────┐
│  Refine   │ │  Generate │
│  Query    │ │  Answer   │
└───────────┘ └─────┬─────┘
      │             │
      └─────────────┤
                    │
         ┌──────────┴──────────┐
         │  Quality Check      │
         └──────────┬──────────┘
              ┌─────┼─────┐
         Inadequate   Good
      ┌───────┴───┐   │
      │ Corrective│   │
      │ Re-retrieve   │
      └───────────┘   │
            └─────────┴─────────┐
            │  Final Answer  │
            └──────────────────┘
```

---

## 🚀 Quick Start

### Local Development

```bash
git clone https://github.com/pranaya-mathur/govt-schemes-rag.git
cd govt-schemes-rag
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
GROQ_API_KEY=your_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key
EOF

# Run FastAPI
python -m uvicorn api.app:app --reload
```

### Docker

```bash
docker-compose up -d
```

### AWS Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete Terraform deployment guide.

---

## 📝 API Usage

### Query Endpoint

```python
import requests

response = requests.post(
    "http://localhost:8000/query",
    json={
        "query": "subsidy schemes for small entrepreneurs",
        "top_k": 5
    }
)

result = response.json()
print(result["answer"])
```

### Example Queries

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

The system uses **LLM-powered intelligent chunking**:

1. **Theme-based Chunking**: Splits schemes by semantic themes (benefits, eligibility, procedure, etc.)
2. **Metadata Enrichment**: Adds scheme name, official URL, ministry info
3. **BGE-M3 Embeddings**: Multilingual 1024-dim vectors
4. **Qdrant Indexing**: 10,812 chunks across 2,153 schemes

---

## 🧪 Tech Stack

| Component | Technology |
|-----------|------------|
| **Orchestration** | LangGraph |
| **LLM Framework** | LangChain |
| **Inference** | Groq (Llama 3.3 70B) |
| **Vector DB** | Qdrant |
| **Embeddings** | BGE-M3 |
| **API** | FastAPI |
| **Containerization** | Docker |
| **Infrastructure** | Terraform (AWS ECS) |
| **Monitoring** | CloudWatch |

---

## 💾 Project Structure

```
govt-schemes-rag/
├── api/
│   ├── app.py          # FastAPI application
│   └── models.py       # Pydantic schemas
├── src/
│   ├── embeddings.py   # BGE-M3 wrapper
│   ├── retrieval.py    # Qdrant client
│   ├── llm.py         # Groq setup
│   ├── prompts.py     # Prompt templates
│   ├── nodes.py       # LangGraph nodes
│   ├── graph.py       # Workflow definition
│   ├── exceptions.py  # Custom exceptions
│   └── logger.py      # Logging config
├── terraform/
│   ├── main.tf        # AWS infrastructure
│   ├── variables.tf   # Terraform variables
│   └── outputs.tf     # Infrastructure outputs
├── examples/
│   └── test_queries.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── config.py
├── main.py
├── DEPLOYMENT.md
└── README.md
```

---

## 🔧 Development

### Run Tests

```bash
python examples/test_queries.py
```

### View Logs

```bash
tail -f logs/rag_system.log
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📦 Deployment

For complete deployment instructions including:
- Local development setup
- Docker deployment
- AWS ECS with Terraform
- Monitoring and scaling
- Troubleshooting

See **[DEPLOYMENT.md](DEPLOYMENT.md)**

---

## 📝 License

MIT License - See [LICENSE](LICENSE)

---

## 💬 Contact

Built with ❤️ for Indian entrepreneurs by [Pranay Mathur](https://github.com/pranaya-mathur)

---

**Star ⭐ this repo if you find it useful!**
