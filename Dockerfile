FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencias del sistema mínimas (pg_dump no hace falta acá; librerías núcleo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# Antes de arrancar: crea las tablas (base vacía) o aplica las migraciones pendientes
CMD ["sh", "-c", "python -m scripts.preparar_db && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]