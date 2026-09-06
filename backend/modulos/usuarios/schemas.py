from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class CeldaEdit(BaseModel):
    fila: int
    columna: int
    habilitado: bool
    numero_puesto: Optional[str] = ""
    rotacion: int

class MapaGridGuardar(BaseModel):
    titulo: str
    filas: int
    columnas: int
    celdas: List[CeldaEdit]


# --- 1. ESQUEMAS DE SECTORES ---
class SectorBase(BaseModel):
    nombre: str
    color: str = "#1a3644"  # ✨ NUEVO: Color por defecto si no envían nada

class SectorCreate(SectorBase):
    pass

class SectorResponse(SectorBase):
    id: int
    activo: bool

    class Config:
        from_attributes = True

# --- 2. ESQUEMAS DE USUARIOS ---

class UserUpdate(BaseModel):
    nombre: str
    apellido: str
    cuil: str
    email: str
    reparticion: str
    puesto: Optional[str] = None
    roles: List[str]
    sector_id: Optional[int] = None  # <-- Campo opcional agregado aquí

class UserResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    cuil: str
    email: str
    reparticion: str
    puesto: Optional[str] = None
    activo: bool
    roles: str 
    sector_id: Optional[int] = None  # <-- Campo opcional agregado aquí
    sector: Optional[SectorResponse] = None # <-- Permite devolver el nombre del sector al frontend

    class Config:
        from_attributes = True

# --- 3. ESQUEMAS DE SEGURIDAD ---

class PasswordChange(BaseModel):
    clave_actual: str
    nueva_clave: str
    confirmar_clave: str

class PuestoEdit(BaseModel):
    nro_inventario: str
    nombre_equipo: str
    usuario_id: Optional[int] = None

# (Nota: Si tenías otros esquemas en tu archivo original como UserCreate, LoginRequest, etc., 
# puedes dejarlos exactamente como estaban debajo de estos).