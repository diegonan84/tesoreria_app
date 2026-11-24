"""
Reporte "Asistencia biométrico" del sistema de RRHH (Excel)
-----------------------------------------------------------
Una fila por persona y día, con el horario teórico (T), lo fichado (R), las horas trabajadas,
si estaba convocado, la incidencia (licencias, etc.) y el estado que calcula el sistema.
Se busca la hoja cuyo encabezado tenga "Hora Ingreso (T)" y "Cant Horas (R)" (las otras hojas se ignoran).

Alertas (pedido de RRHH, 17/11/2026):
  - Si tiene una incidencia cargada → sin alertas.
  - Con 7 h o más no hay alerta de horas (falta compensar / error al fichar), pero si el ingreso
    o la salida difieren más de 1 h del teórico igual sale "Debe realizar cambio de horario" (18/11/2026).
  - Convocado = Si:
      * Cant Horas (R) < 7  → "Debe N minutos" / "Debe 1 hora y 30 minutos" (7 - Cant Horas), y nada más
      * Con 7 h o más: ingreso o salida real difieren más de 1 hora del teórico →
          - si entró antes y/o salió después (no entró tarde ni salió antes, tolerancia 15 min)
            → "Hizo N de más" (no suma al banco, pero compensa deuda)
          - si no → "Debe realizar cambio de horario"
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
ALERTA_HORAS_DE_MAS = "HORAS_DE_MAS"
# Para decidir si la diferencia con el teórico es por quedarse de más (y no un cambio de horario):
# entrar hasta 15 min tarde o salir hasta 15 min antes se considera "en horario".
TOLERANCIA_PUNTUAL_MIN = 15
NOMBRES_ALERTA = {
    ALERTA_HORAS_DE_MAS: "Hizo horas de más",
    ALERTA_COMPENSAR: "Hizo menos de 7 horas",
    ALERTA_CAMBIO_HORARIO: "Debe realizar cambio de horario",
    ALERTA_ERROR_FICHAR: "Error al fichar",
    ALERTA_FALTA_REGISTRO: "Falta algún registro de fichada",
}

# Encabezado normalizado → clave interna
# Cód Reg que no se controlan (pedido de RRHH, 18/11/2026). Se compara sin tildes ni mayúsculas.
COD_REG_SIN_CONTROL = {"AUTORIDADES SUPERIORES", "EXTERNO"}


def cod_reg_sin_control(*valores) -> Optional[str]:
    """Devuelve el Cód Reg que excluye del control (del Excel o del usuario), o None."""
    for v in valores:
        if v and _norm(v) in COD_REG_SIN_CONTROL:
            return v
    return None


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


def duracion(minutos: int) -> str:
    """45 → "45 minutos", 60 → "1 hora", 90 → "1 hora y 30 minutos", 133 → "2 horas y 13 minutos"."""
    h, m = divmod(minutos, 60)
    texto_m = f"{m} minuto{'s' if m != 1 else ''}"
    if h == 0:
        return texto_m
    texto_h = f"{h} hora{'s' if h != 1 else ''}"
    return texto_h if m == 0 else f"{texto_h} y {texto_m}"


def _desvios(fila: dict):
    """(minutos que entró tarde, minutos que salió tarde) respecto del teórico; negativos = antes."""
    def d(r, t):
        a, b = _en_minutos(fila.get(r)), _en_minutos(fila.get(t))
        return None if a is None or b is None else a - b
    return d("r_ingreso", "t_ingreso"), d("r_salida", "t_salida")


def _se_quedo_de_mas(d_in: Optional[int], d_out: Optional[int]) -> bool:
    """True si no entró tarde ni salió antes (más allá de la tolerancia): la jornada se estiró, no se corrió."""
    return (d_in is None or d_in <= TOLERANCIA_PUNTUAL_MIN) and (d_out is None or d_out >= -TOLERANCIA_PUNTUAL_MIN)


def minutos_de_mas(fila: dict) -> int:
    """Minutos trabajados por encima de las 7 h (convocado, sin incidencia); sirven para compensar deuda."""
    if fila.get("incidencia") or not fila.get("convocado"):
        return 0
    return max(0, (fila.get("cant_horas_min") or 0) - JORNADA_MIN)


def calcular_alertas(fila: dict) -> List[dict]:
    """[{codigo, texto}] según las reglas de RRHH (ver docstring del módulo)."""
    if fila.get("incidencia"):
        return []
    alertas = []
    horas = fila.get("cant_horas_min") or 0
    if fila.get("convocado"):
        # Menos de 7 h: solo se avisa lo que debe (aunque además difiera el horario)
        if horas < JORNADA_MIN:
            alertas.append({"codigo": ALERTA_COMPENSAR, "texto": f"Debe {duracion(JORNADA_MIN - horas)}"})
            return alertas
        d_in, d_out = _desvios(fila)
        difs = [abs(d) for d in (d_in, d_out) if d is not None]
        if any(d > TOLERANCIA_CAMBIO_MIN for d in difs):
            if _se_quedo_de_mas(d_in, d_out) and horas > JORNADA_MIN:
                # Cumplió y la diferencia es porque entró antes y/o salió después: no es un cambio de horario
                alertas.append({"codigo": ALERTA_HORAS_DE_MAS, "texto": f"Hizo {duracion(horas - JORNADA_MIN)} de más"})
            else:
                alertas.append({"codigo": ALERTA_CAMBIO_HORARIO, "texto": "Debe realizar cambio de horario"})
    else:
        if horas < JORNADA_MIN:
            alertas.append({"codigo": ALERTA_ERROR_FICHAR, "texto": "Error al fichar"})
        if not fila.get("r_ingreso") or not fila.get("r_salida"):
            alertas.append({"codigo": ALERTA_FALTA_REGISTRO, "texto": "Falta algún registro de fichada"})
    return alertas


def _diferencia(real: Optional[time], teorico: Optional[time], que: str) -> Optional[str]:
    a, b = _en_minutos(real), _en_minutos(teorico)
    if a is None or b is None or a == b:
        return None
    dif = a - b
    if que == "ingreso":
        return f"entró {hhmm(abs(dif))} h {'tarde' if dif > 0 else 'antes'}"
    return f"salió {hhmm(abs(dif))} h {'después' if dif > 0 else 'antes'}"


def detalle_alerta(codigo: str, fila: dict) -> str:
    """Explicación de la alerta con los datos del día (para el listado de alertas)."""
    h = lambda t: t.strftime("%H:%M") if t else "—"
    horas = fila.get("cant_horas_min")
    trabajadas = hhmm(horas) if horas is not None else "0:00"
    teorico = f"Teórico {h(fila.get('t_ingreso'))} a {h(fila.get('t_salida'))}"
    real = f"real {h(fila.get('r_ingreso'))} a {h(fila.get('r_salida'))}"
    if codigo == ALERTA_COMPENSAR:
        falta = duracion(JORNADA_MIN - (horas or 0))
        if not fila.get("r_ingreso") and not fila.get("r_salida"):
            return f"No registró fichadas; debe {falta} de la jornada de 7 horas."
        return f"Hizo menos de 7 horas: trabajó {trabajadas} h y debe {falta} ({teorico}, {real})."
    if codigo == ALERTA_CAMBIO_HORARIO:
        partes = []
        for que, r, t in (("ingreso", "r_ingreso", "t_ingreso"), ("salida", "r_salida", "t_salida")):
            d = _diferencia(fila.get(r), fila.get(t), que)
            a, b = _en_minutos(fila.get(r)), _en_minutos(fila.get(t))
            if d and a is not None and b is not None and abs(a - b) > TOLERANCIA_CAMBIO_MIN:
                partes.append(d)
        return f"{teorico}, {real}: " + " y ".join(partes) + " (más de 1 h de diferencia)."
    if codigo == ALERTA_HORAS_DE_MAS:
        partes = [p for p in (_diferencia(fila.get("r_ingreso"), fila.get("t_ingreso"), "ingreso"),
                              _diferencia(fila.get("r_salida"), fila.get("t_salida"), "salida")) if p]
        extra = duracion(max(0, (horas or 0) - JORNADA_MIN))
        return (f"Cumplió la jornada: trabajó {trabajadas} h, {extra} de más ({teorico}, {real}: {' y '.join(partes)}). "
                "No suma al banco de horas, pero compensa lo que deba.")
    if codigo == ALERTA_ERROR_FICHAR:
        return f"No convocado: registró {trabajadas} h, menos de las 7:00 h ({real})."
    if codigo == ALERTA_FALTA_REGISTRO:
        faltan = [n for n, k in (("ingreso", "r_ingreso"), ("salida", "r_salida")) if not fila.get(k)]
        return f"Falta la fichada de {' y '.join(faltan)}."
    return ""


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
