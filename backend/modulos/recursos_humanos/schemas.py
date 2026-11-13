from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MarcacionOut(BaseModel):
    id: int
    identificador: str
    usuario_id: Optional[int] = None
    empleado: Optional[str] = None
    fecha_hora: datetime
    tipo: Optional[str] = None
    origen: str
    dispositivo: Optional[str] = None


class HomeOfficeUsuario(BaseModel):
    usuario_id: int
    apellido: str
    nombre: str
    cuil: str
    sector: Optional[str] = None
    # Un valor por día de lunes a viernes: "HOME" o "CONVOCADO"
    dias: List[str] = ["CONVOCADO"] * 5


class HomeOfficeIn(BaseModel):
    dias: List[Optional[str]]  # null o vacío se toma como CONVOCADO
