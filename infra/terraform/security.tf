resource "aws_security_group" "app" {
  name        = "${var.project}-app"
  description = "Backend API and dashboard"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project}-app" }
}

# Student clients can be anywhere; the API is protected by its API key.
resource "aws_vpc_security_group_ingress_rule" "api" {
  security_group_id = aws_security_group.app.id
  description       = "Backend API (X-API-Key protected)"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 8000
  to_port           = 8000
  ip_protocol       = "tcp"
}

# The dashboard has no login, so it is limited to a single CIDR.
resource "aws_vpc_security_group_ingress_rule" "dashboard" {
  security_group_id = aws_security_group.app.id
  description       = "Streamlit dashboard"
  cidr_ipv4         = var.dashboard_allowed_cidr
  from_port         = 8501
  to_port           = 8501
  ip_protocol       = "tcp"
}

# No SSH rule: shell access goes through SSM Session Manager.

resource "aws_vpc_security_group_egress_rule" "app_all" {
  security_group_id = aws_security_group.app.id
  description       = "Outbound (package installs, git clone, AWS APIs)"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "db" {
  name        = "${var.project}-db"
  description = "PostgreSQL, reachable only from the app instance"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project}-db" }
}

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  security_group_id            = aws_security_group.db.id
  description                  = "PostgreSQL from the app security group"
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}
