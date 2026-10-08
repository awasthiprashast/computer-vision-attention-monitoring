output "api_url" {
  description = "Set this as API_URL in the client."
  value       = "http://${aws_eip.app.public_ip}:8000/attention"
}

output "dashboard_url" {
  description = "Dashboard (only reachable from dashboard_allowed_cidr)."
  value       = "http://${aws_eip.app.public_ip}:8501"
}

output "api_key" {
  description = "Set this as API_KEY in the client. Run `terraform output -raw api_key`."
  value       = random_password.api_key.result
  sensitive   = true
}

output "reports_bucket" {
  description = "S3 bucket for generated PDF reports."
  value       = aws_s3_bucket.reports.bucket
}

output "rds_endpoint" {
  description = "RDS address (private, only reachable from the app host)."
  value       = aws_db_instance.main.address
}

output "ssm_session_command" {
  description = "Open a shell on the instance without SSH."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.app.id}"
}
