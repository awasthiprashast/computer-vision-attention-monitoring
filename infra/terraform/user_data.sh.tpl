#!/bin/bash
# Boot script for the app host (rendered by Terraform's templatefile).
# Terraform substitutes dollar-brace placeholders; plain $VAR is left for bash.
set -euxo pipefail
exec > >(tee /var/log/attention-bootstrap.log) 2>&1

# t3.micro has 1 GB of RAM; a swap file keeps `docker build` from being OOM-killed.
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

dnf install -y docker git
systemctl enable --now docker

mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

git clone --branch "${repo_branch}" --depth 1 "${repo_url}" /opt/attention
cd /opt/attention

get_param() {
  aws ssm get-parameter --region "${region}" --name "$1" --with-decryption \
    --query Parameter.Value --output text
}

umask 077
cat > .env <<ENV
DATABASE_URL=$(get_param /${project}/database_url)
API_KEY=$(get_param /${project}/api_key)
S3_BUCKET=${bucket}
AWS_DEFAULT_REGION=${region}
ENV

docker compose -f docker-compose.aws.yml up -d --build
