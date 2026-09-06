from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Sector(Base):
    __tablename__ = "sectores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    color = Column(String, default="#1a3644", nullable=True)
    activo = Column(Boolean, default=True)
    usuarios = relationship("User", back_populates="sector")

class User(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    cuil = Column(String, unique=True, index=True, nullable=False)
    reparticion = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    sector_id = Column(Integer, ForeignKey("sectores.id"), nullable=True)
    sector = relationship("Sector", back_populates="usuarios")
    puesto = Column(String, nullable=True)
    activo = Column(Boolean, default=False)
    roles = Column(String, default="Operador")
    tokens = relationship("PasswordResetToken", back_populates="user")

class MapaGrid(Base):
    __tablename__ = "mapas_grid"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, unique=True, nullable=False)
    filas = Column(Integer, default=5)
    columnas = Column(Integer, default=5)
    celdas = relationship("MapaCelda", back_populates="mapa", cascade="all, delete-orphan")

class MapaCelda(Base):
    __tablename__ = "mapas_celdas"
    id = Column(Integer, primary_key=True, index=True)
    mapa_id = Column(Integer, ForeignKey("mapas_grid.id", ondelete="CASCADE"))
    fila = Column(Integer, nullable=False)
    columna = Column(Integer, nullable=False)
    habilitado = Column(Boolean, default=False)
    numero_puesto = Column(String, nullable=True)
    rotacion = Column(Integer, default=0)
    mapa = relationship("MapaGrid", back_populates="celdas")

# Legacy (Lo dejamos por compatibilidad con código anterior)
class Equipo(Base):
    __tablename__ = "equipos"
    id = Column(Integer, primary_key=True, index=True)
    nro_inventario = Column(String, unique=True, index=True, nullable=False)
    nombre_equipo = Column(String, nullable=False)
    piso = Column(String, nullable=False)
    numero_puesto = Column(String, index=True, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario = relationship("User")