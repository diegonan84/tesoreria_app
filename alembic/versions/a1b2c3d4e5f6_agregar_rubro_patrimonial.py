"""agregar rubro patrimonial numero y descripcion

Revision ID: a1b2c3d4e5f6
Revises: fcbf251ce270
Create Date: 2026-09-04

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'fcbf251ce270'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('patrimonio', sa.Column('rubro_patrimonial_numero', sa.String(50), nullable=True))
    op.add_column('patrimonio', sa.Column('rubro_patrimonial_descripcion', sa.String(255), nullable=True))

def downgrade() -> None:
    op.drop_column('patrimonio', 'rubro_patrimonial_descripcion')
    op.drop_column('patrimonio', 'rubro_patrimonial_numero')
