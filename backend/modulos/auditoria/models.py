from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base # <--- Ruta corregida

class RegistroAuditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    accion = Column(String, nullable=False)  # Ej: "INICIO_SESION", "CIERRE_SESION"
    detalle = Column(String, nullable=True)  
    
    # --- NUEVOS CAMPOS DE RED Y EQUIPO ---
    ip_address = Column(String, nullable=True)
    pc_nombre = Column(String, nullable=True)
    pc_usuario = Column(String, nullable=True)
    
    fecha = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("User")