#!/usr/bin/env bash
# aws_backup.sh — Push model weights to S3 + log status.
# For RDS, rely on automated AWS snapshots (configured in rds.tf).
# Runs daily via cron on the EC2 instance.
set -euo pipefail

REPO_DIR="/home/ec2-user/argus"
AWS_REGION="${AWS_REGION:-ap-south-1}"

# Load env (S3_MODELS_BUCKET, S3_REPORTS_BUCKET)
set -a
source "$REPO_DIR/.env.prod"
set +a

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "=== ARGUS S3 backup: $TIMESTAMP ==="

# ── Model weights → S3 ────────────────────────────────────────────────────────
if [ -n "${S3_MODELS_BUCKET:-}" ]; then
  aws s3 sync "$REPO_DIR/models/" "s3://$S3_MODELS_BUCKET/weights/" \
    --region "$AWS_REGION" \
    --exclude "*.py" \
    --exclude "__pycache__/*" \
    --exclude "*.pyc"
  echo "[OK] Model weights synced to s3://$S3_MODELS_BUCKET/weights/"
else
  echo "[SKIP] S3_MODELS_BUCKET not set — skipping model sync"
fi

# ── RDS note ──────────────────────────────────────────────────────────────────
echo "[INFO] RDS automated snapshots are managed by AWS (7-day retention, configured in rds.tf)"
echo "[INFO] To trigger manual snapshot:"
echo "       aws rds create-db-snapshot --db-instance-identifier argus-postgres --db-snapshot-identifier argus-manual-$TIMESTAMP --region $AWS_REGION"

echo "=== Backup complete: $(date -u) ==="
