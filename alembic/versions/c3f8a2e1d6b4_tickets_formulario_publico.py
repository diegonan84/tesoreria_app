"""tickets: formulario público (correo y puesto del solicitante, solicitante_id opcional)

Revision ID: c3f8a2e1d6b4
Revises: b7e2c4d9a1f3
Create Date: 2026-11-03

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3f8a2e1d6b4'
down_revision = 'b7e2c4d9a1f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('solicitante_email', sa.String(160), nullable=True))
    op.add_column('tickets', sa.Column('solicitante_puesto', sa.String(120), nullable=True))
    op.alter_column('tickets', 'solicitante_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column('tickets', 'solicitante_id', existing_type=sa.Integer(), nullable=False)
    op.drop_column('tickets', 'solicitante_puesto')
    op.drop_column('tickets', 'solicitante_email')
