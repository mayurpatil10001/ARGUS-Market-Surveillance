#!/usr/bin/env bash
# aws_deploy.sh — Full AWS first-time deployment (Terraform + ECR push)
# Run from repo root with AWS CLI configured.
# Usage: bash scripts/aws_deploy.sh
set -euo pipefail

echo "=== ARGUS AWS Deployment ==="

# ── Prerequisites ──────────────────────────────────────────────────────────────
command -v aws       >/dev/null || { echo "ERROR: aws CLI not found. Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"; exit 1; }
command -v terraform >/dev/null || { echo "ERROR: terraform not found. Install: https://developer.hashicorp.com/terraform/install"; exit 1; }
command -v docker    >/dev/null || { echo "ERROR: docker not found"; exit 1; }

# ── AWS credentials ────────────────────────────────────────────────────────────
aws sts get-caller-identity > /dev/null 2>&1 || { echo "ERROR: AWS credentials not configured. Run: aws configure"; exit 1; }
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-ap-south-1}
echo "[OK] AWS Account: $AWS_ACCOUNT | Region: $AWS_REGION"

# ── Terraform ─────────────────────────────────────────────────────────────────
[ -f infra/terraform/terraform.tfvars ] || {
  echo "ERROR: infra/terraform/terraform.tfvars not found"
  echo "       Copy infra/terraform/terraform.tfvars.example and fill in values"
  exit 1
}

cd infra/terraform

echo "[..] Initialising Terraform..."
terraform init -upgrade

echo "[..] Validating configuration..."
terraform validate
echo "[OK] Terraform config valid"

echo "[..] Planning infrastructure..."
terraform plan -out=argus.tfplan

echo ""
read -p "Apply this plan? (yes/no): " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "Aborted."; exit 0; }

echo "[..] Applying Terraform plan..."
terraform apply argus.tfplan

# ── Read Terraform outputs ─────────────────────────────────────────────────────
ECR_API=$(terraform output -raw ecr_api_url)
ECR_DASHBOARD=$(terraform output -raw ecr_dashboard_url)
EC2_IP=$(terraform output -raw ec2_public_ip)
ALB_DNS=$(terraform output -raw alb_dns_name)
DOMAIN=$(terraform output -raw domain_url)
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=ARGUS" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" --output text)

cd ../..

# ── Build & push Docker images to ECR ─────────────────────────────────────────
echo "[..] Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$ECR_API"

echo "[..] Building and pushing API image..."
docker build -f Dockerfile.api -t "$ECR_API:latest" .
docker push "$ECR_API:latest"
echo "[OK] API image pushed: $ECR_API:latest"

echo "[..] Building and pushing dashboard image..."
docker build -f Dockerfile.dashboard -t "$ECR_DASHBOARD:latest" .
docker push "$ECR_DASHBOARD:latest"
echo "[OK] Dashboard image pushed: $ECR_DASHBOARD:latest"

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo "========================================================="
echo "[OK] ARGUS AWS deployment initiated successfully"
echo ""
echo "  EC2 IP:       $EC2_IP"
echo "  Instance ID:  $INSTANCE_ID"
echo "  ALB DNS:      $ALB_DNS"
echo "  Domain:       $DOMAIN"
echo ""
echo "EC2 is self-configuring via cloud-init (~5 minutes)."
echo ""
echo "Monitor bootstrap progress:"
echo "  CloudWatch: https://$AWS_REGION.console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logsV2:log-groups/log-group/\$252Fargus\$252Fbootstrap"
echo ""
echo "Or via SSM (no SSH key needed):"
echo "  aws ssm start-session --target $INSTANCE_ID --region $AWS_REGION"
echo ""
echo "For external domain, point CNAME to:"
echo "  $ALB_DNS"
echo "See: infra/DNS_SETUP.md"
echo "========================================================="
