# Yojana-AI: Multi-Agent RAG System for Government Schemes

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Terraform](https://img.shields.io/badge/Terraform-AWS-purple.svg)](https://www.terraform.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://langchain-ai.github.io/langgraph/)

Production-grade retrieval-augmented generation system implementing self-correcting RAG patterns for querying 2,153 Indian government schemes from myscheme.gov.in.

---

## System Overview

### Architecture

Implements a multi-agent architecture using LangGraph for orchestration, combining Self-RAG and Corrective RAG patterns with intent-aware routing. The system processes queries through a directed graph of specialized agents, each handling specific aspects of query understanding, retrieval, and generation.

```
Query → Intent Classification → Vector Retrieval → Relevance Judgment → Generation
           ↓                                              ↓
    Route Selection                              Self-RAG Loop (if needed)
                                                           ↓
                                                  Corrective RAG (if needed)
```

### Core Components

**Query Understanding**
- Intent classification into 6 categories (DISCOVERY, ELIGIBILITY, BENEFITS, COMPARISON, PROCEDURE, GENERAL)
- Query decomposition for scheme name extraction
- Intent-specific retrieval parameter selection

**Retrieval Pipeline**
- BGE-M3 embeddings (1024-dim multilingual)
- Qdrant vector database for similarity search
- Metadata-aware filtering for scheme-specific queries
- Adaptive threshold mechanisms per intent type

**Quality Assurance**
- Binary relevance judgment for retrieved documents
- Answer adequacy evaluation
- Automated query refinement loops (max 2 iterations)
- Corrective re-retrieval based on answer quality

**Infrastructure**
- FastAPI REST API with OpenAPI documentation
- Docker containerization with multi-stage builds
- Terraform IaC for AWS ECS deployment
- CloudWatch integration for observability

---

## Technical Implementation

### Hybrid LLM Strategy

Cost-optimized approach using local and cloud inference:

| Component | Model | Deployment | Rationale |
|-----------|-------|------------|----------|
| Intent Classification | deepseek-r1:8b | Ollama (local) | Low latency, zero cost, deterministic |
| Query Refinement | deepseek-r1:8b | Ollama (local) | Frequent operation, cost-sensitive |
| Answer Generation | llama-3.3-70b | Groq (cloud) | Quality-critical, acceptable latency |
| Relevance/Quality Judges | llama-3.3-70b | Groq (cloud) | Requires reasoning capability |

**Cost Analysis**: ~$5/month for 1000s of queries at current Groq pricing.

### Data Processing

**Intelligent Chunking**
- LLM-based theme classification (benefits, eligibility, application-steps, documents, contact, general)
- Context-preserving splitting maintaining semantic coherence
- Metadata enrichment with scheme identifiers and theme tags
- Output: 10,812 chunks from 2,153 source schemes

**Indexing Pipeline**
- Batch embedding generation with BGE-M3
- Qdrant collection with metadata indexing
- Support for filtered queries on scheme_name and theme fields

### Self-Correcting Mechanisms

**Self-RAG Implementation**
```python
if relevance_judge(query, retrieved_docs) == "NO":
    refined_query = query_refiner(original_query)
    retrieved_docs = retriever(refined_query)
```

**Corrective RAG Implementation**
```python
if quality_judge(answer, query) == "INADEQUATE":
    corrective_query = generate_corrective_query(answer, query)
    additional_docs = retriever(corrective_query)
    answer = regenerate(query, all_docs)
```

---

## Project Structure

```
yojana-ai/
├── api/                      # REST API layer
│   ├── app.py               # FastAPI application
│   └── models.py            # Request/response schemas
├── src/                      # Core system
│   ├── embeddings.py        # Embedding model wrapper
│   ├── retrieval.py         # Vector retrieval logic
│   ├── metadata_retrieval.py # Filtered retrieval
│   ├── query_decomposer.py  # Query understanding
│   ├── llm.py               # LLM client management
│   ├── prompts.py           # Prompt engineering
│   ├── nodes.py             # LangGraph node definitions
│   ├── graph.py             # Workflow orchestration
│   ├── schemas.py           # Pydantic models
│   ├── exceptions.py        # Custom exception hierarchy
│   └── logger.py            # Structured logging
├── data_pipeline/           # Data ingestion
│   ├── chunking.py          # Document processing
│   ├── indexing.py          # Vector DB operations
│   └── run_pipeline.py      # Pipeline orchestrator
├── terraform/               # Infrastructure as Code
│   ├── main.tf              # ECS, VPC, ALB resources
│   ├── variables.tf         # Configuration parameters
│   └── outputs.tf           # Exported values
├── docs/                    # Documentation
│   ├── DEPLOYMENT.md        # Deployment procedures
│   ├── QUICKSTART.md        # Getting started guide
│   ├── TESTING_GUIDE.md     # Testing procedures
│   └── METADATA_FILTERING.md # Feature documentation
├── examples/                # Usage examples
├── Dockerfile               # Container image definition
├── docker-compose.yml       # Local deployment
└── requirements.txt         # Python dependencies
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Ollama (for local inference)
- Groq API key
- Qdrant Cloud instance

### Local Development

```bash
# Clone repository
git clone https://github.com/pranaya-mathur/Yojana-AI.git
cd Yojana-AI

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and endpoints

# Start Ollama
ollama pull deepseek-r1:8b
ollama serve

# Run data pipeline (first time only)
python data_pipeline/run_pipeline.py path/to/schemes.json

# Start API server
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### API Access

- **Base URL**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Reference

### Query Endpoint

**POST** `/query`

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "subsidy schemes for small entrepreneurs",
    "top_k": 5
  }'
```

**Response Schema**
```json
{
  "query": "string",
  "intent": "DISCOVERY|ELIGIBILITY|BENEFITS|COMPARISON|PROCEDURE|GENERAL",
  "answer": "string",
  "retrieved_docs": [
    {
      "id": "string",
      "score": 0.87,
      "scheme_name": "string",
      "theme": "string",
      "text": "string",
      "official_url": "string"
    }
  ],
  "needs_reflection": false,
  "needs_correction": false,
  "metadata": {
    "retrieval_method": "metadata_filtered|hybrid|semantic",
    "reflection_count": 0,
    "correction_count": 0
  }
}
```

### Health Check

**GET** `/health`

```bash
curl http://localhost:8000/health
```

---

## Technology Stack

### Core Dependencies

| Component | Version | Purpose |
|-----------|---------|----------|
| FastAPI | 0.115+ | Async REST API framework |
| LangChain | 0.2+ | LLM orchestration |
| LangGraph | 0.2+ | Agent workflow management |
| Qdrant Client | 1.7+ | Vector database operations |
| Sentence Transformers | 2.5+ | Embedding generation |
| Pydantic | 2.0+ | Data validation |
| Uvicorn | 0.27+ | ASGI server |

### Infrastructure

- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose for local, ECS for production
- **IaC**: Terraform for AWS resource provisioning
- **Monitoring**: CloudWatch Logs and Metrics
- **CI/CD**: GitHub Actions ready

---

## Deployment

### AWS ECS Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete instructions.

**Architecture**
- ECS Fargate for serverless container execution
- Application Load Balancer for traffic distribution
- AWS Secrets Manager for credential management
- CloudWatch for centralized logging
- Auto-scaling based on CPU/memory metrics

**Infrastructure Provisioning**
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Configuration Management

Environment variables:
```bash
GROQ_API_KEY=<groq_api_key>
QDRANT_URL=<qdrant_cluster_url>
QDRANT_API_KEY=<qdrant_api_key>
COLLECTION_NAME=govt_schemes
OLLAMA_BASE_URL=http://localhost:11434
GROQ_MODEL=llama-3.3-70b-versatile
OLLAMA_MODEL=deepseek-r1:8b
EMBEDDING_MODEL=BAAI/bge-m3
LOG_LEVEL=INFO
```

---

## Performance Characteristics

### Latency Profile

| Query Type | Avg Latency | Components |
|------------|-------------|------------|
| Simple (no loops) | 1.8-2.5s | Classification → Retrieval → Generation |
| Self-RAG (1 loop) | 3.8-4.5s | + Query refinement + Re-retrieval |
| Corrective RAG | 4.3-5.5s | + Quality check + Corrective retrieval |

### Scalability

- **Vertical**: Single instance handles ~50 concurrent requests
- **Horizontal**: Stateless design enables unlimited horizontal scaling
- **Bottlenecks**: Groq API rate limits (30 req/min on free tier)

### Cost Analysis

- **Compute**: AWS ECS Fargate ~$20-30/month (256 CPU, 512 MB)
- **LLM Inference**: Groq ~$5/month for 1000s of queries
- **Vector DB**: Qdrant Cloud free tier (1GB)
- **Total**: ~$25-35/month for production workload

---

## Development

### Testing

```bash
# System integration test
python test_system.py

# All schemes test
python test_all_schemes.py

# Custom queries
python examples/test_queries.py
```

### Logging

Structured logging to `logs/rag_system.log`:
```bash
# Tail logs
tail -f logs/rag_system.log

# Filter by level
grep ERROR logs/rag_system.log

# Search queries
grep "query=" logs/rag_system.log
```

### Monitoring

- Request latency per endpoint
- Retrieval quality metrics (relevance scores)
- Self-RAG/Corrective RAG trigger rates
- LLM token consumption
- Error rates and exception types

---

## Design Decisions

### Why Hybrid LLM?

Local inference (Ollama) for high-frequency, low-complexity tasks reduces costs by 80% compared to full cloud deployment while maintaining quality where it matters.

### Why LangGraph?

Enables explicit workflow definition with conditional routing, making the multi-agent system debuggable and maintainable compared to implicit agent frameworks.

### Why BGE-M3?

Multilingual capability handles mixed English/Hindi queries common in Indian government documents. 1024-dim embeddings provide better semantic understanding than smaller models.

### Why Qdrant?

Native metadata filtering support enables efficient scheme-specific queries. Cloud offering provides managed infrastructure with acceptable free tier.

---

## Roadmap

### Completed
- [x] Core RAG pipeline with Self-RAG and Corrective RAG
- [x] Intent-aware routing and retrieval
- [x] Metadata-filtered queries
- [x] Docker containerization
- [x] Terraform infrastructure
- [x] Production API with FastAPI

### In Progress
- [ ] A/B testing framework for prompt optimization
- [ ] Redis caching layer for frequent queries
- [ ] MLflow integration for experiment tracking
- [ ] Prometheus/Grafana monitoring stack

### Planned
- [ ] Streaming responses with SSE
- [ ] Multi-tenant architecture
- [ ] Fine-tuned reranker model
- [ ] GraphQL API alternative
- [ ] Comprehensive test suite (unit, integration, e2e)

---

## Documentation

- [Quickstart Guide](docs/QUICKSTART.md) - 5-minute setup
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- [Testing Guide](docs/TESTING_GUIDE.md) - Testing procedures
- [Metadata Filtering](docs/METADATA_FILTERING.md) - Advanced retrieval

---

## Contributing

This is a portfolio project demonstrating production ML engineering practices. Feel free to fork and adapt for your use cases.

---

## License

MIT License - see LICENSE file for details

---

## Author

**Pranay Mathur**
- GitHub: [@pranaya-mathur](https://github.com/pranaya-mathur)
- Portfolio Project: Production MLOps Engineering

---

*This system demonstrates architectural patterns for production RAG systems including cost optimization, quality assurance loops, and scalable infrastructure design.*