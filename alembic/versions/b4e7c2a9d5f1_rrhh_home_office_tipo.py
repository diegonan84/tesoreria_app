"""rrhh: cada día del tablero se marca como HOME o CONVOCADO

Revision ID: b4e7c2a9d5f1
Revises: a8d3f6b1c9e2
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa

revision = 'b4e7c2a9d5f1'
down_revision = 'a8d3f6b1c9e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Las filas existentes eran días de home office
    op.add_column('rrhh_home_office', sa.Column('tipo', sa.String(12), nullable=False, server_default='HOME'))


def downgrade() -> None:
    op.execute("DELETE FROM rrhh_home_office WHERE tipo <> 'HOME'")
    op.drop_column('rrhh_home_office', 'tipo')
