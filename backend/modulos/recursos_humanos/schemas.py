from datetime import datetime
from typing import Optional
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
