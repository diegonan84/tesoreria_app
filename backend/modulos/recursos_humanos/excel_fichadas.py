"""
Reporte "Asistencia biométrico" del sistema de RRHH (Excel)
-----------------------------------------------------------
Una fila por persona y día, con el horario teórico (T), lo fichado (R), las horas trabajadas,
si estaba convocado, la incidencia (licencias, etc.) y el estado que calcula el sistema.
Se busca la hoja cuyo encabezado tenga "Hora Ingreso (T)" y "Cant Horas (R)" (las otras hojas se ignoran).

Alertas (pedido de RRHH, 17/11/2026):
  - Si tiene una incidencia cargada → sin alertas.
  - Convocado = Si:
      * Cant Horas (R) < 7  → "Falta compensar H:MM" (7 - Cant Horas)
      * Ingreso o salida real difieren más de 1 hora del teórico → "Debe realizar cambio de horario"
  - Convocado = No:
      * Cant Horas (R) < 7  → "Error al fichar"
      * Falta la hora de ingreso o de salida real → "Falta algún registro de fichada"
"""
import io
import re
import unicodedata
from datetime import date, datetime, time
from typing import List, Optional

from openpyxl import load_workbook

JORNADA_MIN = 7 * 60
TOLERANCIA_CAMBIO_MIN = 60

ALERTA_COMPENSAR = "FALTA_COMPENSAR"
ALERTA_CAMBIO_HORARIO = "CAMBIO_HORARIO"
ALERTA_ERROR_FICHAR = "ERROR_FICHAR"
ALERTA_FALTA_REGISTRO = "FALTA_REGISTRO"
NOMBRES_ALERTA = {
    ALERTA_COMPENSAR: "Falta compensar horas",
    ALERTA_CAMBIO_HORARIO: "Debe realizar cambio de horario",
    ALERTA_ERROR_FICHAR: "Error al fichar",
    ALERTA_FALTA_REGISTRO: "Falta algún registro de fichada",
}

# Encabezado normalizado → clave interna
_COLUMNAS = {
    "CUIL": "cuil", "NOMBRE Y APELLIDO": "nombre", "REPARTICION": "reparticion", "COD REG": "cod_reg",
    "FECHA": "fecha", "FERIADO": "feriado", "TIPO HORARIO": "tipo_horario", "CONVOCADO": "convocado",
    "HORA INGRESO (T)": "t_ingreso", "HORA SALIDA (T)": "t_salida",
    "DIA INGRESO (R)": "r_dia_ingreso", "HORA INGRESO (R)": "r_ingreso",
    "DIA SALIDA (R)": "r_dia_salida", "HORA SALIDA (R)": "r_salida",
    "CANT HORAS (R)": "cant_horas", "EXIMIDO DE FIRMA": "eximido",
    "INCIDENCIA": "incidencia", "ESTADO INCIDENCIA": "estado_incidencia", "ESTADO": "estado",
}
_OBLIGATORIAS = ("cuil", "fecha", "convocado", "t_ingreso", "t_salida", "r_ingreso", "r_salida", "cant_horas")


def _norm(texto) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "")).encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", texto).strip()


def _texto(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _hora(v) -> Optional[time]:
    if isinstance(v, datetime):
        return v.time().replace(second=0, microsecond=0)
    if isinstance(v, time):
        return v.replace(second=0, microsecond=0)
    m = re.match(r"^\s*(\d{1,2})[:.](\d{2})", str(v or ""))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return time(h, mi) if h < 24 and mi < 60 else None


def _minutos(v) -> Optional[int]:
    """"07:18" → 438. Admite más de 24 h. ":" o vacío → None."""
    if isinstance(v, time):
        return v.hour * 60 + v.minute
    m = re.match(r"^\s*(\d{1,3})[:.](\d{2})", str(v or ""))
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def _fecha(v) -> Optional[date]:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})", str(v or ""))
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def _si(v) -> Optional[bool]:
    s = _norm(v)
    return True if s in ("SI", "S") else False if s in ("NO", "N") else None


def _en_minutos(t: Optional[time]) -> Optional[int]:
    return t.hour * 60 + t.minute if t else None


def hhmm(minutos: int) -> str:
    return f"{minutos // 60}:{minutos % 60:02d}"


def calcular_alertas(fila: dict) -> List[dict]:
    """[{codigo, texto}] según las reglas de RRHH (ver docstring del módulo)."""
    if fila.get("incidencia"):
        return []
    alertas = []
    horas = fila.get("cant_horas_min") or 0
    if fila.get("convocado"):
        if horas < JORNADA_MIN:
            alertas.append({"codigo": ALERTA_COMPENSAR, "texto": f"Falta compensar {hhmm(JORNADA_MIN - horas)} h"})
        difs = []
        for t, r in (("t_ingreso", "r_ingreso"), ("t_salida", "r_salida")):
            a, b = _en_minutos(fila.get(t)), _en_minutos(fila.get(r))
            if a is not None and b is not None:
                difs.append(abs(a - b))
        if any(d > TOLERANCIA_CAMBIO_MIN for d in difs):
            alertas.append({"codigo": ALERTA_CAMBIO_HORARIO, "texto": "Debe realizar cambio de horario"})
    else:
        if horas < JORNADA_MIN:
            alertas.append({"codigo": ALERTA_ERROR_FICHAR, "texto": "Error al fichar"})
        if not fila.get("r_ingreso") or not fila.get("r_salida"):
            alertas.append({"codigo": ALERTA_FALTA_REGISTRO, "texto": "Falta algún registro de fichada"})
    return alertas


def leer(contenido: bytes) -> dict:
    """{"hoja", "filas": [...], "avisos": [...], "desde", "hasta"}"""
    wb = load_workbook(io.BytesIO(contenido), data_only=True)
    for ws in wb.worksheets:
        for fila_enc in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 40)):
            cols = {}
            for c in fila_enc:
                clave = _COLUMNAS.get(_norm(c.value).replace(".", ""))
                if clave and clave not in cols:
                    cols[clave] = c.column - 1
            if all(k in cols for k in _OBLIGATORIAS):
                return _leer_hoja(ws, fila_enc[0].row, cols)
    raise ValueError("No encontré la hoja de asistencia: tiene que tener las columnas Cuil, Fecha, Convocado, "
                     "Hora Ingreso (T), Hora Salida (T), Hora Ingreso (R), Hora Salida (R) y Cant Horas (R).")


def _leer_hoja(ws, fila_encabezado: int, cols: dict) -> dict:
    filas, avisos = [], []
    for nro, valores in enumerate(ws.iter_rows(min_row=fila_encabezado + 1, values_only=True), start=fila_encabezado + 1):
        v = lambda k: valores[cols[k]] if k in cols and cols[k] < len(valores) else None
        cuil = _texto(v("cuil"))
        if not cuil:
            continue
        fecha = _fecha(v("fecha"))
        if not fecha:
            avisos.append(f"Fila {nro} ({_texto(v('nombre'))}): no tiene una fecha válida, se saltea.")
            continue
        fila = {
            "fila": nro, "cuil": cuil, "nombre": _texto(v("nombre")) or "", "reparticion": _texto(v("reparticion")),
            "cod_reg": _texto(v("cod_reg")), "fecha": fecha, "feriado": _si(v("feriado")) or False,
            "tipo_horario": _texto(v("tipo_horario")), "convocado": _si(v("convocado")),
            "t_ingreso": _hora(v("t_ingreso")), "t_salida": _hora(v("t_salida")),
            "r_ingreso": _hora(v("r_ingreso")), "r_salida": _hora(v("r_salida")),
            "cant_horas_min": _minutos(v("cant_horas")), "eximido": _si(v("eximido")) or False,
            "incidencia": _texto(v("incidencia")), "estado_incidencia": _texto(v("estado_incidencia")),
            "estado": (_texto(v("estado")) or "").rstrip(".") or None,
        }
        if fila["convocado"] is None:
            avisos.append(f"Fila {nro} ({fila['nombre']}): Convocado no es Si ni No; se toma como No.")
            fila["convocado"] = False
        fila["alertas"] = calcular_alertas(fila)
        filas.append(fila)
    fechas = [f["fecha"] for f in filas]
    return {"hoja": ws.title, "filas": filas, "avisos": avisos,
            "desde": min(fechas) if fechas else None, "hasta": max(fechas) if fechas else None}
