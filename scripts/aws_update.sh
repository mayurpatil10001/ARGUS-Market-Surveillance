#!/usr/bin/env bash
# aws_update.sh — Zero-downtime rolling update on EC2
# Pulls latest ECR images, runs migrations, restarts containers one at a time.
# Runs on the EC2 instance itself (or via SSM).
set -euo pipefail

REPO_DIR="/home/ec2-user/argus"
cd "$REPO_DIR"

AWS_REGION=$(aws ec2 metadata --data region 2>/dev/null || echo "${AWS_REGION:-ap-south-1}")

echo "=== ARGUS rolling update: $(date -u) ==="

# Pull latest code
git pull origin main
echo "[OK] Code updated"

# ECR login
ECR_REGISTRY=$(aws ecr describe-repositories \
  --query "repositories[?repositoryName=='argus-api'].repositoryUri" \
  --output text --region "$AWS_REGION" | sed 's|/argus-api||')

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Pull latest images
docker compose -f docker-compose.prod.yml -f docker-compose.aws.yml \
  pull argus-api argus-dashboard
echo "[OK] Images pulled"

# Run DB migrations before restart (safe — idempotent)
docker compose -f docker-compose.prod.yml -f docker-compose.aws.yml \
  run --rm argus-api python -m alembic upgrade head
echo "[OK] Migrations applied"

# Rolling restart: api first, verify health, then worker + dashboard
docker compose -f docker-compose.prod.yml -f docker-compose.aws.yml \
  up -d --no-deps argus-api
echo "[..] Waiting 15s for API to start..."
sleep 15

curl -sf http://localhost:8000/health || {
  echo "ERROR: API health check failed after restart"
  exit 1
}
echo "[OK] API healthy"

docker compose -f docker-compose.prod.yml -f docker-compose.aws.yml \
  up -d --no-deps argus-worker
docker compose -f docker-compose.prod.yml -f docker-compose.aws.yml \
  up -d --no-deps argus-dashboard
echo "[OK] Worker and dashboard updated"

# Clean up old images to free disk space
docker image prune -f
echo "[OK] Old images pruned"

echo "=== Update complete: $(date -u) ==="
