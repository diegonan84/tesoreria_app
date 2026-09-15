from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from backend.database import Base

class RecordatorioCalendario(Base):
    __tablename__ = "agenda_recordatorios"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, index=True, nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_evento = Column(DateTime, index=True, nullable=False)
    recordar_antes_min = Column(Integer, default=0)
    visto = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)