data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${var.project}-app"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

# Session Manager access (replaces SSH).
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "app" {
  statement {
    sid       = "ReadOwnSecrets"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.database_url.arn, aws_ssm_parameter.api_key.arn]
  }

  statement {
    sid       = "ReportObjects"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.reports.arn}/*"]
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "${var.project}-app"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}

resource "aws_iam_instance_profile" "app" {
  name = "${var.project}-app"
  role = aws_iam_role.app.name
}
