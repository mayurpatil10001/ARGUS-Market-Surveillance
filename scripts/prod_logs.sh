#!/usr/bin/env bash
# Tail logs from all services or a specific one.
# Usage: bash scripts/prod_logs.sh [service_name]
SERVICE=${1:-""}
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  logs -f --tail=100 $SERVICE
