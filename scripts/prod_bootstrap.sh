#!/usr/bin/env bash
# ARGUS production bootstrap — run once on a fresh server.
# Usage: bash scripts/prod_bootstrap.sh
set -euo pipefail

echo "=== ARGUS Production Bootstrap ==="

# 1. Check prerequisites
command -v docker  >/dev/null || { echo "ERROR: docker not found"; exit 1; }
docker compose version >/dev/null 2>&1 || \
  docker-compose version >/dev/null 2>&1 || \
  { echo "ERROR: docker compose not found"; exit 1; }

# 2. Verify .env.prod exists
[ -f .env.prod ] || {
  echo "ERROR: .env.prod not found. Copy .env.prod.example and fill in secrets."
  exit 1
}

# 3. Source env to validate required vars
set -a; source .env.prod; set +a
for var in POSTGRES_PASSWORD REDIS_PASSWORD JWT_SECRET ADMIN_PASSWORD; do
  val="${!var:-}"
  [ "$val" = "CHANGE_ME" ] || [ "$val" = "CHANGE_ME_STRONG_PASSWORD" ] || \
  [ "$val" = "CHANGE_ME_64_CHAR_RANDOM_STRING" ] || [ -z "$val" ] && \
    { echo "ERROR: $var is not set or still placeholder in .env.prod"; exit 1; } || true
done
echo "[OK] Secrets validated"

# 4. Build images
echo "[..] Building Docker images..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache
echo "[OK] Images built"

# 5. Start infrastructure services first (DB, Redis, Kafka)
echo "[..] Starting infrastructure services..."
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d postgres redis zookeeper kafka
echo "[..] Waiting 30s for infrastructure to initialise..."
sleep 30

# 6. Run Alembic migrations
echo "[..] Running database migrations..."
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  run --rm argus-api python -m alembic upgrade head
echo "[OK] Migrations applied"

# 7. Seed misinfo model weights (train if missing)
echo "[..] Ensuring model weights are present..."
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  run --rm argus-api python -c "
from models.misinfo.detector import detect
detect('test')
print('Misinfo model ready')
"

# 8. Start all remaining services
echo "[..] Starting all services..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
echo "[..] Waiting 60s for services to stabilise..."
sleep 60

# 9. Health check
echo "[..] Running health check..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)
[ "$HTTP_CODE" = "200" ] || { echo "ERROR: Nginx health check failed (HTTP $HTTP_CODE)"; exit 1; }
echo "[OK] Nginx responding"

API_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health)
[ "$API_CODE" = "200" ] || { echo "ERROR: API health check failed (HTTP $API_CODE)"; exit 1; }
echo "[OK] API responding"

# 10. Run verify_argus.py inside container
echo "[..] Running ARGUS verification suite..."
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec argus-api python verify_argus.py

echo ""
echo "========================================================="
echo "ARGUS production stack is live."
echo "  Dashboard:  http://localhost"
echo "  API docs:   http://localhost/api/docs"
echo "  Health:     http://localhost/health"
echo "========================================================="
