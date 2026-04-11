output "ec2_public_ip" {
  value       = aws_eip.argus.public_ip
  description = "Elastic IP of the ARGUS EC2 instance"
}
output "alb_dns_name" {
  value       = aws_lb.argus.dns_name
  description = "ALB DNS name — point your CNAME here for external domains"
}
output "rds_endpoint" {
  value       = aws_db_instance.argus.endpoint
  description = "RDS PostgreSQL 16 endpoint (host:port)"
}
output "redis_endpoint" {
  value       = aws_elasticache_replication_group.argus.primary_endpoint_address
  description = "ElastiCache Redis primary endpoint"
}
output "reports_bucket" {
  value       = aws_s3_bucket.reports.id
  description = "S3 bucket for PDF case reports"
}
output "models_bucket" {
  value       = aws_s3_bucket.models.id
  description = "S3 bucket for model weights backup"
}
output "ecr_api_url" {
  value       = aws_ecr_repository.api.repository_url
  description = "ECR URL for argus-api Docker image"
}
output "ecr_dashboard_url" {
  value       = aws_ecr_repository.dashboard.repository_url
  description = "ECR URL for argus-dashboard Docker image"
}
output "domain_url" {
  value       = "https://${var.domain_name}"
  description = "Primary application URL"
}
output "api_url" {
  value       = "https://api.${var.domain_name}"
  description = "API docs URL"
}
output "cloudwatch_dashboard" {
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=ARGUS-Production"
  description = "CloudWatch dashboard URL for monitoring"
}
output "ssm_session_command" {
  value       = "aws ssm start-session --target ${aws_instance.argus.id} --region ${var.aws_region}"
  description = "SSM Session Manager command (no SSH key required)"
}
