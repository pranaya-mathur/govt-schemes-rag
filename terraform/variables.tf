variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "govt-schemes-rag"
}

variable "ecr_repo_name" {
  description = "ECR repository name"
  type        = string
  default     = "govt-schemes-rag"
}

variable "task_cpu" {
  description = "ECS task CPU units"
  type        = string
  default     = "1024"  # 1 vCPU
}

variable "task_memory" {
  description = "ECS task memory (MB)"
  type        = string
  default     = "2048"  # 2 GB
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}
