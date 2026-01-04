#!/bin/bash
# Jenkins Server Setup Script
# Runs on first boot of Jenkins EC2 instance

set -e

echo "========================================"
echo "Jenkins Server Setup Starting..."
echo "========================================"

# Update system
echo "[1/8] Updating system packages..."
yum update -y

# Install Docker
echo "[2/8] Installing Docker..."
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
echo "[3/8] Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Install Git
echo "[4/8] Installing Git..."
yum install -y git

# Install AWS CLI v2
echo "[5/8] Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install Jenkins using Docker
echo "[6/8] Setting up Jenkins container..."
mkdir -p /var/jenkins_home
chown -R 1000:1000 /var/jenkins_home

# Create Jenkins docker-compose file
cat > /opt/jenkins-compose.yml << 'EOF'
version: '3.8'

services:
  jenkins:
    image: jenkins/jenkins:lts
    container_name: jenkins
    privileged: true
    user: root
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - /var/jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/local/bin/docker:/usr/local/bin/docker
      - /usr/bin/docker-compose:/usr/bin/docker-compose
    environment:
      - JENKINS_OPTS=--prefix=/jenkins
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# Start Jenkins
echo "[7/8] Starting Jenkins..."
cd /opt
docker-compose -f jenkins-compose.yml up -d

# Wait for Jenkins to start and get initial admin password
echo "[8/8] Waiting for Jenkins to initialize (60 seconds)..."
sleep 60

if [ -f /var/jenkins_home/secrets/initialAdminPassword ]; then
    JENKINS_PASSWORD=$(cat /var/jenkins_home/secrets/initialAdminPassword)
    echo ""
    echo "========================================"
    echo "Jenkins Setup Complete!"
    echo "========================================"
    echo ""
    echo "Jenkins URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
    echo ""
    echo "Initial Admin Password:"
    echo "$JENKINS_PASSWORD"
    echo ""
    echo "Save this password - you'll need it for first login!"
    echo "========================================"
    
    # Save password to a file
    echo "$JENKINS_PASSWORD" > /home/ec2-user/jenkins-initial-password.txt
    chown ec2-user:ec2-user /home/ec2-user/jenkins-initial-password.txt
else
    echo "Warning: Jenkins password file not found yet. Check later with:"
    echo "sudo cat /var/jenkins_home/secrets/initialAdminPassword"
fi

# Install CloudWatch agent for log forwarding (optional)
echo "Installing CloudWatch agent..."
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm
rm amazon-cloudwatch-agent.rpm

# Create helpful aliases
echo "Creating helpful aliases..."
cat >> /home/ec2-user/.bashrc << 'EOF'

# Jenkins aliases
alias jenkins-logs="docker logs -f jenkins"
alias jenkins-restart="docker restart jenkins"
alias jenkins-stop="docker stop jenkins"
alias jenkins-start="docker start jenkins"
alias jenkins-password="sudo cat /var/jenkins_home/secrets/initialAdminPassword"

EOF

echo "========================================"
echo "Setup script complete!"
echo "========================================"