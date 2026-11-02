#!/usr/bin/env bash
# Backups diarios de la BD + archivos subidos (fotos/manuales/notas).
# Programar con cron, ej:
#   0 2 * * * /app/scripts/backup.sh >/dev/null 2>&1
set -euo pipefail

DEST="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP=$(date +%Y%m%d_%H%M)
DB_CONTAINER=$(docker compose ps -q db)

mkdir -p "$DEST"

# 1) Base de datos (volcado lógico comprimido)
docker exec -t "$DB_CONTAINER" pg_dump -U postgres tesoreria_db \
    | gzip > "$DEST/tesoreria_db_${STAMP}.sql.gz"

# 2) Archivos subidos por usuarios (salen del volumen app)
docker run --rm \
    -v "$(docker compose ps -q app):/mnt" \
    -v "$DEST:/backups" \
    alpine tar czf "/backups/uploads_${STAMP}.tar.gz" \
        -C /mnt frontend/fotos frontend/manuales frontend/notas 2>/dev/null || true

# 3) Rotación: borrar backups con más de KEEP_DAYS días
find "$DEST" -name "tesoreria_db_*" -mtime +"$KEEP_DAYS" -delete
find "$DEST" -name "uploads_*" -mtime +"$KEEP_DAYS" -delete

echo "Backup completado en $DEST ($STAMP)"