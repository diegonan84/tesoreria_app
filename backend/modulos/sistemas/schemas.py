from pydantic import BaseModel, Field
from typing import Optional

class NotaSalidaRequest(BaseModel):
    numero_inventario: Optional[str] = None
    cantidad: int = 1
    tipo_manual: Optional[str] = None
    marca_manual: Optional[str] = None
    serie_manual: Optional[str] = None
    nombre_apellido: str = Field(..., max_length=150)
    cuil_cuit: str = Field(..., max_length=20)
    motivo: str = Field(..., max_length=255)