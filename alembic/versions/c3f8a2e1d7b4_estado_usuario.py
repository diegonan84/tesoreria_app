"""estado explícito del usuario (pendiente / activo / suspendido / baja)

Revision ID: c3f8a2e1d7b4
Revises: c4e9d1a7b2f8
Create Date: 2026-11-02

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3f8a2e1d7b4'
down_revision = 'c4e9d1a7b2f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Las bases creadas con scripts/migrar.py (create_all) ya traen estas columnas
    existentes = [c["name"] for c in sa.inspect(op.get_bind()).get_columns('usuarios')]
    if 'estado' in existentes:
        return

    op.add_column('usuarios', sa.Column('estado', sa.String(20), nullable=False, server_default='PENDIENTE'))
    op.add_column('usuarios', sa.Column('fecha_baja', sa.DateTime(), nullable=True))
    op.add_column('usuarios', sa.Column('motivo_baja', sa.String(255), nullable=True))

    # Backfill desde los flags anteriores. Los "inhabilitados" (aprobado y no activo) pasan a
    # SUSPENDIDO: hasta ahora la baja no liberaba bienes ni puesto, así que es lo que realmente eran.
    op.execute("UPDATE usuarios SET estado = 'ACTIVO', aprobado = TRUE WHERE activo = TRUE")
    op.execute("UPDATE usuarios SET estado = 'SUSPENDIDO' WHERE activo = FALSE AND aprobado = TRUE")
    op.execute("UPDATE usuarios SET estado = 'PENDIENTE' WHERE activo IS NOT TRUE AND aprobado IS NOT TRUE")


def downgrade() -> None:
    op.drop_column('usuarios', 'motivo_baja')
    op.drop_column('usuarios', 'fecha_baja')
    op.drop_column('usuarios', 'estado')
