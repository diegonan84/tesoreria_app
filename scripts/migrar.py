"""Crea las tablas en la base de datos (ejecutar una vez en el primer arranque Docker).

Uso:
    docker compose run --rm app python scripts/migrar.py
"""
from backend.database import Base, engine
import backend.models  # asegura que todos los modelos estén registrados

Base.metadata.create_all(bind=engine)
print("Tablas verificadas/creadas correctamente.")