# Terraform Variables for Yojana-AI EC2 Deployment

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "yojana-ai"
}

variable "key_name" {
  description = "EC2 key pair name for SSH access (MUST BE CREATED FIRST)"
  type        = string
  # TODO: Set this in terraform.tfvars or via -var flag
  # Example: key_name = "yojana-ai-key"
}

variable "allowed_ips" {
  description = "List of IP addresses allowed to access Jenkins and SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # TODO: Restrict to your IP for security
  # Example: allowed_ips = ["203.0.113.0/32"]  # Your public IP
}

# ============================================
# EC2 INSTANCE CONFIGURATION
# ============================================

variable "jenkins_instance_type" {
  description = "Jenkins server instance type"
  type        = string
  default     = "t2.micro"  # 1GB RAM, sufficient for Jenkins
}

variable "app_instance_type" {
  description = "Application server instance type"
  type        = string
  default     = "t2.small"  # 2GB RAM - REQUIRED for BGE-M3 + Ollama
  
  validation {
    condition     = contains(["t2.small", "t2.medium", "t3.small", "t3.medium"], var.app_instance_type)
    error_message = "App instance must be at least t2.small (2GB RAM) to fit BGE-M3 model (1.06GB) + Ollama (450MB)."
  }
}

variable "app_ebs_size" {
  description = "EBS volume size for application server (GB)"
  type        = number
  default     = 42  # 25GB app + 10GB models + 5GB buffer + 2GB swap
  
  validation {
    condition     = var.app_ebs_size >= 40
    error_message = "App EBS size must be at least 40GB for Docker images, models, and swap space."
  }
}

# ============================================
# COST OPTIMIZATION FLAGS
# ============================================

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring (costs extra)"
  type        = bool
  default     = false  # Keep false for free tier
}

variable "enable_elastic_ips" {
  description = "Allocate Elastic IPs for instances (free when attached, costs when detached)"
  type        = bool
  default     = false  # Set to true if you want static IPs
}

# ============================================
# TAGGING
# ============================================

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default = {
    Owner       = "DevOps"
    CostCenter  = "Portfolio"
    Terraform   = "true"
  }
}