# Yojana-AI: EC2-based Terraform Deployment

Complete Infrastructure-as-Code setup for deploying Yojana-AI on AWS EC2 instances with cost optimization for free tier.

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Free Tier                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  Jenkins Server  │         │  App Server      │        │
│  │  (t2.micro)      │────────▶│  (t2.small)      │        │
│  │  1GB RAM         │  SSH    │  2GB RAM         │        │
│  │  Port: 8080      │         │  Port: 80        │        │
│  └──────────────────┘         └──────────────────┘        │
│         │                              │                   │
│         │                              │                   │
│         ▼                              ▼                   │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  ECR Repository  │         │ Secrets Manager  │        │
│  │  (Docker Images) │         │  (API Keys)      │        │
│  └──────────────────┘         └──────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

App Server runs:
  - Nginx (reverse proxy)
  - FastAPI (Yojana-AI API)
  - Ollama (phi3.5:3.8b for intent classification)
```

## 💰 Cost Breakdown

| Resource | Specification | Monthly Cost | Notes |
|----------|--------------|--------------|-------|
| Jenkins EC2 | t2.micro, 20hrs/month | **$0.00** | Free tier (750hrs/month) |
| App EC2 | t2.small, 25hrs/month | **$0.00** | Free tier (750hrs/month) |
| EBS (Jenkins) | 20GB gp3 | **$0.60** | $0.03/GB/month |
| EBS (App) | 42GB gp3 | **$1.26** | $0.03/GB/month |
| ECR Storage | 1.7GB | **$0.17** | $0.10/GB/month (500MB free) |
| Secrets Manager | 1 secret | **$0.40** | $0.40/secret/month |
| CloudWatch Logs | 1GB | **$0.00** | 5GB free tier |
| Data Transfer | <1GB/month | **$0.00** | 100GB free tier |
| **TOTAL** | | **$2.43/month** | **On-demand usage only** |

### Cost Optimization Features

- ✅ **On-demand usage**: Instances run only when needed
- ✅ **Automated stop/start**: Scripts minimize running hours
- ✅ **Free tier maximized**: Both instances within 750hrs/month
- ✅ **No ALB/NAT Gateway**: Direct instance access (saves $18-36/month)
- ✅ **Minimal monitoring**: CloudWatch basics only

## 📋 Prerequisites

### 1. AWS CLI Configured

```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure with your credentials
aws configure
# AWS Access Key ID: YOUR_KEY
# AWS Secret Access Key: YOUR_SECRET
# Default region: us-east-1
# Default output format: json
```

### 2. Create SSH Key Pair

```bash
# Create EC2 key pair
aws ec2 create-key-pair \
  --key-name yojana-ai-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/yojana-ai-key.pem

# Set proper permissions
chmod 400 ~/.ssh/yojana-ai-key.pem
```

### 3. Install Terraform

```bash
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify
terraform version
```

## 🚀 Deployment Steps

### Step 1: Create `terraform.tfvars`

```bash
cd terraform-ec2

# Create your variables file
cat > terraform.tfvars << EOF
key_name     = "yojana-ai-key"
allowed_ips  = ["YOUR_PUBLIC_IP/32"]  # Get from: curl ifconfig.me
aws_region   = "us-east-1"
project_name = "yojana-ai"
EOF
```

### Step 2: Initialize Terraform

```bash
# Initialize providers and modules
terraform init

# Validate configuration
terraform validate

# Preview changes
terraform plan
```

### Step 3: Deploy Infrastructure

```bash
# Apply configuration
terraform apply

# Type 'yes' when prompted
# Deployment takes ~5-7 minutes
```

### Step 4: Get Output Values

```bash
# View all outputs
terraform output

# Specific outputs
terraform output jenkins_url
terraform output app_url
terraform output ssh_jenkins
```

**Example output:**
```
jenkins_url = "http://54.123.45.67:8080"
app_url = "http://52.98.76.54"
ecr_repository_url = "123456789.dkr.ecr.us-east-1.amazonaws.com/yojana-ai"
```

### Step 5: Configure Secrets

```bash
# Store API keys in Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id yojana-ai/api-keys \
  --secret-string '{
    "GROQ_API_KEY": "gsk_your_groq_key_here",
    "QDRANT_URL": "https://your-cluster.qdrant.io",
    "QDRANT_API_KEY": "your_qdrant_api_key_here"
  }'
```

### Step 6: Access Jenkins

```bash
# SSH to Jenkins server
ssh -i ~/.ssh/yojana-ai-key.pem ec2-user@<JENKINS_IP>

# Get initial admin password
sudo cat /var/jenkins_home/secrets/initialAdminPassword
# Or from file:
cat ~/jenkins-initial-password.txt
```

**Jenkins Setup:**
1. Open `http://<JENKINS_IP>:8080`
2. Enter initial admin password
3. Install suggested plugins
4. Create admin user
5. Configure GitHub webhook

## 🔧 Post-Deployment Configuration

### 1. Update Start/Stop Scripts

Edit `scripts/start-demo.sh` and `scripts/stop-demo.sh` with your instance IDs:

```bash
# Get instance IDs from Terraform
terraform output jenkins_instance_id  # Copy this
terraform output app_instance_id      # Copy this

# Update scripts
vim ../scripts/start-demo.sh
# Replace:
# JENKINS_INSTANCE_ID="i-XXXXXXXXXXXXXXXXX"
# APP_INSTANCE_ID="i-XXXXXXXXXXXXXXXXX"
```

### 2. Test Application Deployment

```bash
# SSH to app server
ssh -i ~/.ssh/yojana-ai-key.pem ec2-user@<APP_IP>

# Deploy application
sudo deploy-app

# Check status
app-status
app-health
```

### 3. Run Warmup Script

```bash
# From app server
cd /opt/yojana-ai
sudo ../scripts/warmup-models.sh
```

## 📊 Resource Management

### Start Instances (For Demo/Interview)

```bash
./scripts/start-demo.sh
# Takes ~20 minutes for full startup
```

### Stop Instances (Save Costs)

```bash
./scripts/stop-demo.sh
# Confirms before stopping
```

### Manual Control

```bash
# Start specific instance
aws ec2 start-instances --instance-ids <INSTANCE_ID>

# Stop specific instance
aws ec2 stop-instances --instance-ids <INSTANCE_ID>

# Check status
aws ec2 describe-instances \
  --instance-ids <INSTANCE_ID> \
  --query 'Reservations[0].Instances[0].State.Name'
```

## 🛠️ Maintenance

### Update Infrastructure

```bash
# Make changes to .tf files
vim main.tf

# Review changes
terraform plan

# Apply updates
terraform apply
```

### View Logs

```bash
# CloudWatch logs
aws logs tail /aws/ec2/yojana-ai/app --follow

# Or on server
ssh ec2-user@<APP_IP>
app-logs
```

### Backup State

```bash
# State is stored locally by default
# Backup before major changes
cp terraform.tfstate terraform.tfstate.backup

# Recommended: Use S3 backend (uncomment in main.tf)
```

## 🗑️ Cleanup / Destroy

```bash
# WARNING: This deletes ALL resources
terraform destroy

# Type 'yes' to confirm

# Manually delete:
# - ECR images (if any)
# - CloudWatch logs (optional)
# - Secrets (if desired)
```

## 🔐 Security Best Practices

### 1. Restrict IP Access

```hcl
# In terraform.tfvars
allowed_ips = ["YOUR_IP/32"]  # Not 0.0.0.0/0
```

### 2. Rotate Secrets Regularly

```bash
# Update secrets every 90 days
aws secretsmanager update-secret \
  --secret-id yojana-ai/api-keys \
  --secret-string '{...new keys...}'
```

### 3. Enable MFA on AWS Account

### 4. Use IAM Roles (Already configured)

Instances use IAM roles instead of hardcoded credentials ✅

## 📈 Monitoring

### CloudWatch Metrics

- CPU utilization
- Memory usage (with CloudWatch agent)
- Network traffic
- Disk usage

### Set Up Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name yojana-ai-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

## 🐛 Troubleshooting

### Issue: Can't SSH to instances

```bash
# Check security group rules
aws ec2 describe-security-groups \
  --group-ids <SG_ID> \
  --query 'SecurityGroups[0].IpPermissions'

# Verify key permissions
chmod 400 ~/.ssh/yojana-ai-key.pem

# Check instance is running
aws ec2 describe-instances --instance-ids <INSTANCE_ID>
```

### Issue: Application won't start

```bash
# Check Docker status
ssh ec2-user@<APP_IP>
sudo systemctl status docker

# Check compose status
cd /opt/yojana-ai
docker-compose ps

# View logs
docker-compose logs
```

### Issue: Out of memory

```bash
# Check memory and swap
free -h
swapon --show

# Verify instance type
aws ec2 describe-instances \
  --instance-ids <INSTANCE_ID> \
  --query 'Reservations[0].Instances[0].InstanceType'

# Should be t2.small for app server
```

## 📚 Additional Resources

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Jenkins Documentation](https://www.jenkins.io/doc/)

## 🤝 Support

For issues or questions:
1. Check CloudWatch logs
2. Review instance user-data logs: `/var/log/cloud-init-output.log`
3. Verify security groups and IAM roles

---

**Last Updated**: January 4, 2026  
**Terraform Version**: >= 1.0  
**AWS Provider Version**: ~> 5.0