from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


class Marcacion(Base):
    """Fichada cruda tal como llega del origen (reloj, archivo exportado o carga manual).
    Es la base de todo el módulo: horas trabajadas, llegadas tarde y ausencias se calculan
    a partir de estas filas cruzadas con el horario de cada empleado."""
    __tablename__ = "rrhh_marcaciones"
    __table_args__ = (
        # Evita duplicar fichadas si se importa dos veces el mismo archivo / período
        UniqueConstraint("identificador", "fecha_hora", name="uq_rrhh_marcacion_ident_fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # Cómo identifica el origen a la persona (legajo, DNI o ID del reloj)
    identificador = Column(String(40), nullable=False, index=True)
    # Usuario del sistema al que corresponde, si se pudo vincular
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    fecha_hora = Column(DateTime, nullable=False, index=True)  # hora local del reloj
    tipo = Column(String(10), nullable=True)                    # ENTRADA | SALIDA | null si el origen no lo indica
    origen = Column(String(20), nullable=False, default="MANUAL")  # RELOJ | ARCHIVO | MANUAL
    dispositivo = Column(String(80), nullable=True)
    cargado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_carga = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("User", foreign_keys=[usuario_id])
