from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# --------------------------------------------------
# CONCEPTOS
# --------------------------------------------------
class PatrimonioConceptoBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    activo: bool = True

class PatrimonioConceptoCreate(PatrimonioConceptoBase):
    pass

class PatrimonioConceptoResponse(PatrimonioConceptoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --------------------------------------------------
# HISTORIAL
# --------------------------------------------------
class PatrimonioHistorialResponse(BaseModel):
    id: int
    numero_inventario: str
    usuario: str
    fecha: datetime
    accion: str
    campo_modificado: Optional[str] = None
    valor_anterior: Optional[str] = None
    valor_nuevo: Optional[str] = None
    ip: str
    observaciones: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --------------------------------------------------
# PATRIMONIO (BIENES) - ACTUALIZADO AL NUEVO FORMATO
# --------------------------------------------------
class PatrimonioBase(BaseModel):
    numero_inventario: str = Field(..., max_length=50)
    institucional: Optional[str] = Field(None, max_length=255) 
    cuenta: Optional[str] = Field(None, max_length=255) 
    rubro_patrimonial_numero: Optional[str] = Field(None, max_length=50)
    rubro_patrimonial_descripcion: Optional[str] = Field(None, max_length=255)
    estado: Optional[str] = Field(None, max_length=50)
    numero_migrado: Optional[str] = Field(None, max_length=50)
    descripcion_item: Optional[str] = None
    descripcion_bien: Optional[str] = None
    descripcion_detallada: Optional[str] = None
    marca: Optional[str] = Field(None, max_length=255) 
    modelo: Optional[str] = Field(None, max_length=255)
    anio: Optional[str] = Field(None, max_length=50) 
    serie: Optional[str] = Field(None, max_length=255) 
    reparticion: Optional[str] = Field(None, max_length=255) 
    usuario: Optional[str] = Field(None, max_length=255) 
    observaciones: Optional[str] = None
    monto_original: Optional[Decimal] = None
    monto_actualizado: Optional[Decimal] = None
    monto_residual: Optional[Decimal] = None
    activo: bool = True
    
    # --- NUEVOS CAMPOS INFORMÁTICOS ---
    usuario_destino: Optional[str] = Field(None, max_length=255)
    tipo: Optional[str] = Field(None, max_length=255)
    nombre_de_equipo: Optional[str] = Field(None, max_length=255)
    puesto: Optional[str] = Field(None, max_length=255)
    procesador: Optional[str] = Field(None, max_length=255)
    motherboard: Optional[str] = Field(None, max_length=255)
    memoria: Optional[str] = Field(None, max_length=255)
    disco: Optional[str] = Field(None, max_length=255)
    monitor: Optional[str] = Field(None, max_length=255)
    serie_monitor: Optional[str] = Field(None, max_length=255)
    numero_inventario_monitor: Optional[str] = Field(None, max_length=255)

class PatrimonioCreate(PatrimonioBase):
    # Agregamos la cantidad para el alta en lote (por defecto 1, mínimo 1)
    cantidad: int = Field(default=1, ge=1)

class PatrimonioUpdate(BaseModel):
    # Todos los campos opcionales. El numero_inventario NUNCA se incluye aquí por regla de negocio.
    institucional: Optional[str] = Field(None, max_length=255)
    cuenta: Optional[str] = Field(None, max_length=255)
    rubro_patrimonial_numero: Optional[str] = Field(None, max_length=50)
    rubro_patrimonial_descripcion: Optional[str] = Field(None, max_length=255)
    estado: Optional[str] = Field(None, max_length=50)
    numero_migrado: Optional[str] = Field(None, max_length=50)
    descripcion_item: Optional[str] = None
    descripcion_bien: Optional[str] = None
    descripcion_detallada: Optional[str] = None
    marca: Optional[str] = Field(None, max_length=255) 
    modelo: Optional[str] = Field(None, max_length=255) 
    anio: Optional[str] = Field(None, max_length=50)
    serie: Optional[str] = Field(None, max_length=255) 
    reparticion: Optional[str] = Field(None, max_length=255) 
    usuario: Optional[str] = Field(None, max_length=255) 
    observaciones: Optional[str] = None
    monto_original: Optional[Decimal] = None
    monto_actualizado: Optional[Decimal] = None
    monto_residual: Optional[Decimal] = None
    activo: Optional[bool] = None
    
    # --- NUEVOS CAMPOS INFORMÁTICOS ---
    usuario_destino: Optional[str] = Field(None, max_length=255)
    tipo: Optional[str] = Field(None, max_length=255)
    nombre_de_equipo: Optional[str] = Field(None, max_length=255)
    puesto: Optional[str] = Field(None, max_length=255)
    procesador: Optional[str] = Field(None, max_length=255)
    motherboard: Optional[str] = Field(None, max_length=255)
    memoria: Optional[str] = Field(None, max_length=255)
    disco: Optional[str] = Field(None, max_length=255)
    monitor: Optional[str] = Field(None, max_length=255)
    serie_monitor: Optional[str] = Field(None, max_length=255)
    numero_inventario_monitor: Optional[str] = Field(None, max_length=255)

class PatrimonioResponse(PatrimonioBase):
    fecha_alta: datetime
    fecha_modificacion: datetime
    usuario_modificacion: str
    model_config = ConfigDict(from_attributes=True)

class AsignarEquipoRequest(BaseModel):
    usuario_id: Optional[int] = None
    puesto: Optional[str] = None    