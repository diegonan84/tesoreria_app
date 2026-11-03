# Despliegue en Proxmox (Docker)

El sistema corre en una VM Debian 12 con Docker: un contenedor para la app (FastAPI) y otro
para PostgreSQL 16. Los datos quedan en volúmenes de Docker (`pgdata`, fotos, manuales, notas).

## 1. Crear la VM en Proxmox

1. Descargar la ISO de Debian 12 "netinst" y subirla a Proxmox: *local → ISO Images → Upload*
   (o *Download from URL*: `https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/`).
2. *Create VM*:
   - **OS**: la ISO de Debian 12.
   - **Disco**: 32 GB o más.
   - **CPU**: 2 cores. **Memoria**: 4096 MB.
   - **Red**: `vmbr0` (la misma red que las PCs de la oficina).
3. Instalar Debian: sin entorno de escritorio; tildar **SSH server** y **utilidades estándar**.
4. Conviene darle una **IP fija** (reserva en el DHCP del router, o configurada en la VM),
   porque los usuarios van a entrar por esa IP.

## 2. Copiar el sistema a la VM

En la PC de desarrollo (desde la carpeta del proyecto) se arma un paquete con lo commiteado:

```bash
git archive --format=tar.gz -o tesoreria.tar.gz HEAD
```

Copiarlo a la VM (con WinSCP o con `scp`, reemplazando la IP):

```bash
scp tesoreria.tar.gz root@IP_DE_LA_VM:/root/
```

## 3. Instalar y levantar (en la VM, como root)

```bash
mkdir -p /opt/tesoreria && tar xzf /root/tesoreria.tar.gz -C /opt/tesoreria
cd /opt/tesoreria && bash scripts/instalar_servidor.sh
```

El script instala Docker, genera un `.env` con claves aleatorias, construye la imagen y levanta
los contenedores. En el primer arranque la app crea todas las tablas.

## 4. Crear el primer administrador

```bash
cd /opt/tesoreria && docker compose exec app python -m scripts.crear_admin
```

Pide nombre, email, CUIL, repartición y contraseña. Luego se entra desde cualquier PC de la red a
`http://IP_DE_LA_VM:8000`.

## Actualizar a una versión nueva

Generar un `tesoreria.tar.gz` nuevo, copiarlo y en la VM:

```bash
tar xzf /root/tesoreria.tar.gz -C /opt/tesoreria
cd /opt/tesoreria && docker compose up -d --build
```

El `.env` y los datos se conservan; las migraciones pendientes se aplican solas al arrancar.

## Backups

`scripts/backup.sh` vuelca la base y los archivos subidos a `/backups` (rotación de 7 días).
Programarlo con `crontab -e` en la VM:

```
0 2 * * * cd /opt/tesoreria && bash scripts/backup.sh >/dev/null 2>&1
```

Además, se recomienda programar un backup de la VM completa desde Proxmox (*Datacenter → Backup*).

## Comandos útiles

```bash
docker compose ps              # estado de los contenedores
docker compose logs -f app     # ver logs de la app
docker compose restart app     # reiniciar la app
```
