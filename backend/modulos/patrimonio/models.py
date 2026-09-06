from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, Text, Column, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
# Reemplaza la siguiente línea con el import real de tu proyecto
from backend.database import Base 

class Patrimonio(Base):
    __tablename__ = "patrimonio"

    numero_inventario: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # --- Campos de la Exportación (Todos Nullable) ---
    institucional: Mapped[str] = mapped_column(String(255), nullable=True)
    cuenta: Mapped[str] = mapped_column(String(255), nullable=True)
    rubro_patrimonial_numero: Mapped[str] = mapped_column(String(50), nullable=True)
    rubro_patrimonial_descripcion: Mapped[str] = mapped_column(String(255), nullable=True)
    estado: Mapped[str] = mapped_column(String(50), nullable=True)
    numero_migrado: Mapped[str] = mapped_column(String(50), nullable=True)
    descripcion_item: Mapped[str] = mapped_column(Text, nullable=True)
    descripcion_bien: Mapped[str] = mapped_column(Text, nullable=True)
    descripcion_detallada = Column(String, nullable=True)
    marca: Mapped[str] = mapped_column(String(255), nullable=True)
    modelo: Mapped[str] = mapped_column(String(255), nullable=True)
    anio: Mapped[str] = mapped_column(String(50), nullable=True)
    serie: Mapped[str] = mapped_column(String(255), nullable=True)
    reparticion: Mapped[str] = mapped_column(String(255), nullable=True)
    usuario: Mapped[str] = mapped_column(String(255), nullable=True) 
    observaciones: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Montos
    monto_original: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    monto_actualizado: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    monto_residual: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)

    # --- NUEVOS CAMPOS INFORMÁTICOS ---
    usuario_destino: Mapped[str] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str] = mapped_column(String(255), nullable=True)
    nombre_de_equipo: Mapped[str] = mapped_column(String(255), nullable=True)
    puesto: Mapped[str] = mapped_column(String(255), nullable=True)
    procesador: Mapped[str] = mapped_column(String(255), nullable=True)
    motherboard: Mapped[str] = mapped_column(String(255), nullable=True)
    memoria: Mapped[str] = mapped_column(String(255), nullable=True)
    disco: Mapped[str] = mapped_column(String(255), nullable=True)
    monitor: Mapped[str] = mapped_column(String(255), nullable=True)
    serie_monitor: Mapped[str] = mapped_column(String(255), nullable=True)
    numero_inventario_monitor: Mapped[str] = mapped_column(String(255), nullable=True)
# ✨ NUEVOS CAMPOS PARA ASIGNACIÓN RELACIONAL ✨
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=True)
    responsable = relationship("User", backref="equipos_asignados")
    # --- Campos de Auditoría y Sistema (Intactos) ---
    fecha_alta: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_modificacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    usuario_modificacion: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relación opcional con el historial
    historial: Mapped[list["PatrimonioHistorial"]] = relationship("PatrimonioHistorial", back_populates="bien_patrimonial", cascade="all, delete-orphan")

class PatrimonioHistorial(Base):
    __tablename__ = "patrimonio_historial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_inventario: Mapped[str] = mapped_column(String(50), ForeignKey("patrimonio.numero_inventario"), nullable=False)
    usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    accion: Mapped[str] = mapped_column(String(50), nullable=False) # ALTA, MODIFICACION, BAJA, IMPORTACION
    campo_modificado: Mapped[str] = mapped_column(String(100), nullable=True)
    valor_anterior: Mapped[str] = mapped_column(Text, nullable=True)
    valor_nuevo: Mapped[str] = mapped_column(Text, nullable=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    observaciones: Mapped[str] = mapped_column(Text, nullable=True)

    bien_patrimonial: Mapped["Patrimonio"] = relationship("Patrimonio", back_populates="historial")


class PatrimonioConcepto(Base):
    __tablename__ = "patrimonio_conceptos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class PatrimonioImportacion(Base):
    __tablename__ = "patrimonio_importaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    cantidad_registros: Mapped[int] = mapped_column(Integer, default=0)
    cantidad_altas: Mapped[int] = mapped_column(Integer, default=0)
    cantidad_modificaciones: Mapped[int] = mapped_column(Integer, default=0)
    cantidad_omitidos: Mapped[int] = mapped_column(Integer, default=0)