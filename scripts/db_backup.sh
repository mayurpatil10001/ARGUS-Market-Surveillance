#!/usr/bin/env bash
# PostgreSQL dump to ./backups/argus_YYYYMMDD_HHMMSS.sql.gz
set -euo pipefail
set -a; source .env.prod; set +a
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
FILENAME="argus_$(date +%Y%m%d_%H%M%S).sql.gz"
echo "Backing up PostgreSQL to $BACKUP_DIR/$FILENAME..."
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec -T postgres pg_dump -U argus argus | gzip > "$BACKUP_DIR/$FILENAME"
echo "Backup complete: $BACKUP_DIR/$FILENAME"
# Keep only last 14 backups
ls -t "$BACKUP_DIR"/argus_*.sql.gz | tail -n +15 | xargs -r rm --
echo "Old backups pruned. Current count: $(ls $BACKUP_DIR/argus_*.sql.gz | wc -l)"
