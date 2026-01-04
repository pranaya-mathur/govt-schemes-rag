# Terraform Outputs for Yojana-AI

# ============================================
# EC2 INSTANCE OUTPUTS
# ============================================

output "jenkins_instance_id" {
  description = "Jenkins EC2 instance ID"
  value       = aws_instance.jenkins.id
}

output "jenkins_public_ip" {
  description = "Jenkins server public IP address"
  value       = aws_instance.jenkins.public_ip
}

output "jenkins_private_ip" {
  description = "Jenkins server private IP address"
  value       = aws_instance.jenkins.private_ip
}

output "jenkins_url" {
  description = "Jenkins web UI URL"
  value       = "http://${aws_instance.jenkins.public_ip}:8080"
}

output "app_instance_id" {
  description = "Application EC2 instance ID"
  value       = aws_instance.app.id
}

output "app_public_ip" {
  description = "Application server public IP address"
  value       = aws_instance.app.public_ip
}

output "app_private_ip" {
  description = "Application server private IP address"
  value       = aws_instance.app.private_ip
}

output "app_url" {
  description = "Application API URL"
  value       = "http://${aws_instance.app.public_ip}"
}

output "app_docs_url" {
  description = "Application API docs URL"
  value       = "http://${aws_instance.app.public_ip}/docs"
}

# ============================================
# ECR REPOSITORY OUTPUTS
# ============================================

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = aws_ecr_repository.app.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.app.arn
}

# ============================================
# SECRETS MANAGER OUTPUTS
# ============================================

output "secrets_manager_arn" {
  description = "Secrets Manager secret ARN for API keys"
  value       = aws_secretsmanager_secret.api_keys.arn
}

output "secrets_manager_name" {
  description = "Secrets Manager secret name"
  value       = aws_secretsmanager_secret.api_keys.name
}

# ============================================
# SECURITY GROUP OUTPUTS
# ============================================

output "jenkins_security_group_id" {
  description = "Jenkins security group ID"
  value       = aws_security_group.jenkins.id
}

output "app_security_group_id" {
  description = "Application security group ID"
  value       = aws_security_group.app.id
}

# ============================================
# CLOUDWATCH LOG GROUPS
# ============================================

output "jenkins_log_group" {
  description = "CloudWatch log group for Jenkins"
  value       = aws_cloudwatch_log_group.jenkins.name
}

output "app_log_group" {
  description = "CloudWatch log group for Application"
  value       = aws_cloudwatch_log_group.app.name
}

output "api_log_group" {
  description = "CloudWatch log group for API logs"
  value       = aws_cloudwatch_log_group.api.name
}

# ============================================
# USEFUL SSH COMMANDS
# ============================================

output "ssh_jenkins" {
  description = "SSH command for Jenkins server"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${aws_instance.jenkins.public_ip}"
}

output "ssh_app" {
  description = "SSH command for Application server"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${aws_instance.app.public_ip}"
}

# ============================================
# DEPLOYMENT COMMANDS
# ============================================

output "ecr_login_command" {
  description = "AWS ECR login command for Docker"
  value       = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.app.repository_url}"
  sensitive   = true
}

output "docker_push_command" {
  description = "Docker push command example"
  value       = "docker tag yojana-ai:latest ${aws_ecr_repository.app.repository_url}:latest && docker push ${aws_ecr_repository.app.repository_url}:latest"
}

# ============================================
# SUMMARY OUTPUT
# ============================================

output "deployment_summary" {
  description = "Deployment summary"
  value = {
    jenkins_url    = "http://${aws_instance.jenkins.public_ip}:8080"
    app_url        = "http://${aws_instance.app.public_ip}"
    api_docs       = "http://${aws_instance.app.public_ip}/docs"
    jenkins_ssh    = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${aws_instance.jenkins.public_ip}"
    app_ssh        = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${aws_instance.app.public_ip}"
    ecr_repository = aws_ecr_repository.app.repository_url
    secrets_name   = aws_secretsmanager_secret.api_keys.name
  }
}