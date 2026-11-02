"""integración WhatsApp: contactos, mensajes, pendientes y origen de tickets

Revision ID: c4e9d1a7b2f8
Revises: b7e2c4d9a1f3
Create Date: 2026-10 (reconstruida el 2026-11-02)

El archivo original de esta revisión se perdió: la base de producción ya la tenía aplicada
pero no estaba en el repositorio. Se reconstruyó a partir del esquema real de esa base para
que la cadena de migraciones vuelva a estar completa. Cada paso verifica si el objeto ya
existe, así que es seguro correrla sobre bases que ya tienen estas tablas.
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4e9d1a7b2f8'
down_revision = 'b7e2c4d9a1f3'
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _tiene_columna(tabla, columna):
    return columna in [c["name"] for c in _insp().get_columns(tabla)]


def upgrade() -> None:
    tablas = _insp().get_table_names()

    if 'whatsapp_contactos' not in tablas:
        op.create_table(
            'whatsapp_contactos',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('telefono', sa.String(20), nullable=False),
            sa.Column('nombre_perfil', sa.String(120), nullable=True),
            sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
            sa.Column('ultimo_mensaje', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_whatsapp_contactos_id', 'whatsapp_contactos', ['id'])
        op.create_index('ix_whatsapp_contactos_telefono', 'whatsapp_contactos', ['telefono'], unique=True)
        op.create_index('ix_whatsapp_contactos_usuario_id', 'whatsapp_contactos', ['usuario_id'])

    if 'whatsapp_pendientes' not in tablas:
        op.create_table(
            'whatsapp_pendientes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('contacto_id', sa.Integer(), sa.ForeignKey('whatsapp_contactos.id'), nullable=False),
            sa.Column('texto', sa.Text(), nullable=False, server_default=''),
            sa.Column('estado', sa.String(20), nullable=False, server_default='Pendiente'),
            sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id'), nullable=True),
            sa.Column('fecha_creacion', sa.DateTime(), nullable=True),
            sa.Column('fecha_actualizacion', sa.DateTime(), nullable=True),
            sa.Column('resuelto_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        )
        op.create_index('ix_whatsapp_pendientes_id', 'whatsapp_pendientes', ['id'])
        op.create_index('ix_whatsapp_pendientes_contacto_id', 'whatsapp_pendientes', ['contacto_id'])
        op.create_index('ix_whatsapp_pendientes_estado', 'whatsapp_pendientes', ['estado'])
        op.create_index('ix_whatsapp_pendientes_fecha_creacion', 'whatsapp_pendientes', ['fecha_creacion'])

    if 'whatsapp_mensajes' not in tablas:
        op.create_table(
            'whatsapp_mensajes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('wa_id', sa.String(128), nullable=True),
            sa.Column('contacto_id', sa.Integer(), sa.ForeignKey('whatsapp_contactos.id'), nullable=False),
            sa.Column('direccion', sa.String(10), nullable=False),
            sa.Column('tipo', sa.String(20), nullable=False, server_default='text'),
            sa.Column('texto', sa.Text(), nullable=True),
            sa.Column('estado_envio', sa.String(20), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('pendiente_id', sa.Integer(), sa.ForeignKey('whatsapp_pendientes.id'), nullable=True),
            sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id'), nullable=True),
            sa.Column('fecha', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_whatsapp_mensajes_id', 'whatsapp_mensajes', ['id'])
        op.create_index('ix_whatsapp_mensajes_contacto_id', 'whatsapp_mensajes', ['contacto_id'])
        op.create_index('ix_whatsapp_mensajes_fecha', 'whatsapp_mensajes', ['fecha'])
        op.create_index('ix_whatsapp_mensajes_wa_id', 'whatsapp_mensajes', ['wa_id'], unique=True)

    # Tickets que llegan por WhatsApp: pueden no tener usuario solicitante
    if not _tiene_columna('tickets', 'origen'):
        op.add_column('tickets', sa.Column('origen', sa.String(20), nullable=False, server_default='web'))
    if not _tiene_columna('tickets', 'contacto_id'):
        op.add_column('tickets', sa.Column('contacto_id', sa.Integer(), nullable=True))
        op.create_foreign_key('tickets_contacto_id_fkey', 'tickets', 'whatsapp_contactos', ['contacto_id'], ['id'])
        op.create_index('ix_tickets_contacto_id', 'tickets', ['contacto_id'])
    if not _tiene_columna('tickets_comentarios', 'origen'):
        op.add_column('tickets_comentarios', sa.Column('origen', sa.String(20), nullable=False, server_default='web'))
    op.alter_column('tickets', 'solicitante_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column('tickets', 'solicitante_id', existing_type=sa.Integer(), nullable=False)
    op.drop_column('tickets_comentarios', 'origen')
    op.drop_index('ix_tickets_contacto_id', table_name='tickets')
    op.drop_constraint('tickets_contacto_id_fkey', 'tickets', type_='foreignkey')
    op.drop_column('tickets', 'contacto_id')
    op.drop_column('tickets', 'origen')
    op.drop_table('whatsapp_mensajes')
    op.drop_table('whatsapp_pendientes')
    op.drop_table('whatsapp_contactos')
