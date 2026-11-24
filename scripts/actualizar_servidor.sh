#!/usr/bin/env bash
# Actualiza el servidor (Debian, Docker) con un paquete nuevo, con backup previo.
#
# En la PC de desarrollo:
#   git archive --format=tar.gz -o tesoreria.tar.gz HEAD
#   scp tesoreria.tar.gz root@10.78.10.158:/root/
# En el servidor, como root:
#   tar xzf /root/tesoreria.tar.gz -C /tmp scripts/actualizar_servidor.sh
#   bash /tmp/scripts/actualizar_servidor.sh
#
# Qué hace:
#   1. Backup de la base (pg_dump) y del código actual en /root/respaldos/
#   2. Descomprime el paquete sobre /opt/tesoreria (no toca .env ni los volúmenes de datos)
#   3. Reconstruye y reinicia la app: al arrancar aplica las migraciones pendientes (alembic upgrade head)
#   4. Verifica que la app responda y muestra la versión de la base
set -euo pipefail

DESTINO=/opt/tesoreria
PAQUETE=${1:-/root/tesoreria.tar.gz}
TS=$(date +%Y%m%d-%H%M)
RESPALDOS=/root/respaldos

[ -f "$PAQUETE" ] || { echo "No encuentro el paquete $PAQUETE"; exit 1; }
cd "$DESTINO"
mkdir -p "$RESPALDOS"

version_base() {
    docker compose exec -T db psql -U postgres -d tesoreria_db -tAc "select version_num from alembic_version" 2>/dev/null || echo "?"
}

echo "== 1. Backup =="
docker compose exec -T db pg_dump -U postgres tesoreria_db > "$RESPALDOS/$TS-tesoreria_db.sql"
tar czf "$RESPALDOS/$TS-codigo.tar.gz" -C "$DESTINO" --exclude=./backups .
ls -lh "$RESPALDOS/$TS-tesoreria_db.sql" "$RESPALDOS/$TS-codigo.tar.gz"
echo "Versión de la base antes: $(version_base)"

echo "== 2. Código nuevo =="
tar xzf "$PAQUETE" -C "$DESTINO"

echo "== 3. Reiniciar la app (aplica migraciones) =="
docker compose up -d --build app

echo "== 4. Verificación =="
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login | grep -q 200; then
        echo "La app responde (login 200)."
        break
    fi
    sleep 3
    [ "$i" = 30 ] && { echo "La app NO responde. Ver: docker compose logs app"; docker compose logs --tail 40 app; exit 1; }
done
echo "Versión de la base después: $(version_base)"
for ruta in /control-fichadas /home-office; do
    echo "  $ruta -> $(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$ruta")"
done
docker compose logs --tail 15 app
echo "Listo. Backup en $RESPALDOS/$TS-*"
