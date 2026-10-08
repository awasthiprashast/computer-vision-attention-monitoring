variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for all resources."
  type        = string
  default     = "attention"
}

variable "dashboard_allowed_cidr" {
  description = "CIDR allowed to reach the dashboard (port 8501), e.g. your public IP as 203.0.113.7/32. No default on purpose."
  type        = string

  validation {
    condition     = can(cidrhost(var.dashboard_allowed_cidr, 0)) && var.dashboard_allowed_cidr != "0.0.0.0/0"
    error_message = "Provide a valid CIDR that is not 0.0.0.0/0: the dashboard has no login."
  }
}

variable "instance_type" {
  description = "EC2 instance type for the backend and dashboard."
  type        = string
  default     = "t3.micro"
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "repo_url" {
  description = "Git repository the instance clones at boot."
  type        = string
  default     = "https://github.com/awasthiprashast/computer-vision-attention-monitoring"
}

variable "repo_branch" {
  description = "Branch the instance deploys."
  type        = string
  default     = "main"
}

variable "skip_final_snapshot" {
  description = "Skip the final RDS snapshot on destroy. Set false for anything you want to keep."
  type        = bool
  default     = true
}
