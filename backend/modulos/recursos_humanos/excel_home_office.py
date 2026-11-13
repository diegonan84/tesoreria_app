"""
Excel del Tablero de Home Office
--------------------------------
Formato (una fila por persona):  CUIL | NOMBRE | APELLIDO | LUNES | MARTES | MIERCOLES | JUEVES | VIERNES

Cada celda de día se marca con color de relleno y/o texto:
  - celeste/azul o texto "Home" / "H"            → HOME
  - verde        o texto "Convocado" / "C"       → CONVOCADO
  - vacía, blanca o gris                          → Convocado (es el valor por defecto)
El texto tiene prioridad sobre el color. Al exportar se escriben las dos cosas.
"""
import colorsys
import io
import re
import unicodedata
from typing import List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import COLOR_INDEX

COLUMNAS_DIAS = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES")

# Colores con los que se exporta cada marca (los mismos tonos que usa el ejemplo de RRHH)
COLOR_TIPO = {"HOME": "9BC2E6", "CONVOCADO": "A9D08E"}
TEXTO_TIPO = {"HOME": "Home", "CONVOCADO": "Convocado"}

TEXTOS_HOME = {"H", "HOME", "HOME OFFICE", "HO", "CASA", "REMOTO", "TELETRABAJO"}
TEXTOS_CONVOCADO = {"C", "CONVOCADO", "CONVOCADA", "P", "PRESENCIAL", "OFICINA"}
TEXTOS_VACIO = {"", "-", "—", "X SIN MARCAR", "SIN MARCAR"}

# Colores del tema de Office por defecto, por si el archivo usa colores de tema y no trae el suyo
_TEMA_OFFICE = ["FFFFFF", "000000", "E7E6E6", "44546A", "4472C4", "ED7D31", "A5A5A5", "FFC000", "5B9BD5", "70AD47"]


def _normalizar(texto) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto).strip().upper()


def solo_digitos(cuil) -> str:
    return re.sub(r"\D", "", str(cuil or ""))


# ---------------------------------------------------------------------------
# Exportar
# ---------------------------------------------------------------------------
def exportar(filas: List[dict]) -> bytes:
    """filas: [{cuil, nombre, apellido, sector, dias: [HOME|CONVOCADO|None] * 5}]"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Home Office"
    borde = Border(*(Side(style="thin", color="BFBFBF"),) * 4)

    encabezado = ["CUIL", "NOMBRE", "APELLIDO", *COLUMNAS_DIAS, "SECTOR"]
    ws.append(encabezado)
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", start_color="1A3644", end_color="1A3644")
        celda.alignment = Alignment(horizontal="center")
        celda.border = borde

    for f in filas:
        ws.append([f["cuil"], f["nombre"], f["apellido"], *[TEXTO_TIPO.get(t, "") for t in f["dias"]], f.get("sector") or ""])
        fila = ws.max_row
        for i, tipo in enumerate(f["dias"]):
            celda = ws.cell(row=fila, column=4 + i)
            celda.alignment = Alignment(horizontal="center")
            if tipo in COLOR_TIPO:
                celda.fill = PatternFill("solid", start_color=COLOR_TIPO[tipo], end_color=COLOR_TIPO[tipo])
        for celda in ws[fila]:
            celda.border = borde

    for letra, ancho in zip("ABCDEFGHI", (16, 20, 20, 12, 12, 12, 12, 12, 24)):
        ws.column_dimensions[letra].width = ancho
    ws.freeze_panes = "D2"

    ref = wb.create_sheet("Referencias")
    ref.append(["Color / texto", "Significado"])
    for tipo, significado in (("HOME", "Trabaja desde su casa"), ("CONVOCADO", "Tiene que ir a la oficina")):
        ref.append([TEXTO_TIPO[tipo], significado])
        ref.cell(row=ref.max_row, column=1).fill = PatternFill("solid", start_color=COLOR_TIPO[tipo], end_color=COLOR_TIPO[tipo])
    ref.append(["(vacío)", "Sin marcar"])
    ref.append([])
    ref.append(["Al importar se busca a cada persona por CUIL. Alcanza con pintar la celda o escribir H / C."])
    ref.column_dimensions["A"].width = 16
    ref.column_dimensions["B"].width = 30
    ref["A1"].font = ref["B1"].font = Font(bold=True)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Importar
# ---------------------------------------------------------------------------
def _colores_tema(wb) -> List[str]:
    xml = getattr(wb, "loaded_theme", None)
    if not xml:
        return _TEMA_OFFICE
    if isinstance(xml, bytes):
        xml = xml.decode("utf-8", "ignore")
    bloque = re.search(r"<a:clrScheme.*?</a:clrScheme>", xml, re.S)
    if not bloque:
        return _TEMA_OFFICE
    colores = []
    for nombre in ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"):
        m = re.search(rf"<a:{nombre}>.*?(?:srgbClr val|lastClr)=\"([0-9A-Fa-f]{{6}})\"", bloque.group(0), re.S)
        colores.append(m.group(1).upper() if m else None)
    # Excel intercambia dk/lt en los índices de tema: 0=lt1, 1=dk1, 2=lt2, 3=dk2
    colores[0], colores[1], colores[2], colores[3] = colores[1], colores[0], colores[3], colores[2]
    return [c or d for c, d in zip(colores, _TEMA_OFFICE)]


def _aplicar_tinte(hex_rgb: str, tinte: float) -> str:
    r, g, b = (int(hex_rgb[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l * (1 + tinte) if tinte < 0 else l * (1 - tinte) + tinte
    return "".join(f"{round(v * 255):02X}" for v in colorsys.hls_to_rgb(h, l, s))


def _color_relleno(celda, tema: List[str]) -> Optional[str]:
    relleno = celda.fill
    if not relleno or relleno.fill_type in (None, "none"):
        return None
    color = relleno.fgColor if relleno.fill_type == "solid" else (relleno.fgColor or relleno.start_color)
    if color is None:
        return None
    hex_rgb = None
    if color.type == "rgb" and isinstance(color.rgb, str):
        hex_rgb = color.rgb[-6:]
        if color.rgb.upper() == "00000000":  # "sin color" de openpyxl
            return None
    elif color.type == "indexed" and color.indexed is not None and color.indexed < len(COLOR_INDEX):
        hex_rgb = COLOR_INDEX[color.indexed][-6:]
    elif color.type == "theme" and color.theme is not None and color.theme < len(tema):
        hex_rgb = tema[color.theme]
    if not hex_rgb:
        return None
    return _aplicar_tinte(hex_rgb, color.tint or 0) if color.tint else hex_rgb.upper()


def tipo_por_color(hex_rgb: Optional[str]) -> Optional[str]:
    """Verde → CONVOCADO; celeste/azul → HOME; blanco, gris u otro → None."""
    if not hex_rgb:
        return None
    r, g, b = (int(hex_rgb[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.12 or v < 0.15:  # blanco, gris o negro
        return None
    grados = h * 360
    if 70 <= grados < 170:
        return "CONVOCADO"
    if 170 <= grados < 260:
        return "HOME"
    return "?"  # otro color (amarillo, rojo…): se informa como no reconocido


def tipo_de_celda(celda, tema: List[str]) -> Optional[str]:
    """HOME, CONVOCADO, None (sin marcar) o "?" si la celda tiene algo que no se entiende."""
    texto = _normalizar(celda.value)
    if texto in TEXTOS_HOME:
        return "HOME"
    if texto in TEXTOS_CONVOCADO:
        return "CONVOCADO"
    if texto not in TEXTOS_VACIO:
        return "?"
    return tipo_por_color(_color_relleno(celda, tema))


def leer(contenido: bytes) -> dict:
    """Devuelve {"filas": [{fila, cuil, nombre, apellido, dias}], "problemas": [str]}."""
    wb = load_workbook(io.BytesIO(contenido), data_only=True)
    ws = wb.worksheets[0]
    tema = _colores_tema(wb)

    # Buscamos la fila de encabezados en las primeras 15 filas
    columnas, fila_encabezado = {}, None
    for fila in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 15)):
        nombres = {_normalizar(c.value): c.column for c in fila if c.value is not None}
        if "CUIL" in nombres:
            columnas, fila_encabezado = nombres, fila[0].row
            break
    if not fila_encabezado:
        raise ValueError("No encontré la columna CUIL en la primera hoja.")
    faltan = [d for d in COLUMNAS_DIAS if d not in columnas]
    if faltan:
        raise ValueError("Faltan las columnas: " + ", ".join(faltan) + ".")

    filas, problemas = [], []
    for nro in range(fila_encabezado + 1, ws.max_row + 1):
        cuil = ws.cell(row=nro, column=columnas["CUIL"]).value
        if cuil is None or str(cuil).strip() == "":
            continue
        dias = []
        for i, dia in enumerate(COLUMNAS_DIAS):
            tipo = tipo_de_celda(ws.cell(row=nro, column=columnas[dia]), tema)
            if tipo == "?":
                problemas.append(f"Fila {nro}, {dia.capitalize()}: no se reconoce la marca (queda Convocado).")
                tipo = None
            dias.append(tipo)
        filas.append({
            "fila": nro,
            "cuil": str(cuil).strip(),
            "nombre": str(ws.cell(row=nro, column=columnas["NOMBRE"]).value or "").strip() if "NOMBRE" in columnas else "",
            "apellido": str(ws.cell(row=nro, column=columnas["APELLIDO"]).value or "").strip() if "APELLIDO" in columnas else "",
            "dias": dias,
        })
    return {"filas": filas, "problemas": problemas}
