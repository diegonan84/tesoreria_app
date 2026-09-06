from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base

class MensajeChat(Base):
    __tablename__ = "mensajes_chat"
    id = Column(Integer, primary_key=True, index=True)
    remitente_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    destinatario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    contenido = Column(String, nullable=False)
    fecha_envio = Column(DateTime(timezone=True), server_default=func.now())
    leido = Column(Boolean, default=False)

class ContactoChat(Base):
    __tablename__ = "chat_contactos"
    id = Column(Integer, primary_key=True, index=True)
    solicitante_id = Column(Integer, index=True)
    receptor_id = Column(Integer, index=True)
    estado = Column(String, default="PENDIENTE")    