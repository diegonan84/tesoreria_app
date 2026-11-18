"""rrhh: banco de horas (movimientos por CUIL)

Revision ID: c5e8a1f3b7d2
Revises: b9d4f2a6c8e1
Create Date: 2026-11-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'c5e8a1f3b7d2'
down_revision = 'b9d4f2a6c8e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rrhh_banco_horas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cuil', sa.String(20), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True),
        sa.Column('nombre', sa.String(150), nullable=True),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=True),
        sa.Column('minutos', sa.Integer(), nullable=False),
        sa.Column('detalle', sa.String(255), nullable=True),
        sa.Column('archivo', sa.String(200), nullable=True),
        sa.Column('creado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_rrhh_banco_horas_cuil', 'rrhh_banco_horas', ['cuil'])
    op.create_index('ix_rrhh_banco_horas_usuario_id', 'rrhh_banco_horas', ['usuario_id'])
    op.create_index('ix_rrhh_banco_horas_tipo', 'rrhh_banco_horas', ['tipo'])
    op.create_index('ix_rrhh_banco_horas_fecha', 'rrhh_banco_horas', ['fecha'])


def downgrade() -> None:
    op.drop_table('rrhh_banco_horas')
