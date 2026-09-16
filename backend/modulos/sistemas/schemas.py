from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class NotaSalidaRequest(BaseModel):
    numero_inventario: Optional[str] = None
    cantidad: int = 1
    tipo_manual: Optional[str] = None
    marca_manual: Optional[str] = None
    serie_manual: Optional[str] = None
    nombre_apellido: str = Field(..., max_length=150)
    cuil_cuit: str = Field(..., max_length=20)
    motivo: str = Field(..., max_length=255)

class NotaSalidaResponse(BaseModel):
    id: int
    numero: str
    fecha_creacion: datetime
    creador_email: Optional[str] = None
    creador_nombre: Optional[str] = None
    nombre_apellido: str
    cuil_cuit: str
    motivo: str
    numero_inventario: Optional[str] = None
    cantidad: int = 1
    tipo: Optional[str] = None
    marca: Optional[str] = None
    serie: Optional[str] = None
    archivo_url: Optional[str] = None

    class Config:
        from_attributes = True