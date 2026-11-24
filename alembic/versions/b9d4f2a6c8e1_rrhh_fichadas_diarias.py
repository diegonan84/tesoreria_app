"""rrhh: archivos de fichadas importados y asistencia diaria con alertas

Revision ID: b9d4f2a6c8e1
Revises: a7e2b4c8f6d3
Create Date: 2026-11-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'b9d4f2a6c8e1'
down_revision = 'a7e2b4c8f6d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rrhh_fichadas_archivos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('hash_sha256', sa.String(64), nullable=False),
        sa.Column('desde', sa.Date(), nullable=True),
        sa.Column('hasta', sa.Date(), nullable=True),
        sa.Column('filas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('subido_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_subida', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_rrhh_fichadas_archivos_hash_sha256', 'rrhh_fichadas_archivos', ['hash_sha256'], unique=True)
    op.create_table(
        'rrhh_fichadas_diarias',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('archivo_id', sa.Integer(), sa.ForeignKey('rrhh_fichadas_archivos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cuil', sa.String(20), nullable=False),
        sa.Column('nombre', sa.String(150), nullable=False),
        sa.Column('reparticion', sa.String(150), nullable=True),
        sa.Column('cod_reg', sa.String(100), nullable=True),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('feriado', sa.Boolean(), nullable=True),
        sa.Column('tipo_horario', sa.String(80), nullable=True),
        sa.Column('convocado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('teorico_ingreso', sa.Time(), nullable=True),
        sa.Column('teorico_salida', sa.Time(), nullable=True),
        sa.Column('real_ingreso', sa.Time(), nullable=True),
        sa.Column('real_salida', sa.Time(), nullable=True),
        sa.Column('horas_min', sa.Integer(), nullable=True),
        sa.Column('eximido', sa.Boolean(), nullable=True),
        sa.Column('incidencia', sa.String(40), nullable=True),
        sa.Column('estado_incidencia', sa.String(150), nullable=True),
        sa.Column('estado', sa.String(120), nullable=True),
        sa.Column('alertas', sa.Text(), nullable=True),
        sa.Column('fecha_carga', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('cuil', 'fecha', name='uq_rrhh_fichada_cuil_fecha'),
    )
    op.create_index('ix_rrhh_fichadas_diarias_archivo_id', 'rrhh_fichadas_diarias', ['archivo_id'])
    op.create_index('ix_rrhh_fichadas_diarias_usuario_id', 'rrhh_fichadas_diarias', ['usuario_id'])
    op.create_index('ix_rrhh_fichadas_diarias_cuil', 'rrhh_fichadas_diarias', ['cuil'])
    op.create_index('ix_rrhh_fichadas_diarias_fecha', 'rrhh_fichadas_diarias', ['fecha'])


def downgrade() -> None:
    op.drop_table('rrhh_fichadas_diarias')
    op.drop_table('rrhh_fichadas_archivos')
