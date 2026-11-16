"""rrhh: historial por fechas de los horarios (vigente_desde / vigente_hasta)

Revision ID: a7e2b4c8f6d3
Revises: f4c1d9e6b3a7
Create Date: 2026-11-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'a7e2b4c8f6d3'
down_revision = 'f4c1d9e6b3a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rrhh_horario_historial',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dia_semana', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(12), nullable=False),
        sa.Column('franja', sa.String(80), nullable=True),
        sa.Column('hora_desde', sa.Time(), nullable=True),
        sa.Column('hora_hasta', sa.Time(), nullable=True),
        sa.Column('lugar', sa.String(60), nullable=True),
        sa.Column('vigente_desde', sa.Date(), nullable=False),
        sa.Column('vigente_hasta', sa.Date(), nullable=True),
        sa.Column('modificado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_rrhh_horario_historial_usuario_id', 'rrhh_horario_historial', ['usuario_id'])
    op.create_index('ix_rrhh_horario_historial_vigente_desde', 'rrhh_horario_historial', ['vigente_desde'])
    op.create_index('ix_rrhh_horario_historial_vigente_hasta', 'rrhh_horario_historial', ['vigente_hasta'])
    # Punto de partida: el horario cargado hoy, vigente desde su última modificación
    op.execute("""
        INSERT INTO rrhh_horario_historial
            (usuario_id, dia_semana, tipo, franja, hora_desde, hora_hasta, lugar, vigente_desde, modificado_por_id, fecha_registro)
        SELECT usuario_id, dia_semana, tipo, franja, hora_desde, hora_hasta, lugar,
               CAST(COALESCE(fecha_modificacion, CURRENT_TIMESTAMP) AS DATE), modificado_por_id, CURRENT_TIMESTAMP
        FROM rrhh_home_office
    """)


def downgrade() -> None:
    op.drop_table('rrhh_horario_historial')
