# Deployment Guide

## Local Development

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- AWS CLI (for cloud deployment)
- Terraform (for infrastructure)

### Environment Setup

1. Clone repository:
```bash
git clone https://github.com/pranaya-mathur/govt-schemes-rag.git
cd govt-schemes-rag
```

2. Create `.env` file:
```bash
GROQ_API_KEY=your_groq_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key
LOG_LEVEL=INFO
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run FastAPI server:
```bash
python -m uvicorn api.app:app --reload
```

API will be available at: http://localhost:8000

---

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t govt-schemes-rag .

# Run container
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e QDRANT_URL=your_url \
  -e QDRANT_API_KEY=your_key \
  govt-schemes-rag
```

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## AWS Deployment with Terraform

### 1. Prerequisites

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
```

### 2. Store Secrets

```bash
# Store API keys in AWS Secrets Manager
aws secretsmanager create-secret \
  --name govt-schemes-rag/groq-api-key \
  --secret-string "your_groq_key"

aws secretsmanager create-secret \
  --name govt-schemes-rag/qdrant-url \
  --secret-string "https://your-cluster.qdrant.io"

aws secretsmanager create-secret \
  --name govt-schemes-rag/qdrant-api-key \
  --secret-string "your_qdrant_key"
```

### 3. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t govt-schemes-rag .

# Tag image
docker tag govt-schemes-rag:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/govt-schemes-rag:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/govt-schemes-rag:latest
```

### 4. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply infrastructure
terraform apply
```

### 5. Get Service URL

```bash
# Get task public IP
aws ecs list-tasks --cluster govt-schemes-rag-cluster
aws ecs describe-tasks --cluster govt-schemes-rag-cluster --tasks <task-arn>
```

Access API at: `http://<public-ip>:8000`

---

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Query Schemes
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "subsidy schemes for small entrepreneurs",
    "top_k": 5
  }'
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Monitoring

### CloudWatch Logs
```bash
# View logs
aws logs tail /ecs/govt-schemes-rag --follow
```

### Container Insights
- Navigate to AWS ECS Console
- Select cluster: `govt-schemes-rag-cluster`
- View metrics and insights

---

## Scaling

### Update Task Count
```bash
aws ecs update-service \
  --cluster govt-schemes-rag-cluster \
  --service govt-schemes-rag-service \
  --desired-count 3
```

### Terraform Scaling
```hcl
# In terraform/variables.tf
variable "desired_count" {
  default = 3
}
```

```bash
terraform apply
```

---

## Troubleshooting

### Check Service Status
```bash
aws ecs describe-services \
  --cluster govt-schemes-rag-cluster \
  --services govt-schemes-rag-service
```

### View Task Logs
```bash
aws logs get-log-events \
  --log-group-name /ecs/govt-schemes-rag \
  --log-stream-name ecs/rag-api/<task-id>
```

### Common Issues

1. **Health check failing**: Increase `startPeriod` in task definition
2. **Out of memory**: Increase `task_memory` in Terraform
3. **Secrets not found**: Verify secret names match exactly

---

## Cleanup

```bash
# Destroy infrastructure
cd terraform
terraform destroy

# Delete secrets
aws secretsmanager delete-secret --secret-id govt-schemes-rag/groq-api-key
aws secretsmanager delete-secret --secret-id govt-schemes-rag/qdrant-url
aws secretsmanager delete-secret --secret-id govt-schemes-rag/qdrant-api-key
```
