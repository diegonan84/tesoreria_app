from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RecordatorioCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    fecha_evento: datetime
    recordar_antes_min: int = 0

class RecordatorioUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_evento: Optional[datetime] = None
    recordar_antes_min: Optional[int] = None

class RecordatorioResponse(BaseModel):
    id: int
    usuario_id: int
    titulo: str
    descripcion: Optional[str] = None
    fecha_evento: datetime
    recordar_antes_min: int = 0
    visto: bool = False

    class Config:
        from_attributes = True