from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


class Ticket(Base):
    """Pedido / incidencia cargado en la Mesa de Ayuda."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, index=True, nullable=True)  # TK-00001 (se completa al crear)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=False)
    categoria = Column(String(50), nullable=False, default="Otro")
    prioridad = Column(String(20), nullable=False, default="Media")
    estado = Column(String(20), nullable=False, default="Abierto", index=True)

    # Equipo afectado (opcional): se cruza con patrimonio.numero_inventario
    numero_inventario = Column(String, nullable=True)

    solicitante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    asignado_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)

    fecha_creacion = Column(DateTime, default=datetime.utcnow, index=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fecha_cierre = Column(DateTime, nullable=True)

    solicitante = relationship("User", foreign_keys=[solicitante_id])
    asignado = relationship("User", foreign_keys=[asignado_id])
    comentarios = relationship(
        "TicketComentario",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketComentario.fecha",
    )


class TicketComentario(Base):
    """Mensajes del hilo del ticket. tipo='sistema' para cambios automáticos
    (estado, asignación); es_interno=True solo lo ve el personal de Soporte."""
    __tablename__ = "tickets_comentarios"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    texto = Column(Text, nullable=False)
    tipo = Column(String(20), nullable=False, default="comentario")  # comentario | sistema
    es_interno = Column(Boolean, default=False)
    fecha = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="comentarios")
    usuario = relationship("User")
