#!/bin/bash
# Warmup script - Downloads BGE-M3 model to volume on first deployment
# Run this ONCE after initial deployment

set -e

echo "=========================================="
echo "Model Warmup Script"
echo "=========================================="
echo ""
echo "This script downloads the BGE-M3 embedding model (1.06GB)"
echo "to the Docker volume for caching. Run this ONCE after"
echo "first deployment."
echo ""

# Check if API container is running
if ! docker ps | grep -q yojana-ai-api; then
    echo "❌ ERROR: yojana-ai-api container is not running"
    echo "Please start the application first:"
    echo "  docker-compose up -d"
    exit 1
fi

echo "[1/3] Checking container status..."
docker ps | grep yojana-ai-api

echo ""
echo "[2/3] Downloading BGE-M3 model (this may take 3-5 minutes)..."
echo ""

docker exec yojana-ai-api python -c "
import sys
from sentence_transformers import SentenceTransformer

print('Starting model download...')
print('Model: BAAI/bge-m3 (1.06GB)')
print('')

try:
    model = SentenceTransformer('BAAI/bge-m3')
    print('✅ Model downloaded successfully!')
    print(f'   Dimension: {model.get_sentence_embedding_dimension()}')
    print(f'   Device: {model.device}')
    print('')
    print('Testing model with sample query...')
    embedding = model.encode('test query')
    print(f'✅ Model is working! Embedding shape: {embedding.shape}')
    sys.exit(0)
except Exception as e:
    print(f'❌ ERROR: {str(e)}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "[3/3] Verifying model cache..."
    docker exec yojana-ai-api ls -lh /root/.cache/huggingface/hub/ | grep bge-m3
    
    echo ""
    echo "=========================================="
    echo "✅ Warmup Complete!"
    echo "=========================================="
    echo ""
    echo "The BGE-M3 model is now cached in the Docker volume."
    echo "It will be instantly available on subsequent deployments."
    echo ""
    echo "Next steps:"
    echo "  1. Test the API: curl http://localhost/health"
    echo "  2. Make a test query"
    echo "  3. The model is ready for production use!"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ Warmup Failed"
    echo "=========================================="
    echo ""
    echo "Check the error message above and try again."
    echo "Common issues:"
    echo "  - Internet connectivity problems"
    echo "  - Insufficient disk space"
    echo "  - Container not running properly"
    echo ""
    exit 1
fi