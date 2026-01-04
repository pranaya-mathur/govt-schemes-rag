#!/bin/bash
# Start Demo Environment - Automated startup for interviews/demos
# This script starts both EC2 instances and the application stack

set -e

echo "=========================================="
echo "Starting Yojana-AI Demo Environment"
echo "=========================================="
echo ""

# ============================================
# CONFIGURATION - UPDATE WITH YOUR VALUES
# ============================================
JENKINS_INSTANCE_ID="i-XXXXXXXXXXXXXXXXX"  # TODO: Replace with your Jenkins instance ID
APP_INSTANCE_ID="i-XXXXXXXXXXXXXXXXX"      # TODO: Replace with your App instance ID
REGION="us-east-1"                         # TODO: Update if using different region
SSH_KEY="~/.ssh/yojana-ai-key.pem"        # TODO: Update with your SSH key path

echo "Configuration:"
echo "  Jenkins Instance: $JENKINS_INSTANCE_ID"
echo "  App Instance:     $APP_INSTANCE_ID"
echo "  Region:           $REGION"
echo ""

# ============================================
# STEP 1: Start EC2 Instances
# ============================================
echo "[1/7] Starting EC2 instances..."
aws ec2 start-instances \
    --instance-ids $JENKINS_INSTANCE_ID $APP_INSTANCE_ID \
    --region $REGION \
    --output table

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to start instances"
    echo "Please check:"
    echo "  - AWS credentials configured (aws configure)"
    echo "  - Instance IDs are correct"
    echo "  - You have permissions to start instances"
    exit 1
fi

echo "✅ Instances starting..."
echo ""

# ============================================
# STEP 2: Wait for Instances to Boot
# ============================================
echo "[2/7] Waiting for instances to boot (2 minutes)..."
for i in {1..120}; do
    echo -n "."
    sleep 1
    if [ $((i % 20)) -eq 0 ]; then
        echo " ${i}s"
    fi
done
echo ""
echo "✅ Boot wait complete"
echo ""

# ============================================
# STEP 3: Get Instance Public IPs
# ============================================
echo "[3/7] Getting instance public IPs..."

JENKINS_IP=$(aws ec2 describe-instances \
    --instance-ids $JENKINS_INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $REGION)

APP_IP=$(aws ec2 describe-instances \
    --instance-ids $APP_INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $REGION)

if [ -z "$JENKINS_IP" ] || [ -z "$APP_IP" ]; then
    echo "❌ ERROR: Failed to get instance IPs"
    exit 1
fi

echo "✅ Instance IPs retrieved:"
echo "  Jenkins: $JENKINS_IP"
echo "  App:     $APP_IP"
echo ""

# ============================================
# STEP 4: Wait for SSH to be Available
# ============================================
echo "[4/7] Waiting for SSH to be ready..."
for i in {1..30}; do
    if ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=5 ec2-user@$APP_IP "echo 'SSH ready'" &> /dev/null; then
        echo "✅ SSH connection established"
        break
    fi
    echo -n "."
    sleep 10
done
echo ""

# ============================================
# STEP 5: Start Docker Compose Stack
# ============================================
echo "[5/7] Starting Docker Compose stack on app server..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ec2-user@$APP_IP << 'ENDSSH'
    cd /opt/yojana-ai
    
    echo "Pulling latest images..."
    docker-compose pull
    
    echo "Starting services..."
    docker-compose up -d
    
    echo "Waiting for services to start..."
    sleep 10
    
    echo "Container status:"
    docker-compose ps
ENDSSH

if [ $? -eq 0 ]; then
    echo "✅ Docker Compose stack started"
else
    echo "❌ ERROR: Failed to start Docker Compose"
    exit 1
fi
echo ""

# ============================================
# STEP 6: Warm Up Ollama Model
# ============================================
echo "[6/7] Warming up Ollama model (phi3.5:3.8b)..."
echo "This may take 2-3 minutes for first load..."
for i in {1..180}; do
    echo -n "."
    sleep 1
    if [ $((i % 30)) -eq 0 ]; then
        echo " ${i}s"
    fi
done
echo ""
echo "✅ Ollama warmup complete"
echo ""

# ============================================
# STEP 7: Health Check
# ============================================
echo "[7/7] Running health check..."
for i in {1..10}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$APP_IP/health)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Health check passed!"
        echo ""
        echo "=========================================="
        echo "✅ DEMO ENVIRONMENT IS READY!"
        echo "=========================================="
        echo ""
        echo "Access Points:"
        echo "  🚀 API:           http://$APP_IP"
        echo "  📜 API Docs:      http://$APP_IP/docs"
        echo "  ❤️  Health:        http://$APP_IP/health"
        echo "  🔧 Jenkins:       http://$JENKINS_IP:8080"
        echo ""
        echo "Quick Test:"
        echo "  curl -X POST http://$APP_IP/query \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"query\": \"What is PMEGP scheme?\"}'"
        echo ""
        echo "To Stop:"
        echo "  ./scripts/stop-demo.sh"
        echo ""
        echo "=========================================="
        exit 0
    fi
    echo "Attempt $i/10: Health check returned $HTTP_CODE, retrying..."
    sleep 10
done

echo ""
echo "❌ ERROR: Health check failed after 10 attempts"
echo ""
echo "Troubleshooting:"
echo "  1. Check container logs:"
echo "     ssh ec2-user@$APP_IP 'docker-compose logs'"
echo ""
echo "  2. Check container status:"
echo "     ssh ec2-user@$APP_IP 'docker-compose ps'"
echo ""
echo "  3. Restart services:"
echo "     ssh ec2-user@$APP_IP 'docker-compose restart'"
echo ""
exit 1