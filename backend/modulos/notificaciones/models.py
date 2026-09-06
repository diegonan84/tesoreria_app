from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from backend.database import Base 

class NotificacionGlobal(Base):
    __tablename__ = "notificaciones_globales"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    mensaje = Column(String, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # Restauramos quién creó la notificación
    creador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)


class LecturaNotificacion(Base):
    __tablename__ = "lecturas_notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    
    # Restauramos la restricción única (un registro por usuario)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    
    # Restauramos la fecha de la última lectura general
    ultima_lectura = Column(DateTime, default=datetime.utcnow)