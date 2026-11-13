"""rrhh: franja horaria por día y datos de la planilla de horarios por persona

Revision ID: e3a9c7b5d1f8
Revises: d8b3e5f7a2c4
Create Date: 2026-11-13

"""
from alembic import op
import sqlalchemy as sa

revision = 'e3a9c7b5d1f8'
down_revision = 'd8b3e5f7a2c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('rrhh_home_office', sa.Column('franja', sa.String(80), nullable=True))
    op.add_column('rrhh_home_office', sa.Column('hora_desde', sa.Time(), nullable=True))
    op.add_column('rrhh_home_office', sa.Column('hora_hasta', sa.Time(), nullable=True))
    op.add_column('rrhh_home_office', sa.Column('lugar', sa.String(60), nullable=True))
    op.create_table(
        'rrhh_personal_horario',
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('area', sa.String(80), nullable=True),
        sa.Column('subsector', sa.String(150), nullable=True),
        sa.Column('observacion', sa.Text(), nullable=True),
        sa.Column('color', sa.String(6), nullable=True),
        sa.Column('nombre_planilla', sa.String(150), nullable=True),
        sa.Column('orden', sa.Integer(), nullable=True),
        sa.Column('fecha_importacion', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('rrhh_personal_horario')
    op.drop_column('rrhh_home_office', 'lugar')
    op.drop_column('rrhh_home_office', 'hora_hasta')
    op.drop_column('rrhh_home_office', 'hora_desde')
    op.drop_column('rrhh_home_office', 'franja')
