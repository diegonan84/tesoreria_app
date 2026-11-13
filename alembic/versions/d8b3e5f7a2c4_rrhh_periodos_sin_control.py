"""rrhh: períodos sin control de Home / Convocado

Revision ID: d8b3e5f7a2c4
Revises: c6f2a8d4e1b9
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa

revision = 'd8b3e5f7a2c4'
down_revision = 'c6f2a8d4e1b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rrhh_periodos_sin_control',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=True),
        sa.Column('desde', sa.Date(), nullable=False),
        sa.Column('hasta', sa.Date(), nullable=False),
        sa.Column('motivo', sa.String(150), nullable=True),
        sa.Column('creado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_rrhh_periodos_sin_control_usuario_id', 'rrhh_periodos_sin_control', ['usuario_id'])
    op.create_index('ix_rrhh_periodos_sin_control_desde', 'rrhh_periodos_sin_control', ['desde'])
    op.create_index('ix_rrhh_periodos_sin_control_hasta', 'rrhh_periodos_sin_control', ['hasta'])


def downgrade() -> None:
    op.drop_table('rrhh_periodos_sin_control')
