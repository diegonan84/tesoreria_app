"""
Planilla de horarios de RRHH ("2026 HORARIOS.xlsx")
---------------------------------------------------
Una hoja por área. En cada hoja:
    fila 1:  PERSONAL | FRANJA HORARIA
    fila 2:  APELLIDO Y NOMBRES | LUNES | MARTES | MIERCOLES | JUEVES | VIERNES
    luego:   filas de personas, intercaladas con filas-título de subsector (solo columna A)
             y al final una fila de totales (sin nombre) que se ignora.
Celdas de día: la franja horaria en texto ("9:00 a 16:00", "8 A 15", "DGAI 9 A 16"...).
El día Home/remoto va pintado de amarillo y/o con una "R" en el texto.
Columnas G en adelante: observaciones libres.
El color de la celda del nombre se guarda tal cual (se usa para el Cód Reg).
"""
import colorsys
import io
import re
from typing import List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from .excel_home_office import _color_relleno, _colores_tema, _normalizar
from .franjas import leer_franja

DIAS = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES")
AMARILLO = "FFFF00"
BLANCO = {"FFFFFF", "000000"}


def es_amarillo(hex_rgb: Optional[str]) -> bool:
    if not hex_rgb:
        return False
    r, g, b = (int(hex_rgb[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return 52 <= h * 360 <= 68 and s >= 0.6 and v >= 0.7  # FFC000 (naranja, ~45°) no cuenta


def _color_significativo(celda, tema) -> Optional[str]:
    """Color de relleno si no es blanco/transparente."""
    c = _color_relleno(celda, tema)
    if not c or c.upper() in BLANCO:
        return None
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    if min(r, g, b) >= 245:  # casi blanco
        return None
    return c.upper()


def _buscar_encabezado(ws):
    """Fila y columnas de 'APELLIDO Y NOMBRES' y de cada día (en las primeras 10 filas)."""
    for fila in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 10)):
        nombres = {_normalizar(c.value): c.column for c in fila if c.value is not None}
        if all(d in nombres for d in DIAS):
            col_nombre = next((col for k, col in nombres.items() if "APELLIDO" in k or "NOMBRE" in k), 1)
            return fila[0].row, col_nombre, [nombres[d] for d in DIAS]
    return None, None, None


def leer(contenido: bytes) -> dict:
    """{"personas": [...], "avisos": [str], "hojas": [str]}

    Cada persona: {hoja, fila, nombre, subsector, color, observacion,
                   dias: [ {tipo: HOME|CONVOCADO|SIN_HORARIO, texto, desde, hasta, lugar} ] * 5}"""
    wb = load_workbook(io.BytesIO(contenido), data_only=True)
    tema = _colores_tema(wb)
    personas, avisos, hojas = [], [], []

    for ws in wb.worksheets:
        if _normalizar(ws.title) == "SIN AREA":
            avisos.append("Hoja \"SIN ÁREA\": son las personas que no estaban en la planilla, se saltea.")
            continue
        fila_enc, col_nombre, cols_dias = _buscar_encabezado(ws)
        if not fila_enc:
            avisos.append(f"Hoja \"{ws.title}\": no tiene los encabezados LUNES a VIERNES, se saltea.")
            continue
        hojas.append(ws.title)
        ultima_col = max(cols_dias)
        subsector = None
        for nro in range(fila_enc + 1, ws.max_row + 1):
            nombre = ws.cell(row=nro, column=col_nombre).value
            nombre = re.sub(r"\s+", " ", str(nombre)).strip() if nombre is not None else ""
            valores = [ws.cell(row=nro, column=c).value for c in cols_dias]
            hay_dias = any(v is not None and str(v).strip() for v in valores)

            if not nombre:
                continue  # fila de totales o vacía
            if not hay_dias:
                subsector = nombre  # fila-título de subsector
                continue

            dias, remotos = [], 0
            for i, col in enumerate(cols_dias):
                celda = ws.cell(row=nro, column=col)
                franja = leer_franja(celda.value)
                amarillo = es_amarillo(_color_relleno(celda, tema))
                if franja is None:
                    dias.append({"tipo": "SIN_HORARIO", "texto": None, "desde": None, "hasta": None, "lugar": None})
                    continue
                remoto = franja.remoto or amarillo
                if franja.remoto != amarillo:
                    avisos.append(f"{ws.title}, fila {nro} ({nombre}), {DIAS[i].capitalize()}: "
                                  + ("tiene R pero no está pintado de amarillo" if franja.remoto
                                     else "está en amarillo pero no tiene R") + "; se toma como Home.")
                if not franja.entendida:
                    avisos.append(f"{ws.title}, fila {nro} ({nombre}), {DIAS[i].capitalize()}: "
                                  f"no se entiende el horario \"{franja.texto}\" (se guarda el texto tal cual).")
                remotos += remoto
                dias.append({
                    "tipo": "HOME" if remoto else "CONVOCADO",
                    "texto": (franja.limpio or franja.texto)[:80] if franja.limpio or not franja.remoto else None,
                    "desde": franja.desde, "hasta": franja.hasta,
                    "lugar": (franja.lugar or None) and franja.lugar[:60],
                })
            if remotos > 1:
                avisos.append(f"{ws.title}, fila {nro} ({nombre}): tiene {remotos} días Home.")

            obs = [str(ws.cell(row=nro, column=c).value).strip()
                   for c in range(ultima_col + 1, ws.max_column + 1)
                   if ws.cell(row=nro, column=c).value is not None and str(ws.cell(row=nro, column=c).value).strip()]
            personas.append({
                "hoja": ws.title, "fila": nro, "nombre": nombre, "subsector": subsector,
                "color": _color_significativo(ws.cell(row=nro, column=col_nombre), tema),
                "observacion": " | ".join(obs) or None,
                "dias": dias,
            })
    return {"personas": personas, "avisos": avisos, "hojas": hojas}


# ---------------------------------------------------------------------------
# Exportar con el mismo formato
# ---------------------------------------------------------------------------
def _relleno(hex_rgb: str) -> PatternFill:
    return PatternFill("solid", start_color=hex_rgb, end_color=hex_rgb)


def exportar(personas: List[dict]) -> bytes:
    """personas: [{area, subsector, apellido, nombre, color, observacion, cod_reg,
                   dias: [{tipo, texto}] * 5}] ya ordenadas."""
    wb = Workbook()
    wb.remove(wb.active)
    borde = Border(*(Side(style="thin", color="BFBFBF"),) * 4)
    negrita = Font(bold=True)

    areas = []
    for p in personas:
        if (p.get("area") or "SIN ÁREA") not in areas:
            areas.append(p.get("area") or "SIN ÁREA")

    for area in areas:
        ws = wb.create_sheet(re.sub(r"[\\/*?:\[\]]", " ", area)[:31])
        ws.append(["PERSONAL", "FRANJA HORARIA"])
        ws.merge_cells(start_row=1, start_column=2, end_row=1, end_column=6)
        ws.append(["APELLIDO Y NOMBRES", *DIAS, "OBSERVACIONES", "CÓD REG"])
        for fila in (1, 2):
            for celda in ws[fila]:
                celda.font = Font(bold=True, color="FFFFFF")
                celda.fill = _relleno("1A3644")
                celda.alignment = Alignment(horizontal="center")
                celda.border = borde

        presentes = [0] * 5
        subsector = object()
        for p in (x for x in personas if (x.get("area") or "SIN ÁREA") == area):
            if p.get("subsector") != subsector:
                subsector = p.get("subsector")
                if subsector:
                    ws.append([subsector])
                    ws.cell(row=ws.max_row, column=1).font = negrita
                    ws.cell(row=ws.max_row, column=1).fill = _relleno("B4C6E7")
            nombre = f"{p['apellido']},{p['nombre']}".upper()
            textos = []
            for d in p["dias"]:
                texto = d.get("texto") or ""
                if d["tipo"] == "HOME" and not re.search(r"(^|[\s\-:])R(\s|$|:)", texto, re.I):
                    texto = f"{texto} - R".strip(" -") if texto else "R"
                textos.append(texto)
            ws.append([nombre, *textos, p.get("observacion") or "", p.get("cod_reg") or ""])
            fila = ws.max_row
            if p.get("color"):
                ws.cell(row=fila, column=1).fill = _relleno(p["color"])
            for i, d in enumerate(p["dias"]):
                celda = ws.cell(row=fila, column=2 + i)
                celda.alignment = Alignment(horizontal="center")
                if d["tipo"] == "HOME":
                    celda.fill = _relleno(AMARILLO)
                elif d["tipo"] == "CONVOCADO":
                    presentes[i] += 1
            for celda in ws[fila][:8]:
                celda.border = borde

        # Igual que la planilla original: totales sin nombre (así no se confunde con una persona al reimportar)
        ws.append([None, *presentes, "← presenciales por día"])
        for celda in ws[ws.max_row][:6]:
            celda.font = negrita
            celda.alignment = Alignment(horizontal="center")
        for letra, ancho in zip("ABCDEFGH", (42, 18, 18, 18, 18, 18, 50, 10)):
            ws.column_dimensions[letra].width = ancho
        ws.freeze_panes = "B3"

    if not wb.worksheets:
        wb.create_sheet("Horarios").append(["Sin datos"])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
