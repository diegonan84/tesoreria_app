"""rrhh: días de home office por usuario

Revision ID: a8d3f6b1c9e2
Revises: f1a7c3e9b2d4
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa

revision = 'a8d3f6b1c9e2'
down_revision = 'f1a7c3e9b2d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rrhh_home_office',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dia_semana', sa.Integer(), nullable=False),
        sa.Column('modificado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_modificacion', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('usuario_id', 'dia_semana', name='uq_rrhh_home_office_usuario_dia'),
    )
    op.create_index('ix_rrhh_home_office_usuario_id', 'rrhh_home_office', ['usuario_id'])


def downgrade() -> None:
    op.drop_table('rrhh_home_office')
