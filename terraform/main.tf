terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ECR Repository
resource "aws_ecr_repository" "rag_api" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "govt-schemes-rag"
    Environment = var.environment
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "rag_cluster" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.project_name}-cluster"
    Environment = var.environment
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "rag_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-logs"
    Environment = var.environment
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-execution-role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "rag_task" {
  family                   = var.project_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "rag-api"
      image     = "${aws_ecr_repository.rag_api.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        }
      ]

      secrets = [
        {
          name      = "GROQ_API_KEY"
          valueFrom = aws_secretsmanager_secret.groq_api_key.arn
        },
        {
          name      = "QDRANT_URL"
          valueFrom = aws_secretsmanager_secret.qdrant_url.arn
        },
        {
          name      = "QDRANT_API_KEY"
          valueFrom = aws_secretsmanager_secret.qdrant_api_key.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.rag_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-task"
    Environment = var.environment
  }
}

# Secrets Manager
resource "aws_secretsmanager_secret" "groq_api_key" {
  name = "${var.project_name}/groq-api-key"

  tags = {
    Name        = "${var.project_name}-groq-key"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "qdrant_url" {
  name = "${var.project_name}/qdrant-url"

  tags = {
    Name        = "${var.project_name}-qdrant-url"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "qdrant_api_key" {
  name = "${var.project_name}/qdrant-api-key"

  tags = {
    Name        = "${var.project_name}-qdrant-key"
    Environment = var.environment
  }
}

# VPC (simplified - use existing VPC in production)
resource "aws_default_vpc" "default" {
  tags = {
    Name = "Default VPC"
  }
}

resource "aws_default_subnet" "default_az1" {
  availability_zone = "${var.aws_region}a"
}

resource "aws_default_subnet" "default_az2" {
  availability_zone = "${var.aws_region}b"
}

# Security Group
resource "aws_security_group" "rag_sg" {
  name        = "${var.project_name}-sg"
  description = "Security group for RAG API"
  vpc_id      = aws_default_vpc.default.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-sg"
    Environment = var.environment
  }
}

# ECS Service
resource "aws_ecs_service" "rag_service" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.rag_cluster.id
  task_definition = aws_ecs_task_definition.rag_task.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_default_subnet.default_az1.id, aws_default_subnet.default_az2.id]
    security_groups  = [aws_security_group.rag_sg.id]
    assign_public_ip = true
  }

  tags = {
    Name        = "${var.project_name}-service"
    Environment = var.environment
  }
}
