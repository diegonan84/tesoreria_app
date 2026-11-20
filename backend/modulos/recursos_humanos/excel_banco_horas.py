"""
Excel de saldo inicial del banco de horas
-----------------------------------------
Una fila por persona. Se busca (en cualquier hoja, en las primeras 20 filas) un encabezado con
una columna CUIL y una columna de horas: "Saldo Hs", "Saldo", "Debe", "Horas adeudadas", "Banco", "Horas"...
El valor es lo que la persona DEBE (formato de la planilla de RRHH: "Saldo Hs" = 0:51 → debe 51 minutos;
0 = no debe nada). Si viniera con signo negativo, también se toma como deuda.
Modelo: Nombre | Apellido | CUIL | Saldo Hs (CUIL como número o con guiones).
Valores admitidos: "3:50", "-3:50", "03:50:00", 3.5 (horas decimales), una hora de Excel (0,1597…)
o un número entero de minutos si la columna dice "MIN".
"""
import io
import re
import unicodedata
from datetime import datetime, time, timedelta
from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

_COLS_HORAS = ("SALDO HS", "SALDO HORAS", "SALDO H", "SALDO", "SALDO INICIAL", "DEBE", "HORAS ADEUDADAS", "ADEUDA",
               "ADEUDADAS", "FALTANTE", "FALTANTES", "DEUDA", "BANCO", "BANCO DE HORAS", "HORAS", "HS")


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
            col_apellido = next((i for k, i in nombres.items() if "APELLIDO" in k and "NOMBRE" not in k), None)
            col_nombre = next((i for k, i in nombres.items() if "NOMBRE" in k), None)
            modo, col, titulo = "DEUDA", None, None
            for k, i in nombres.items():
                base = k.replace(" EN MINUTOS", "").replace(" MINUTOS", "").replace(" MIN", "").strip()
                if base in _COLS_HORAS:
                    col, titulo = i, k
                    break
            if col is None:
                continue
            en_minutos = "MIN" in titulo
            filas, avisos = [], []
            for nro, valores in enumerate(ws.iter_rows(min_row=fila_enc[0].row + 1, values_only=True),
                                          start=fila_enc[0].row + 1):
                cuil = valores[col_cuil] if col_cuil < len(valores) else None
                if cuil is None or not str(cuil).strip():
                    continue
                partes = [valores[c] for c in (col_apellido, col_nombre) if c is not None and c < len(valores) and valores[c]]
                nombre = ", ".join(str(x).strip() for x in partes)
                minutos = _a_minutos(valores[col] if col < len(valores) else None, en_minutos)
                if minutos is None:
                    avisos.append(f"Fila {nro} ({nombre or cuil}): sin horas o con un valor que no se entiende; se saltea.")
                    continue
                minutos = -abs(minutos)  # siempre es lo que debe
                filas.append({"fila": nro, "cuil": str(cuil).strip(), "nombre": nombre, "minutos": minutos})
            return {"filas": filas, "avisos": avisos, "columna": titulo, "modo": modo, "hoja": ws.title}
    raise ValueError("No encontré una columna CUIL junto con una columna de horas (Debe, Saldo, Horas o Banco).")



# ---------------------------------------------------------------------------
# Exportar la planilla de estado de horas
# ---------------------------------------------------------------------------
def _hhmm(minutos: int) -> str:
    signo = "-" if minutos < 0 else ""
    m = abs(minutos)
    return f"{signo}{m // 60}:{m % 60:02d}"


def exportar(personas: list, fechas: list) -> bytes:
    """personas: [{apellido, nombre, cuil, sector, cod_reg, inicial, fichadas, ajustes, total, texto, por_dia: {fecha: min}}]
    (minutos con signo: negativo = debe). fechas: días con deudas sumadas, en orden."""
    wb = Workbook()
    borde = Border(*(Side(style="thin", color="BFBFBF"),) * 4)
    titulo = PatternFill("solid", start_color="1A3644", end_color="1A3644")
    rojo, verde = Font(color="B3261E", bold=True), Font(color="2E7D32", bold=True)

    def encabezado(ws, columnas, anchos):
        ws.append(columnas)
        for c in ws[ws.max_row]:
            c.font, c.fill, c.border = Font(bold=True, color="FFFFFF"), titulo, borde
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, ancho in enumerate(anchos, start=1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = ancho
        ws.freeze_panes = "D2"

    # Hoja 1: saldo de cada persona
    ws = wb.active
    ws.title = "Estado de horas"
    encabezado(ws, ["Apellido", "Nombre", "CUIL", "Sector", "Cód Reg", "Saldo inicial",
                    "Deuda por fichadas", "Ajustes", "Saldo total", "Estado"],
               [20, 22, 15, 34, 26, 12, 12, 10, 12, 30])
    for p in personas:
        ws.append([p["apellido"], p["nombre"], p["cuil"], p["sector"] or "", p["cod_reg"] or "",
                   _hhmm(p["inicial"]), _hhmm(p["fichadas"]), _hhmm(p["ajustes"]), _hhmm(p["total"]), p["texto"]])
        fila = ws.max_row
        for c in ws[fila]:
            c.border = borde
        for col in range(6, 10):
            ws.cell(row=fila, column=col).alignment = Alignment(horizontal="center")
        ws.cell(row=fila, column=9).font = rojo if p["total"] < 0 else verde if p["total"] > 0 else Font()
    total = sum(p["total"] for p in personas)
    ws.append(["", "", "", "", "Total", _hhmm(sum(p["inicial"] for p in personas)),
               _hhmm(sum(p["fichadas"] for p in personas)), _hhmm(sum(p["ajustes"] for p in personas)), _hhmm(total), ""])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

    # Hoja 2: lo que debió cada persona cada día (lo sumado desde los Excel de fichadas)
    ws2 = wb.create_sheet("Deuda por día")
    encabezado(ws2, ["Apellido", "Nombre", "CUIL"] + [f.strftime("%d/%m/%Y") for f in fechas] + ["Total fichadas"],
               [20, 22, 15] + [12] * len(fechas) + [14])
    for p in personas:
        if not p["por_dia"]:
            continue
        ws2.append([p["apellido"], p["nombre"], p["cuil"]] + [_hhmm(p["por_dia"][f]) if f in p["por_dia"] else "" for f in fechas]
                   + [_hhmm(p["fichadas"])])
        for c in ws2[ws2.max_row]:
            c.border = borde
            if c.column > 3:
                c.alignment = Alignment(horizontal="center")
    if ws2.max_row == 1:
        ws2.append(["Todavía no se sumaron deudas de fichadas."])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
