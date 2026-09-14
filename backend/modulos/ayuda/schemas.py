from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ManualAyudaResponse(BaseModel):
    id: int
    titulo: str
    descripcion: Optional[str] = None
    archivo_url: str
    archivo_nombre: str
    fecha_subida: Optional[datetime] = None

    class Config:
        from_attributes = True

class ManualAyudaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None