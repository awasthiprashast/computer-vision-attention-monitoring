# Secrets are generated here and stored as SecureStrings. The instance reads them at boot
# through its IAM role, so they never appear in user_data.

resource "random_password" "api_key" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "database_url" {
  name = "/${var.project}/database_url"
  type = "SecureString"
  # sslmode=require: RDS PostgreSQL 15+ rejects unencrypted connections by default.
  value = "postgresql://${aws_db_instance.main.username}:${random_password.db.result}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}?sslmode=require"
}

resource "aws_ssm_parameter" "api_key" {
  name  = "/${var.project}/api_key"
  type  = "SecureString"
  value = random_password.api_key.result
}
