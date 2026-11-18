"""
Excel de saldo inicial del banco de horas
-----------------------------------------
Una fila por persona. Se busca (en cualquier hoja, en las primeras 20 filas) un encabezado con
una columna CUIL y una columna de horas. Columnas de horas que se reconocen:
  - "DEBE" / "HORAS ADEUDADAS" / "ADEUDA" / "FALTANTE": horas que la persona debe (siempre deuda)
  - "SALDO" / "BANCO" / "HORAS" / "SALDO INICIAL": saldo con signo (negativo = debe, positivo = a favor)
Valores admitidos: "3:50", "-3:50", "03:50:00", 3.5 (horas decimales), una hora de Excel (0,1597…)
o un número entero de minutos si la columna dice "MIN".
"""
import io
import re
import unicodedata
from datetime import datetime, time, timedelta
from typing import Optional

from openpyxl import load_workbook

_COLS_DEUDA = ("DEBE", "HORAS ADEUDADAS", "ADEUDA", "ADEUDADAS", "FALTANTE", "FALTANTES", "DEUDA")
_COLS_SALDO = ("SALDO", "SALDO INICIAL", "BANCO", "BANCO DE HORAS", "HORAS", "SALDO HORAS")


def _norm(texto) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "")).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9 ]", " ", re.sub(r"\s+", " ", texto)).strip()


def _a_minutos(v, en_minutos: bool) -> Optional[int]:
    """Valor de la celda → minutos con signo (None si está vacía o no se entiende)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, timedelta):
        return round(v.total_seconds() / 60)
    if isinstance(v, datetime):
        v = v.time()
    if isinstance(v, time):
        return v.hour * 60 + v.minute
    if isinstance(v, (int, float)):
        if en_minutos:
            return round(v)
        # Excel guarda las horas como fracción de día (0,16 = 3:50); números mayores son horas decimales
        return round(v * 24 * 60) if abs(v) < 1 else round(v * 60)
    s = str(v).strip().replace(",", ".")
    m = re.match(r"^([+-]?)\s*(\d{1,4})\s*[:h]\s*(\d{1,2})", s, re.I)
    if m:
        total = int(m.group(2)) * 60 + int(m.group(3))
        return -total if m.group(1) == "-" else total
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)$", s)
    if m:
        return round(float(m.group(1))) if en_minutos else round(float(m.group(1)) * 60)
    return None


def leer(contenido: bytes) -> dict:
    """{"filas": [{fila, cuil, nombre, minutos}], "avisos": [], "columna": str, "modo": "DEUDA"|"SALDO"}
    minutos: saldo con signo (negativo = debe)."""
    wb = load_workbook(io.BytesIO(contenido), data_only=True)
    for ws in wb.worksheets:
        for fila_enc in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20)):
            nombres = {_norm(c.value): c.column - 1 for c in fila_enc if c.value is not None}
            col_cuil = next((i for k, i in nombres.items() if k == "CUIL" or k.startswith("CUIL")), None)
            if col_cuil is None:
                continue
            col_nombre = next((i for k, i in nombres.items() if "NOMBRE" in k or "APELLIDO" in k), None)
            modo, col, titulo = None, None, None
            for k, i in nombres.items():
                base = k.replace(" EN MINUTOS", "").replace(" MINUTOS", "").replace(" MIN", "").strip()
                if base in _COLS_DEUDA:
                    modo, col, titulo = "DEUDA", i, k
                    break
                if base in _COLS_SALDO and col is None:
                    modo, col, titulo = "SALDO", i, k
            if col is None:
                continue
            en_minutos = "MIN" in titulo
            filas, avisos = [], []
            for nro, valores in enumerate(ws.iter_rows(min_row=fila_enc[0].row + 1, values_only=True),
                                          start=fila_enc[0].row + 1):
                cuil = valores[col_cuil] if col_cuil < len(valores) else None
                if cuil is None or not str(cuil).strip():
                    continue
                nombre = str(valores[col_nombre]).strip() if col_nombre is not None and valores[col_nombre] else ""
                minutos = _a_minutos(valores[col] if col < len(valores) else None, en_minutos)
                if minutos is None:
                    avisos.append(f"Fila {nro} ({nombre or cuil}): sin horas o con un valor que no se entiende; se saltea.")
                    continue
                if modo == "DEUDA":
                    minutos = -abs(minutos)
                filas.append({"fila": nro, "cuil": str(cuil).strip(), "nombre": nombre, "minutos": minutos})
            return {"filas": filas, "avisos": avisos, "columna": titulo, "modo": modo, "hoja": ws.title}
    raise ValueError("No encontré una columna CUIL junto con una columna de horas (Debe, Saldo, Horas o Banco).")
