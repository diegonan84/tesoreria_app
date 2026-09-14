from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from backend.database import Base

class ManualAyuda(Base):
    __tablename__ = "manuales_ayuda"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    archivo_url = Column(String, nullable=False)
    archivo_nombre = Column(String, nullable=False)
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    fecha_subida = Column(DateTime, default=datetime.utcnow)