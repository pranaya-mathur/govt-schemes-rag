#!/bin/bash
# Application Server Setup Script
# Runs on first boot of Application EC2 instance

set -e

echo "========================================"
echo "Application Server Setup Starting..."
echo "========================================"

# Update system
echo "[1/9] Updating system packages..."
yum update -y

# Install Docker
echo "[2/9] Installing Docker..."
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
echo "[3/9] Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Install AWS CLI v2
echo "[4/9] Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install Git
echo "[5/9] Installing Git..."
yum install -y git

# Configure swap space (2GB)
echo "[6/9] Setting up 2GB swap space..."
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Verify swap
echo "Swap configured:"
swapon --show
free -h

# Create application directory
echo "[7/9] Creating application directory..."
mkdir -p /opt/yojana-ai
cd /opt/yojana-ai

# Create .env file template
echo "[8/9] Creating environment file template..."
cat > /opt/yojana-ai/.env << 'EOF'
# Yojana-AI Environment Variables
# This file is populated by deployment scripts

# ECR Configuration
ECR_REGISTRY=<will-be-set-by-terraform>

# API Keys (from AWS Secrets Manager)
GROQ_API_KEY=<will-be-fetched-from-secrets-manager>
QDRANT_URL=<will-be-fetched-from-secrets-manager>
QDRANT_API_KEY=<will-be-fetched-from-secrets-manager>

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434

# Application Configuration
PRODUCTION_MODE=true
LOG_LEVEL=INFO
EOF

chown -R ec2-user:ec2-user /opt/yojana-ai

# Create deployment helper script
echo "[9/9] Creating deployment helper scripts..."
cat > /usr/local/bin/deploy-app << 'EOFSCRIPT'
#!/bin/bash
# Helper script to deploy application

set -e

echo "Deploying Yojana-AI application..."

cd /opt/yojana-ai

# Get ECR credentials
echo "Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws ecr describe-repositories --repository-names yojana-ai --query 'repositories[0].repositoryUri' --output text | cut -d'/' -f1)

# Pull latest images
echo "Pulling latest images..."
docker-compose pull

# Restart services
echo "Restarting services..."
docker-compose up -d

# Show status
echo ""
echo "Deployment complete! Container status:"
docker-compose ps

echo ""
echo "View logs with: docker-compose logs -f"
EOFSCRIPT

chmod +x /usr/local/bin/deploy-app

# Create helpful aliases and functions
cat >> /home/ec2-user/.bashrc << 'EOF'

# Yojana-AI aliases
alias app-logs="cd /opt/yojana-ai && docker-compose logs -f"
alias app-status="cd /opt/yojana-ai && docker-compose ps"
alias app-restart="cd /opt/yojana-ai && docker-compose restart"
alias app-stop="cd /opt/yojana-ai && docker-compose stop"
alias app-start="cd /opt/yojana-ai && docker-compose up -d"
alias app-deploy="sudo deploy-app"

# Quick health check
app-health() {
    echo "Application Health Check:"
    echo ""
    curl -s http://localhost/health | jq .
}

# Get API keys from Secrets Manager
get-secrets() {
    echo "Fetching secrets from AWS Secrets Manager..."
    aws secretsmanager get-secret-value --secret-id yojana-ai/api-keys --query SecretString --output text | jq .
}

EOF

# Install jq for JSON parsing
yum install -y jq

# Install CloudWatch agent
echo "Installing CloudWatch agent..."
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm
rm amazon-cloudwatch-agent.rpm

# Configure CloudWatch agent for Docker logs
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/lib/docker/containers/*/*.log",
            "log_group_name": "/yojana-ai/docker",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S.%fZ"
          }
        ]
      }
    }
  }
}
EOF

# Note: CloudWatch agent will be started after first deployment

echo ""
echo "========================================"
echo "Application Server Setup Complete!"
echo "========================================"
echo ""
echo "Server is ready for deployment."
echo ""
echo "Next steps:"
echo "1. Configure secrets: aws secretsmanager put-secret-value --secret-id yojana-ai/api-keys --secret-string '{...}'"
echo "2. Run deployment from Jenkins or manually with: sudo deploy-app"
echo ""
echo "Helpful commands:"
echo "  app-status  - Show container status"
echo "  app-logs    - View application logs"
echo "  app-health  - Check API health"
echo "  get-secrets - View stored secrets"
echo ""
echo "========================================"