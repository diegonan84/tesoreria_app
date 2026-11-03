#!/usr/bin/env bash
# Instala Docker y levanta el sistema en una VM Debian 13 recién creada (Proxmox).
# Ejecutar como root dentro de la carpeta del proyecto, ej:
#   cd /opt/tesoreria && bash scripts/instalar_servidor.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# 1) Docker Engine + plugin compose (repositorio oficial de Docker)
if ! command -v docker >/dev/null 2>&1; then
    apt-get update
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
fi

# 2) .env con claves aleatorias (solo la primera vez; no se pisa si ya existe)
if [ ! -f .env ]; then
    IP=$(hostname -I | awk '{print $1}')
    cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 16)
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=http://${IP}:8000
EOF
    chmod 600 .env
    echo ".env creado con claves aleatorias."
fi

# 3) Construir y levantar (la app crea las tablas sola en el primer arranque)
docker compose up -d --build

echo
echo "Listo. Falta crear el primer administrador:"
echo "  docker compose exec app python -m scripts.crear_admin"
echo "Después entrá desde el navegador a: http://$(hostname -I | awk '{print $1}'):8000"
