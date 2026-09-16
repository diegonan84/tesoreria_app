from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from backend.database import Base

class NotaSalida(Base):
    __tablename__ = "notas_salida"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, index=True, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    creador_email = Column(String, nullable=True)
    creador_nombre = Column(String, nullable=True)
    nombre_apellido = Column(String, nullable=False)
    cuil_cuit = Column(String, nullable=False)
    motivo = Column(String, nullable=False)
    numero_inventario = Column(String, nullable=True)
    cantidad = Column(Integer, default=1)
    tipo = Column(String, nullable=True)
    marca = Column(String, nullable=True)
    serie = Column(String, nullable=True)
    archivo_url = Column(String, nullable=True)