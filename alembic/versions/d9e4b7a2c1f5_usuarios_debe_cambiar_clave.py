"""usuarios: debe_cambiar_clave (cambio obligatorio tras importación o reseteo)

Revision ID: d9e4b7a2c1f5
Revises: c3f8a2e1d6b4
Create Date: 2026-11-04

"""
from alembic import op
import sqlalchemy as sa

revision = 'd9e4b7a2c1f5'
down_revision = 'c3f8a2e1d6b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('debe_cambiar_clave', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('usuarios', 'debe_cambiar_clave')
