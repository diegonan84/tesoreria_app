"""crear tablas de Agenda (recordatorios) y Notas de salida

Revision ID: d2a6f9c3e8b1
Revises: c3f8a2e1d7b4
Create Date: 2026-11-02

Estos módulos se agregaron sin migración; en bases creadas con create_all ya existen,
por eso cada tabla se crea solo si falta.
"""
from alembic import op
import sqlalchemy as sa

revision = 'd2a6f9c3e8b1'
down_revision = 'c3f8a2e1d7b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    tablas = sa.inspect(op.get_bind()).get_table_names()

    if 'agenda_recordatorios' not in tablas:
        op.create_table(
            'agenda_recordatorios',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('usuario_id', sa.Integer(), nullable=False),
            sa.Column('titulo', sa.String(), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('fecha_evento', sa.DateTime(), nullable=False),
            sa.Column('recordar_antes_min', sa.Integer(), nullable=True),
            sa.Column('visto', sa.Boolean(), nullable=True),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_agenda_recordatorios_id', 'agenda_recordatorios', ['id'])
        op.create_index('ix_agenda_recordatorios_usuario_id', 'agenda_recordatorios', ['usuario_id'])
        op.create_index('ix_agenda_recordatorios_fecha_evento', 'agenda_recordatorios', ['fecha_evento'])

    if 'notas_salida' not in tablas:
        op.create_table(
            'notas_salida',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('numero', sa.String(), nullable=False),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
            sa.Column('creador_email', sa.String(), nullable=True),
            sa.Column('creador_nombre', sa.String(), nullable=True),
            sa.Column('nombre_apellido', sa.String(), nullable=False),
            sa.Column('cuil_cuit', sa.String(), nullable=False),
            sa.Column('motivo', sa.String(), nullable=False),
            sa.Column('numero_inventario', sa.String(), nullable=True),
            sa.Column('cantidad', sa.Integer(), nullable=True),
            sa.Column('tipo', sa.String(), nullable=True),
            sa.Column('marca', sa.String(), nullable=True),
            sa.Column('serie', sa.String(), nullable=True),
            sa.Column('archivo_url', sa.String(), nullable=True),
        )
        op.create_index('ix_notas_salida_id', 'notas_salida', ['id'])
        op.create_index('ix_notas_salida_numero', 'notas_salida', ['numero'], unique=True)


def downgrade() -> None:
    op.drop_table('notas_salida')
    op.drop_table('agenda_recordatorios')
