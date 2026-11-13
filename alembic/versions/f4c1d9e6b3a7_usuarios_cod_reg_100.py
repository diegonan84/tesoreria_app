"""usuarios: cod_reg pasa a 100 caracteres ("Nueva Carrera Administrativa", "Carrera Gerencial"...)

Revision ID: f4c1d9e6b3a7
Revises: e3a9c7b5d1f8
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa

revision = 'f4c1d9e6b3a7'
down_revision = 'e3a9c7b5d1f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('usuarios', 'cod_reg', existing_type=sa.String(20), type_=sa.String(100), existing_nullable=True)


def downgrade() -> None:
    op.alter_column('usuarios', 'cod_reg', existing_type=sa.String(100), type_=sa.String(20), existing_nullable=True)
