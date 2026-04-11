#!/usr/bin/env bash
# Graceful shutdown — waits for in-flight requests to complete (30s timeout)
set -euo pipefail
echo "Stopping ARGUS production stack..."
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  down --timeout 30
echo "Stack stopped. Volumes preserved."
