# CI/CD Setup Guide - Hybrid GitHub Actions + Jenkins Pipeline

This guide provides step-by-step instructions to set up the hybrid CI/CD pipeline for Yojana-AI deployment.

## Overview

The hybrid CI/CD architecture combines:
- **GitHub Actions** (CI) - Automated testing, Docker builds, and ECR pushes
- **Jenkins** (CD) - Deployment orchestration, SSH to EC2, health checks, and rollback

## Architecture Flow

```
Developer Push → GitHub → GitHub Actions (CI) → AWS ECR → Jenkins (CD) → EC2 Deployment
                            ↓                                    ↓
                     Tests + Build                        Deploy + Health Check
```

---

## Part 1: GitHub Actions Setup (CI Pipeline)

### Prerequisites

1. **AWS Account** with ECR repository created
2. **IAM User** with ECR permissions
3. **GitHub Repository** with admin access
4. **Jenkins Server** accessible via webhook

### Step 1: Create AWS ECR Repository

```bash
# Using AWS CLI
aws ecr create-repository \
    --repository-name yojana-ai \
    --region ap-south-1

# Note the repository URI
# Example: 123456789012.dkr.ecr.ap-south-1.amazonaws.com/yojana-ai
```

### Step 2: Create IAM User for GitHub Actions

1. **Create IAM User**: `github-actions-yojana-ai`
2. **Attach Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    }
  ]
}
```

3. **Generate Access Keys** and note them securely

### Step 3: Configure GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions → New repository secret**

Add the following secrets:

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `AWS_ACCESS_KEY_ID` | IAM user access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `GROQ_API_KEY` | Groq API key for testing | `gsk_xxxxx` |
| `QDRANT_URL` | Qdrant cloud URL | `https://xxxxx.qdrant.io` |
| `QDRANT_API_KEY` | Qdrant API key | `xxxxx` |
| `JENKINS_URL` | Jenkins server URL | `http://54.123.45.67:8080` |
| `JENKINS_USER` | Jenkins username | `admin` |
| `JENKINS_TOKEN` | Jenkins API token | `11xxxxxxxxxxxxx` |

### Step 4: Verify GitHub Actions Workflow

The workflow file is already created at `.github/workflows/ci.yml`. It will automatically trigger on:
- Push to `main` or `develop` branches
- Pull requests to `main`

**Test the workflow**:
```bash
git commit --allow-empty -m "test: trigger CI pipeline"
git push origin main
```

Check the **Actions** tab in GitHub to monitor progress.

---

## Part 2: Jenkins Setup (CD Pipeline)

### Prerequisites

1. **Jenkins Server** running (can be on EC2 t2.micro)
2. **Docker** installed on Jenkins server
3. **AWS CLI** installed on Jenkins server
4. **SSH access** to deployment server

### Step 1: Install Jenkins (if not already installed)

**On Amazon Linux 2 / Ubuntu EC2:**

```bash
# Install Java
sudo yum install java-11-openjdk -y

# Install Jenkins
sudo wget -O /etc/yum.repos.d/jenkins.repo \
    https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
sudo yum install jenkins -y

# Start Jenkins
sudo systemctl start jenkins
sudo systemctl enable jenkins

# Get initial admin password
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Access Jenkins at: `http://<jenkins-server-ip>:8080`

### Step 2: Install Required Jenkins Plugins

Go to: **Manage Jenkins → Plugin Manager → Available**

Install these plugins:
- ✅ **Pipeline** (for Jenkinsfile support)
- ✅ **Git Plugin** (for Git integration)
- ✅ **SSH Agent** (for SSH deployment)
- ✅ **AWS Steps** (optional, for AWS integration)
- ✅ **AnsiColor** (for colored console output)
- ✅ **Timestamper** (for timestamps in logs)

### Step 3: Configure Jenkins Credentials

Go to: **Manage Jenkins → Credentials → System → Global credentials**

Add the following credentials:

#### 1. ECR Registry URL
- **Kind**: Secret text
- **ID**: `ecr-registry-url`
- **Secret**: Your ECR registry URL (e.g., `123456789012.dkr.ecr.ap-south-1.amazonaws.com`)

#### 2. App Server IP
- **Kind**: Secret text
- **ID**: `app-server-ip`
- **Secret**: Your EC2 deployment server public IP

#### 3. SSH Private Key
- **Kind**: SSH Username with private key
- **ID**: `app-server-ssh-key`
- **Username**: `ec2-user`
- **Private Key**: Paste your `.pem` file content

### Step 4: Configure AWS CLI on Jenkins Server

```bash
# SSH into Jenkins server
ssh -i your-key.pem ec2-user@<jenkins-server-ip>

# Install AWS CLI
sudo yum install aws-cli -y

# Configure AWS credentials (for ECR login)
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: ap-south-1
# - Default output format: json

# Test ECR authentication
aws ecr get-login-password --region ap-south-1 | \
    docker login --username AWS --password-stdin \
    <your-ecr-registry>
```

### Step 5: Create Jenkins Pipeline Job

1. **New Item** → Enter name: `yojana-ai-deploy` → Select **Pipeline** → OK

2. **Configure the job**:

   **General Section:**
   - ✅ Check "This project is parameterized"
   - Add String Parameter:
     - Name: `IMAGE_TAG`
     - Default: `latest`
     - Description: `Docker image tag to deploy`

   **Pipeline Section:**
   - Definition: `Pipeline script from SCM`
   - SCM: `Git`
   - Repository URL: `https://github.com/pranaya-mathur/Yojana-AI.git`
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`

3. **Save**

### Step 6: Enable Remote Triggering

1. Go to job configuration: `yojana-ai-deploy`
2. **Build Triggers Section:**
   - ✅ Check "Trigger builds remotely"
   - Authentication Token: Create a secure token (e.g., `yojana-deploy-token-2024`)
3. **Save**

**Webhook URL format:**
```
http://<jenkins-url>:8080/job/yojana-ai-deploy/buildWithParameters?token=yojana-deploy-token-2024
```

Update this URL in your GitHub Actions secrets as `JENKINS_URL`.

---

## Part 3: Deployment Server Setup (EC2)

### Step 1: Prepare EC2 Instance

**Launch EC2 Instance:**
- AMI: Amazon Linux 2
- Instance Type: `t2.small` (2GB RAM required for BGE-M3)
- Storage: 30GB
- Security Group: Allow ports 22 (SSH), 8000 (API), 11434 (Ollama)

### Step 2: Install Docker & Docker Compose

```bash
# SSH into deployment server
ssh -i your-key.pem ec2-user@<app-server-ip>

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Logout and login again for group changes
exit
ssh -i your-key.pem ec2-user@<app-server-ip>
```

### Step 3: Setup Deployment Directory

```bash
# Create deployment directory
sudo mkdir -p /opt/yojana-ai
sudo chown ec2-user:ec2-user /opt/yojana-ai
cd /opt/yojana-ai

# Clone repository
git clone https://github.com/pranaya-mathur/Yojana-AI.git .

# Create .env file
cp .env.example .env
# Edit with your actual credentials
nano .env
```

### Step 4: Configure AWS CLI on Deployment Server

```bash
# Install AWS CLI
sudo yum install aws-cli -y

# Configure AWS credentials (for ECR pull)
aws configure
```

### Step 5: Create Docker Volumes

```bash
# Create volumes for persistent data
docker volume create ollama-models
docker volume create huggingface-cache

# Verify
docker volume ls
```

---

## Part 4: Testing the Complete Pipeline

### Test 1: Manual Jenkins Build

1. Go to Jenkins job: `yojana-ai-deploy`
2. Click **Build with Parameters**
3. Enter `IMAGE_TAG`: `latest`
4. Click **Build**
5. Monitor console output

### Test 2: End-to-End CI/CD Flow

```bash
# Make a code change
echo "# Test CI/CD" >> README.md
git add README.md
git commit -m "test: trigger full CI/CD pipeline"
git push origin main
```

**Expected Flow:**
1. GitHub Actions triggers (CI)
2. Tests run
3. Docker image builds
4. Image pushes to ECR
5. Jenkins webhook triggered (CD)
6. Jenkins deploys to EC2
7. Health checks pass
8. Deployment successful

### Test 3: Verify Deployment

```bash
# SSH into deployment server
ssh -i your-key.pem ec2-user@<app-server-ip>

# Check running containers
cd /opt/yojana-ai
docker-compose ps

# Check logs
docker-compose logs -f api

# Test API
curl http://localhost:8000/health
```

---

## Part 5: Monitoring & Maintenance

### View GitHub Actions Runs

```bash
# URL format
https://github.com/pranaya-mathur/Yojana-AI/actions
```

### View Jenkins Build History

```bash
# URL format
http://<jenkins-url>:8080/job/yojana-ai-deploy/
```

### Check Deployment Logs

```bash
# On deployment server
cd /opt/yojana-ai

# Application logs
docker-compose logs -f api

# Container stats
docker stats

# Disk usage
df -h
docker system df
```

### Rollback Procedure

If deployment fails, Jenkins automatically attempts rollback. For manual rollback:

```bash
# SSH into deployment server
cd /opt/yojana-ai

# List available images
docker images | grep yojana-ai

# Stop current deployment
docker-compose down

# Tag previous image as latest
docker tag yojana-ai-previous <ecr-registry>/yojana-ai:latest

# Restart with previous version
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

---

## Part 6: Troubleshooting

### Issue 1: GitHub Actions Cannot Push to ECR

**Symptoms:**
- CI build fails at "Push image to ECR" step
- Error: "denied: User not authenticated"

**Solution:**
```bash
# Verify IAM user has correct permissions
# Check GitHub secrets are correctly set
# Test ECR authentication locally:
aws ecr get-login-password --region ap-south-1 | \
    docker login --username AWS --password-stdin <ecr-registry>
```

### Issue 2: Jenkins Cannot Trigger from GitHub Actions

**Symptoms:**
- CI completes but Jenkins doesn't start
- Error: "Failed to trigger Jenkins deployment"

**Solution:**
```bash
# Verify Jenkins URL is accessible from GitHub
curl -X POST http://<jenkins-url>:8080/job/yojana-ai-deploy/build \
    --user <user>:<token>

# Check Jenkins security settings:
# Manage Jenkins → Configure Global Security
# Ensure "Allow anonymous read access" is enabled OR
# Use proper authentication token
```

### Issue 3: Deployment Health Check Fails

**Symptoms:**
- Jenkins deployment stage fails at health check
- Container starts but doesn't respond

**Solution:**
```bash
# SSH into deployment server
cd /opt/yojana-ai

# Check container logs
docker-compose logs api

# Common issues:
# 1. Missing environment variables
cat .env

# 2. Port conflicts
sudo netstat -tulpn | grep 8000

# 3. Ollama not running
docker-compose ps

# 4. Model download in progress
docker exec yojana-ai-api ls -lh /root/.cache/huggingface/hub
```

### Issue 4: Out of Memory (OOM) Errors

**Symptoms:**
- Container crashes with exit code 137
- `dmesg` shows OOM killer

**Solution:**
```bash
# Check memory usage
free -h
docker stats

# If using t2.micro (1GB), upgrade to t2.small (2GB)
# Update Terraform:
cd terraform-ec2
# Edit main.tf: instance_type = "t2.small"
terraform apply
```

---

## Part 7: Security Best Practices

### 1. Rotate Credentials Regularly

```bash
# Rotate every 90 days:
# - AWS access keys
# - Jenkins API tokens
# - SSH keys
# - API keys (Groq, Qdrant)
```

### 2. Use IAM Roles for EC2 (Recommended)

Instead of AWS credentials in `.env`, attach IAM role to EC2:

```bash
# Create IAM role with ECR pull permissions
# Attach to EC2 instance
# Remove AWS credentials from .env
```

### 3. Enable GitHub Branch Protection

- Settings → Branches → Add rule
- Branch name pattern: `main`
- ✅ Require pull request reviews
- ✅ Require status checks (CI must pass)

### 4. Restrict Jenkins Access

- Enable Jenkins authentication
- Create separate user for GitHub Actions
- Use API tokens instead of passwords

---

## Part 8: Cost Optimization

### Current Monthly Costs

| Service | Configuration | Cost |
|---------|--------------|------|
| EC2 (App Server) | t2.small, 730hrs | **$0** (free tier) |
| ECR Storage | 500MB images | **$0** (free tier) |
| Data Transfer | 15GB/month | **$0** (free tier) |
| Groq API | ~10k calls | **$0** (free tier) |
| Qdrant Cloud | 1GB cluster | **$0** (free tier) |
| **Total** | | **$0/month** |

### After Free Tier (12 months)

| Service | Cost |
|---------|------|
| EC2 t2.small (on-demand) | $16.79/month |
| ECR Storage (500MB) | $0.05/month |
| Groq API | $5-10/month |
| **Total** | **~$22/month** |

### Cost Reduction Strategies

1. **Use Spot Instances**: Save 70% on EC2 costs
2. **Schedule Stop/Start**: Stop instances when not in use
3. **Cleanup Old Images**: Regularly delete unused ECR images
4. **Optimize Docker Images**: Current optimized size: 1.2GB

---

## Part 9: Next Steps

### Phase 1: Testing (Week 1)
- [ ] Set up test environment
- [ ] Run integration tests
- [ ] Load testing
- [ ] Security scanning

### Phase 2: Monitoring (Week 2)
- [ ] Set up CloudWatch metrics
- [ ] Configure log aggregation
- [ ] Create dashboards
- [ ] Set up alerts

### Phase 3: Automation (Week 3)
- [ ] Add automated rollback tests
- [ ] Implement blue-green deployment
- [ ] Add canary deployments
- [ ] Create disaster recovery plan

### Phase 4: Documentation (Week 4)
- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Runbooks for incidents
- [ ] Video demos for portfolio

---

## Conclusion

You now have a production-grade hybrid CI/CD pipeline that:

✅ **Automates testing** with GitHub Actions  
✅ **Builds and stores** Docker images in ECR  
✅ **Deploys reliably** with Jenkins orchestration  
✅ **Monitors health** with automatic checks  
✅ **Rolls back** on failures automatically  
✅ **Costs $0/month** within free tier limits  

This architecture demonstrates enterprise-level DevOps practices suitable for senior technical architect portfolios and production deployments.

---

## Support

For issues or questions:
- **GitHub Issues**: [Yojana-AI Issues](https://github.com/pranaya-mathur/Yojana-AI/issues)
- **Documentation**: Check `docs/` directory
- **48-Hour Plan**: See `docs/DEPLOYMENT_PLAN_48HR.md`
