# Yojana-AI: EC2-based Terraform Configuration
# Cost-optimized deployment using AWS Free Tier with on-demand instances

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # S3 backend for state management (recommended for production)
  # Uncomment and configure after creating S3 bucket
  # backend "s3" {
  #   bucket = "yojana-ai-terraform-state"
  #   key    = "prod/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

# ============================================
# DATA SOURCES
# ============================================

# Latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================
# NETWORKING
# ============================================

# Use default VPC (free tier friendly)
resource "aws_default_vpc" "default" {
  tags = {
    Name = "Default VPC"
  }
}

# Security Group for Jenkins Server
resource "aws_security_group" "jenkins" {
  name        = "${var.project_name}-jenkins-sg"
  description = "Security group for Jenkins CI/CD server"
  vpc_id      = aws_default_vpc.default.id

  # Jenkins UI
  ingress {
    description = "Jenkins UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = var.allowed_ips  # Restrict to your IP
  }

  # SSH from your IP only
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ips
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-jenkins-sg"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

# Security Group for Application Server
resource "aws_security_group" "app" {
  name        = "${var.project_name}-app-sg"
  description = "Security group for application server"
  vpc_id      = aws_default_vpc.default.id

  # HTTP from anywhere
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS from anywhere (for future SSL)
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH from Jenkins server only
  ingress {
    description     = "SSH from Jenkins"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.jenkins.id]
  }

  # SSH from your IP (for debugging)
  ingress {
    description = "SSH from admin"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ips
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-app-sg"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

# ============================================
# IAM ROLES & POLICIES
# ============================================

# IAM Role for Jenkins EC2 Instance
resource "aws_iam_role" "jenkins" {
  name = "${var.project_name}-jenkins-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name      = "${var.project_name}-jenkins-role"
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# Policy for Jenkins to access ECR and trigger deployments
resource "aws_iam_role_policy" "jenkins_policy" {
  name = "${var.project_name}-jenkins-policy"
  role = aws_iam_role.jenkins.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories",
          "ecr:ListImages"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "jenkins" {
  name = "${var.project_name}-jenkins-profile"
  role = aws_iam_role.jenkins.name

  tags = {
    Name      = "${var.project_name}-jenkins-profile"
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# IAM Role for Application EC2 Instance
resource "aws_iam_role" "app" {
  name = "${var.project_name}-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name      = "${var.project_name}-app-role"
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# Policy for App server to pull from ECR and write logs
resource "aws_iam_role_policy" "app_policy" {
  name = "${var.project_name}-app-policy"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.api_keys.arn
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "${var.project_name}-app-profile"
  role = aws_iam_role.app.name

  tags = {
    Name      = "${var.project_name}-app-profile"
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# ============================================
# EC2 INSTANCES
# ============================================

# Jenkins Server (t2.micro - sufficient for CI/CD)
resource "aws_instance" "jenkins" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.jenkins_instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.jenkins.id]
  iam_instance_profile   = aws_iam_instance_profile.jenkins.name

  root_block_device {
    volume_size = 20  # 20GB for Jenkins
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = file("${path.module}/user-data/jenkins-setup.sh")

  tags = {
    Name        = "${var.project_name}-jenkins"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
    Role        = "CI/CD"
  }
}

# Application Server (t2.small - for 2GB RAM)
resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.app_instance_type  # t2.small for 2GB RAM
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  root_block_device {
    volume_size = var.app_ebs_size  # 42GB for app + models
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = file("${path.module}/user-data/app-setup.sh")

  tags = {
    Name        = "${var.project_name}-app"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
    Role        = "Application"
  }
}

# ============================================
# ECR REPOSITORY
# ============================================

resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  # Lifecycle policy to keep only last 5 images
  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Name        = var.project_name
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ============================================
# SECRETS MANAGER
# ============================================

resource "aws_secretsmanager_secret" "api_keys" {
  name        = "${var.project_name}/api-keys"
  description = "API keys for Groq, Qdrant, etc."

  tags = {
    Name        = "${var.project_name}-api-keys"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

# Secret values must be set manually or via terraform.tfvars
# aws secretsmanager put-secret-value --secret-id yojana-ai/api-keys --secret-string '{"GROQ_API_KEY":"...","QDRANT_API_KEY":"...","QDRANT_URL":"..."}'

# ============================================
# CLOUDWATCH LOG GROUPS
# ============================================

resource "aws_cloudwatch_log_group" "jenkins" {
  name              = "/aws/ec2/${var.project_name}/jenkins"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-jenkins-logs"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/ec2/${var.project_name}/app"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-app-logs"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/${var.project_name}/api"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-api-logs"
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = var.environment
  }
}

# ============================================
# ELASTIC IPS (Optional but recommended)
# ============================================

# Uncomment if you want static IPs that persist across stop/start
# resource "aws_eip" "jenkins" {
#   instance = aws_instance.jenkins.id
#   domain   = "vpc"
# 
#   tags = {
#     Name      = "${var.project_name}-jenkins-eip"
#     Project   = var.project_name
#     ManagedBy = "terraform"
#   }
# }
# 
# resource "aws_eip" "app" {
#   instance = aws_instance.app.id
#   domain   = "vpc"
# 
#   tags = {
#     Name      = "${var.project_name}-app-eip"
#     Project   = var.project_name
#     ManagedBy = "terraform"
#   }
# }