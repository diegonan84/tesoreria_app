from datetime import date, datetime
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
    # Período sin control vigente hoy (propio o general), si hay
    sin_control: Optional[str] = None
    # Franja horaria de cada día (texto de la planilla) y datos de la planilla
    franjas: List[Optional[str]] = [None] * 5
    area: Optional[str] = None
    subsector: Optional[str] = None
    observacion: Optional[str] = None
    cod_reg: Optional[str] = None


class HomeOfficeIn(BaseModel):
    dias: List[Optional[str]]  # null o vacío se toma como CONVOCADO


class HomeOfficeCambio(BaseModel):
    usuario_id: int
    dias: List[Optional[str]]
    # Opcionales: si no vienen, no se tocan. Franja vacía = ese día no tiene horario.
    franjas: Optional[List[Optional[str]]] = None
    observacion: Optional[str] = None


class HomeOfficeLote(BaseModel):
    cambios: List[HomeOfficeCambio]



class PeriodoSinControlIn(BaseModel):
    usuario_id: Optional[int] = None  # null = todo el personal
    desde: date
    hasta: date
    motivo: Optional[str] = None


class PeriodoSinControlOut(PeriodoSinControlIn):
    id: int
    persona: str
    vigente: bool
