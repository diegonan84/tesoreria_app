"""rrhh: tabla de marcaciones (fichadas crudas)

Revision ID: f1a7c3e9b2d4
Revises: d9e4b7a2c1f5
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a7c3e9b2d4'
down_revision = 'd9e4b7a2c1f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rrhh_marcaciones',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('identificador', sa.String(40), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_hora', sa.DateTime(), nullable=False),
        sa.Column('tipo', sa.String(10), nullable=True),
        sa.Column('origen', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('dispositivo', sa.String(80), nullable=True),
        sa.Column('cargado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_carga', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('identificador', 'fecha_hora', name='uq_rrhh_marcacion_ident_fecha'),
    )
    op.create_index('ix_rrhh_marcaciones_id', 'rrhh_marcaciones', ['id'])
    op.create_index('ix_rrhh_marcaciones_identificador', 'rrhh_marcaciones', ['identificador'])
    op.create_index('ix_rrhh_marcaciones_usuario_id', 'rrhh_marcaciones', ['usuario_id'])
    op.create_index('ix_rrhh_marcaciones_fecha_hora', 'rrhh_marcaciones', ['fecha_hora'])


def downgrade() -> None:
    op.drop_table('rrhh_marcaciones')
