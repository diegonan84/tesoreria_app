"""Deja la base lista antes de arrancar la app (lo ejecuta el contenedor en cada inicio).

- Base vacía: crea todas las tablas y la marca en la última migración de Alembic.
- Base existente: aplica las migraciones pendientes (alembic upgrade head).

Uso:
    python -m scripts.preparar_db
"""
from sqlalchemy import inspect
from alembic import command
from alembic.config import Config

from backend.database import Base, engine
import backend.models  # asegura que todos los modelos estén registrados

alembic_cfg = Config("alembic.ini")  # alembic/env.py toma DATABASE_URL del entorno

if "usuarios" not in inspect(engine).get_table_names():
    Base.metadata.create_all(bind=engine)
    command.stamp(alembic_cfg, "head")
    print("Base nueva: tablas creadas y marcadas en la última migración.")
else:
    command.upgrade(alembic_cfg, "head")
    print("Base existente: migraciones al día.")
