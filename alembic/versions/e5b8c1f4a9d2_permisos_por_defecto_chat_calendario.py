"""permisos por defecto: Chat y Calendario para todos los usuarios

Revision ID: e5b8c1f4a9d2
Revises: d2a6f9c3e8b1
Create Date: 2026-11-02

"""
from alembic import op
import sqlalchemy as sa

revision = 'e5b8c1f4a9d2'
down_revision = 'd2a6f9c3e8b1'
branch_labels = None
depends_on = None

POR_DEFECTO = ["Operador", "Calendario", "Cal_Agenda", "Chat", "Chat_Mensajes"]
# Páginas de Patrimonio que antes no tenían permiso propio: quien ya tenía páginas de
# Patrimonio tildadas entraba igual, así que se las sumamos para no quitarle acceso.
PATRIMONIO_NUEVAS = ["Patr_Asignaciones", "Patr_Total", "Patr_Reportes"]


def upgrade() -> None:
    bind = op.get_bind()
    filas = bind.execute(sa.text("SELECT id, roles FROM usuarios")).fetchall()
    for uid, roles in filas:
        lista = [r.strip() for r in (roles or "").split(",") if r.strip()]
        nuevos = POR_DEFECTO[:]
        if any(r.startswith("Patr_") for r in lista):
            nuevos += PATRIMONIO_NUEVAS
        final = lista + [r for r in nuevos if r not in lista]
        if final != lista:
            bind.execute(sa.text("UPDATE usuarios SET roles = :r WHERE id = :id"), {"r": ",".join(final), "id": uid})


def downgrade() -> None:
    # No se revierte: no se puede distinguir lo agregado acá de lo que asignó un administrador
    pass
