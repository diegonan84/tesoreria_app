from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

CATEGORIAS = ["Hardware", "Software", "Red / Internet", "Impresoras", "Accesos / Usuarios", "Telefonía", "Otro"]
PRIORIDADES = ["Baja", "Media", "Alta", "Urgente"]
ESTADOS = ["Abierto", "En curso", "En espera", "Resuelto", "Cerrado"]

Categoria = Literal["Hardware", "Software", "Red / Internet", "Impresoras", "Accesos / Usuarios", "Telefonía", "Otro"]
Prioridad = Literal["Baja", "Media", "Alta", "Urgente"]
Estado = Literal["Abierto", "En curso", "En espera", "Resuelto", "Cerrado"]


class TicketCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=150)
    descripcion: str = Field(..., min_length=3, max_length=4000)
    categoria: Categoria = "Otro"
    prioridad: Prioridad = "Media"
    numero_inventario: Optional[str] = Field(None, max_length=50)


class TicketPublicoCreate(BaseModel):
    """Alta desde el formulario público (sin login). Nombre y puesto son obligatorios."""
    nombre: str = Field(..., min_length=2, max_length=120)
    puesto: str = Field(..., min_length=1, max_length=120)
    titulo: str = Field(..., min_length=3, max_length=150)
    descripcion: str = Field(..., min_length=3, max_length=4000)
    categoria: Categoria = "Otro"
    # Campo trampa anti-spam: los humanos no lo ven, los bots lo completan
    web: Optional[str] = None


class TicketUpdate(BaseModel):
    """Cambios de gestión. El personal de Soporte puede tocar todo;
    el solicitante solo puede pasar su ticket a 'Cerrado' o reabrirlo."""
    estado: Optional[Estado] = None
    prioridad: Optional[Prioridad] = None
    categoria: Optional[Categoria] = None
    asignado_id: Optional[int] = None
    desasignar: bool = False


class ComentarioCreate(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)
    es_interno: bool = False


class UsuarioMini(BaseModel):
    id: Optional[int] = None  # None = solicitante externo (formulario público)
    nombre: str
    sector: Optional[str] = None


class ComentarioResponse(BaseModel):
    id: int
    texto: str
    tipo: str
    es_interno: bool
    fecha: datetime
    usuario: Optional[UsuarioMini] = None


class TicketResponse(BaseModel):
    id: int
    numero: Optional[str] = None
    titulo: str
    descripcion: str
    categoria: str
    prioridad: str
    estado: str
    numero_inventario: Optional[str] = None
    solicitante_puesto: Optional[str] = None
    origen: str = "sistema"  # sistema | formulario_publico
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    solicitante: Optional[UsuarioMini] = None
    asignado: Optional[UsuarioMini] = None
    cantidad_comentarios: int = 0


class TicketDetalle(TicketResponse):
    comentarios: list[ComentarioResponse] = []
    equipo: Optional[dict] = None
