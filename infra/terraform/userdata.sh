#!/usr/bin/env bash
# EC2 bootstrap — runs once on first launch via cloud-init
# All secrets are pulled from SSM Parameter Store — nothing is hardcoded.
set -euo pipefail
exec > >(tee /var/log/argus-bootstrap.log) 2>&1

echo "=== ARGUS EC2 Bootstrap ==="
echo "Timestamp: $(date -u)"

# 1. System packages
dnf update -y
dnf install -y docker git curl python3-pip jq awscli unzip

# 2. Docker + Compose V2
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user
mkdir -p /usr/local/lib/docker/cli-plugins
COMPOSE_URL="https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64"
curl -SL "$COMPOSE_URL" -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
echo "[OK] Docker $(docker --version)"
echo "[OK] Compose $(docker compose version)"

# 3. CloudWatch agent
dnf install -y amazon-cloudwatch-agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'CWCONFIG'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/argus-bootstrap.log",
            "log_group_name": "/argus/bootstrap",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/home/ec2-user/argus/*.log",
            "log_group_name": "/argus/app",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  },
  "metrics": {
    "metrics_collected": {
      "mem":  { "measurement": ["mem_used_percent"] },
      "disk": {
        "measurement": ["disk_used_percent"],
        "resources": ["/"]
      }
    },
    "append_dimensions": { "InstanceId": "$${aws:InstanceId}" }
  }
}
CWCONFIG
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent
echo "[OK] CloudWatch agent started"

# 4. Read secrets from SSM Parameter Store
AWS_REGION="${aws_region}"
get_ssm() {
  aws ssm get-parameter --name "$1" --with-decryption \
    --region "$AWS_REGION" --query Parameter.Value --output text
}

echo "[..] Fetching secrets from SSM..."
DB_PASSWORD=$(get_ssm "/argus/db_password")
REDIS_PASSWORD=$(get_ssm "/argus/redis_password")
JWT_SECRET=$(get_ssm "/argus/jwt_secret")
ADMIN_PASSWORD=$(get_ssm "/argus/admin_password")
echo "[OK] Secrets fetched"

# 5. Clone or pull repo
REPO_DIR="/home/ec2-user/argus"
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "[..] Cloning repository..."
  # Replace with your actual repo URL:
  git clone https://github.com/YOUR_ORG/argus.git "$REPO_DIR"
else
  echo "[..] Pulling latest code..."
  git -C "$REPO_DIR" pull origin main
fi
chown -R ec2-user:ec2-user "$REPO_DIR"
echo "[OK] Code at $REPO_DIR"

# 6. Write .env.prod with live values from SSM + Terraform outputs
cat > "$REPO_DIR/.env.prod" <<EOF
POSTGRES_URL=postgresql://argus:$${DB_PASSWORD}@${db_endpoint}/argus
POSTGRES_PASSWORD=$${DB_PASSWORD}
REDIS_URL=rediss://:$${REDIS_PASSWORD}@${redis_endpoint}:6379
REDIS_PASSWORD=$${REDIS_PASSWORD}
KAFKA_BOOTSTRAP=localhost:9092
JWT_SECRET=$${JWT_SECRET}
ADMIN_PASSWORD=$${ADMIN_PASSWORD}
ALERT_SCORE_THRESHOLD=7.5
DNA_SIMILARITY_THRESHOLD=0.85
PS402_MARKET_MOVING_THRESHOLD=0.6
REPORTS_DIR=/tmp/argus_reports
S3_REPORTS_BUCKET=${reports_bucket}
S3_MODELS_BUCKET=${models_bucket}
AWS_DEFAULT_REGION=${aws_region}
AWS_REGION=${aws_region}
DOMAIN_NAME=${domain_name}
EOF
chmod 600 "$REPO_DIR/.env.prod"
chown ec2-user:ec2-user "$REPO_DIR/.env.prod"
echo "[OK] .env.prod written"

# 7. Pull model weights from S3 (if available from previous deploy)
echo "[..] Syncing model weights from S3..."
aws s3 sync "s3://${models_bucket}/weights/" "$REPO_DIR/models/" \
  --region "$AWS_REGION" 2>/dev/null || echo "[INFO] No weights in S3 yet — will train on first run"

# 8. ECR login and pull Docker images
ECR_REGISTRY="${ecr_registry}"
echo "[..] Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Pull if images exist in ECR
docker pull "$ECR_REGISTRY/argus-api:latest"     2>/dev/null || echo "[INFO] argus-api not in ECR yet — will build locally"
docker pull "$ECR_REGISTRY/argus-dashboard:latest" 2>/dev/null || echo "[INFO] argus-dashboard not in ECR yet — will build locally"

# 9. Run production bootstrap
echo "[..] Running prod_bootstrap.sh..."
cd "$REPO_DIR"
bash scripts/prod_bootstrap.sh || echo "[WARN] Bootstrap completed with warnings (check logs)"

# 10. Push trained model weights back to S3
echo "[..] Pushing model weights to S3..."
aws s3 sync "$REPO_DIR/models/" "s3://${models_bucket}/weights/" \
  --region "$AWS_REGION" \
  --exclude "*.py" \
  --exclude "__pycache__/*" \
  --exclude "*.pyc" \
  2>/dev/null || echo "[WARN] S3 model sync failed (non-fatal)"

# 11. Set up automatic daily DB backup via cron
cat > /etc/cron.d/argus-backup <<'CRON'
0 2 * * * ec2-user cd /home/ec2-user/argus && bash scripts/aws_backup.sh >> /home/ec2-user/argus/backup.log 2>&1
CRON
echo "[OK] Backup cron installed"

# 12. Set up daily model weight sync to S3
cat > /etc/cron.d/argus-model-sync <<'CRON'
30 2 * * * ec2-user aws s3 sync /home/ec2-user/argus/models/ s3://${models_bucket}/weights/ --exclude "*.py" --exclude "__pycache__/*" >> /home/ec2-user/argus/s3-sync.log 2>&1
CRON
echo "[OK] Model sync cron installed"

echo ""
echo "=== Bootstrap complete: $(date -u) ==="
echo "ARGUS is now running at https://${domain_name}"
