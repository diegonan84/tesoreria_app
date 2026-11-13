"""
Lectura de las franjas horarias tal como se escriben en la planilla de RRHH.

Ejemplos que entiende:
    "11 a 18", "9:00 a 16:00", "8.30 A 15.30", "09:30 - 16:30", "10-17", "8a 15",
    "ENTE HU 6 a 12", "Resgistro Civil 9:30 a 16:30", "DGAI 9 A 16",
    "11 a 18 - R", "R: 10 a 17", "R 9 a 16"
Devuelve el lugar (texto antes del horario), hora desde/hasta y si trae la marca "R" (remoto).
"""
import re
from dataclasses import dataclass
from datetime import time
from typing import Optional

_HORA = r"(\d{1,2})(?:\s*[:.,h]\s*(\d{2}))?"
_RANGO = re.compile(_HORA + r"\s*(?:hs\.?)?\s*(?:a|-|–|al|hasta)\s*" + _HORA + r"\s*(?:hs\.?)?", re.I)
# "R" suelta como marca de remoto: al principio ("R:", "R ") o al final ("- R", " R")
_MARCA_R = re.compile(r"(?:^\s*R\s*[:\-.]?\s+|^\s*R\s*:|[\s\-–(]R\)?\s*$|^\s*R\s*$)", re.I)


@dataclass
class Franja:
    texto: str
    lugar: Optional[str] = None
    desde: Optional[time] = None
    hasta: Optional[time] = None
    remoto: bool = False

    @property
    def entendida(self) -> bool:
        return self.desde is not None and self.hasta is not None


def _hora(h: str, m: Optional[str]) -> Optional[time]:
    h, m = int(h), int(m or 0)
    if h == 24 and m == 0:
        return time(23, 59)
    if 0 <= h < 24 and 0 <= m < 60:
        return time(h, m)
    return None


def leer_franja(valor) -> Optional[Franja]:
    """None si la celda está vacía."""
    if valor is None:
        return None
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    if not texto:
        return None
    f = Franja(texto=texto)

    resto = texto
    if _MARCA_R.search(resto):
        f.remoto = True
        resto = _MARCA_R.sub(" ", resto).strip(" -–:")

    m = _RANGO.search(resto)
    if m:
        f.desde = _hora(m.group(1), m.group(2))
        f.hasta = _hora(m.group(3), m.group(4))
        lugar = resto[:m.start()].strip(" -–:,")
        f.lugar = lugar or None
    else:
        f.lugar = resto or None
    return f
