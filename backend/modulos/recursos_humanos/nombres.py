"""
Vincular "APELLIDO,NOMBRES (G.O.)" de la planilla de RRHH con los usuarios del sistema.
La planilla no trae CUIL, así que se compara por las palabras del apellido y los nombres.
"""
import re
import unicodedata
from typing import Iterable, List, Optional, Tuple

# Palabras que no son parte del nombre (cargos o siglas entre paréntesis ya se quitan aparte)
_IGNORAR = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "DR", "DRA", "LIC", "CDOR", "CDORA", "ING", "SR", "SRA"}


def normalizar(texto) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "")).encode("ascii", "ignore").decode().upper()
    texto = re.sub(r"\([^)]*\)", " ", texto)          # (G.O.), (SGO), (S.G.O.)
    texto = re.sub(r"[^A-Z ]", " ", texto)            # comas, puntos, guiones, números
    return re.sub(r"\s+", " ", texto).strip()


def palabras(texto) -> frozenset:
    return frozenset(p for p in normalizar(texto).split() if len(p) > 1 and p not in _IGNORAR)


def separar_apellido_nombre(texto) -> Tuple[str, str]:
    """"PEREZ,JUAN CARLOS (G.O.)" → ("PEREZ", "JUAN CARLOS"). Sin coma, todo va al apellido."""
    limpio = re.sub(r"\([^)]*\)", " ", str(texto or ""))
    if "," in limpio:
        apellido, nombre = limpio.split(",", 1)
    else:
        apellido, nombre = limpio, ""
    return re.sub(r"\s+", " ", apellido).strip(), re.sub(r"\s+", " ", nombre).strip()


def vincular(texto, usuarios: Iterable) -> Tuple[Optional[object], List[object]]:
    """Devuelve (usuario, candidatos).
    - usuario: el único que coincide con seguridad, o None.
    - candidatos: posibles coincidencias cuando no hay una sola segura (para elegir a mano)."""
    buscado = palabras(texto)
    if not buscado:
        return None, []
    usuarios = list(usuarios)
    claves = [(u, palabras(f"{u.apellido} {u.nombre}")) for u in usuarios]

    exactos = [u for u, c in claves if c == buscado]
    if len(exactos) == 1:
        return exactos[0], []
    if len(exactos) > 1:
        return None, exactos

    # Uno contiene al otro: "PEREZ, JUAN" contra "Pérez, Juan Carlos" (o al revés). Mínimo 2 palabras en común.
    incluidos = [u for u, c in claves if len(c & buscado) >= 2 and (c <= buscado or buscado <= c)]
    if len(incluidos) == 1:
        return incluidos[0], []
    if incluidos:
        return None, incluidos

    # Sugerencias: comparten el apellido completo y al menos una palabra del nombre
    apellido, _ = separar_apellido_nombre(texto)
    pal_apellido = palabras(apellido)
    sugeridos = [u for u, c in claves if pal_apellido and pal_apellido <= c and len(c & buscado) > len(pal_apellido)]
    if not sugeridos:
        sugeridos = [u for u, c in claves if pal_apellido and pal_apellido <= c]
    return None, sugeridos[:5]
