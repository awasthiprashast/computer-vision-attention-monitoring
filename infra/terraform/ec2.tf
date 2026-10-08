data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023_ami.value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  # IMDSv2 only. Hop limit 2 lets containers on the host reach the instance role credentials.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    region      = var.region
    project     = var.project
    repo_url    = var.repo_url
    repo_branch = var.repo_branch
    bucket      = aws_s3_bucket.reports.bucket
  })
  user_data_replace_on_change = true

  # The RDS instance and SSM parameters must exist before the boot script reads them.
  depends_on = [aws_ssm_parameter.database_url, aws_ssm_parameter.api_key]

  tags = { Name = "${var.project}-app" }
}

# A fixed address, so the client's API_URL does not change across restarts.
resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = { Name = "${var.project}-app" }
}
