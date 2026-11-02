from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
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

# Permisos con los que arranca todo usuario nuevo: plataforma básica + Chat y Calendario.
# Los códigos deben coincidir con CATALOGO_PERMISOS (frontend/js/app.js).
ROLES_POR_DEFECTO = "Operador,Calendario,Cal_Agenda,Chat,Chat_Mensajes"


def roles_con_defecto(roles: str) -> str:
    """Agrega los permisos por defecto a una lista de roles separada por comas."""
    lista = [r.strip() for r in (roles or "").split(",") if r.strip()]
    for r in ROLES_POR_DEFECTO.split(","):
        if r not in lista:
            lista.append(r)
    return ",".join(lista)


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
    # `estado` es la fuente de verdad del ciclo de vida; `activo`/`aprobado` se mantienen
    # sincronizados (ver aplicar_estado) porque muchos módulos filtran por User.activo.
    estado = Column(String(20), default="PENDIENTE", nullable=False, server_default="PENDIENTE")
    activo = Column(Boolean, default=False)
    aprobado = Column(Boolean, default=False)
    fecha_baja = Column(DateTime, nullable=True)
    motivo_baja = Column(String(255), nullable=True)
    roles = Column(String, default=ROLES_POR_DEFECTO)
    foto = Column(Text, nullable=True)
    tokens = relationship("PasswordResetToken", back_populates="user")


# Estados del usuario:
#   PENDIENTE  → se registró solo y espera aprobación de un administrador
#   ACTIVO     → puede ingresar al sistema
#   SUSPENDIDO → inhabilitado temporalmente (licencia, sanción, etc.); conserva bienes y puesto
#   BAJA       → ya no pertenece al organismo; se libera su puesto y opcionalmente sus bienes
ESTADOS_USUARIO = ("PENDIENTE", "ACTIVO", "SUSPENDIDO", "BAJA")


def aplicar_estado(user: "User", estado: str, motivo: str = None):
    """Cambia el estado del usuario manteniendo coherentes los flags legados."""
    user.estado = estado
    user.activo = estado == "ACTIVO"
    user.aprobado = estado != "PENDIENTE"
    if estado in ("SUSPENDIDO", "BAJA"):
        user.fecha_baja = datetime.utcnow()
        user.motivo_baja = motivo
    else:
        user.fecha_baja = None
        user.motivo_baja = None

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