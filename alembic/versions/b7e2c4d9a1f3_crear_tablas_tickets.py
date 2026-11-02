"""crear tablas de mesa de ayuda (tickets)

Revision ID: b7e2c4d9a1f3
Revises: a1b2c3d4e5f6
Create Date: 2026-10-03

"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e2c4d9a1f3'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tickets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('numero', sa.String(), nullable=True),
        sa.Column('titulo', sa.String(150), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=False),
        sa.Column('categoria', sa.String(50), nullable=False, server_default='Otro'),
        sa.Column('prioridad', sa.String(20), nullable=False, server_default='Media'),
        sa.Column('estado', sa.String(20), nullable=False, server_default='Abierto'),
        sa.Column('numero_inventario', sa.String(), nullable=True),
        sa.Column('solicitante_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('asignado_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
        sa.Column('fecha_cierre', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_tickets_id', 'tickets', ['id'])
    op.create_index('ix_tickets_numero', 'tickets', ['numero'], unique=True)
    op.create_index('ix_tickets_estado', 'tickets', ['estado'])
    op.create_index('ix_tickets_solicitante_id', 'tickets', ['solicitante_id'])
    op.create_index('ix_tickets_asignado_id', 'tickets', ['asignado_id'])
    op.create_index('ix_tickets_fecha_creacion', 'tickets', ['fecha_creacion'])

    op.create_table(
        'tickets_comentarios',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False, server_default='comentario'),
        sa.Column('es_interno', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('fecha', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_tickets_comentarios_id', 'tickets_comentarios', ['id'])
    op.create_index('ix_tickets_comentarios_ticket_id', 'tickets_comentarios', ['ticket_id'])


def downgrade() -> None:
    op.drop_index('ix_tickets_comentarios_ticket_id', table_name='tickets_comentarios')
    op.drop_index('ix_tickets_comentarios_id', table_name='tickets_comentarios')
    op.drop_table('tickets_comentarios')
    for ix in ['ix_tickets_fecha_creacion', 'ix_tickets_asignado_id', 'ix_tickets_solicitante_id',
               'ix_tickets_estado', 'ix_tickets_numero', 'ix_tickets_id']:
        op.drop_index(ix, table_name='tickets')
    op.drop_table('tickets')
