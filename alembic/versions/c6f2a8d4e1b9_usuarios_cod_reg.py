"""usuarios: cod_reg (Cód Reg de RRHH)

Revision ID: c6f2a8d4e1b9
Revises: b4e7c2a9d5f1
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa

revision = 'c6f2a8d4e1b9'
down_revision = 'b4e7c2a9d5f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('cod_reg', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'cod_reg')
