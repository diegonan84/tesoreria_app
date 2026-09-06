import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from sqlalchemy.orm import Session
from backend.modulos.patrimonio.models import Patrimonio

from . import schemas

class SistemasService:
    def __init__(self, db: Session):
        self.db = db

    def generar_pdf_salida(self, data: schemas.NotaSalidaRequest):
        tipo = data.tipo_manual or "Equipo"
        marca = data.marca_manual or ""
        serie = data.serie_manual or "S/N"
        inventario_str = ""

        # Cruzamos datos con Patrimonio si ingresan el Nro de Inventario
        if data.numero_inventario:
            bien = self.db.query(Patrimonio).filter(Patrimonio.numero_inventario == data.numero_inventario).first()
            if bien:
                tipo = bien.tipo or bien.descripcion_bien or "Equipo"
                marca = bien.marca or "Sin marca"
                serie = bien.serie or "S/N"
                inventario_str = f" Nro Inventario: {bien.numero_inventario}"
            else:
                inventario_str = f" Nro Inventario: {data.numero_inventario}"

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        hoy = datetime.now()
        fecha_str = f"Buenos Aires, {hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

        # --- DIBUJAR DOCUMENTO ---
        
        # 1. Escudo / Logo GCBA
        ruta_logo = "frontend/img/escudo_ba.png"
        y_offset_titulos = height - 80
        
        if os.path.exists(ruta_logo):
            ancho_logo = 80
            alto_logo = 80
            x_logo = (width - ancho_logo) / 2.0
            y_logo = height - 120
            # Dibujamos la imagen manteniendo su proporción
            c.drawImage(ruta_logo, x_logo, y_logo, width=ancho_logo, height=alto_logo, preserveAspectRatio=True, mask='auto')
            y_offset_titulos = height - 150 # Bajamos los textos para hacerle lugar al escudo

        # 2. Textos Institucionales
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2.0, y_offset_titulos, "GOBIERNO DE LA CIUDAD DE BUENOS AIRES")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2.0, y_offset_titulos - 20, "DIRECCIÓN GENERAL TESORERÍA")

        # 3. Fecha
        c.setFont("Helvetica", 11)
        c.drawRightString(width - 70, y_offset_titulos - 60, fecha_str)

        # 4. Cuerpo de la nota
        c.setFont("Helvetica", 12)
        texto_nota = (
            f"Se hace entrega de {data.cantidad} ({data.cantidad}) {tipo} marca {marca} "
            f"Nro de serie: {serie}{inventario_str} a {data.nombre_apellido} "
            f"CUIT/CUIL {data.cuil_cuit} por el motivo: {data.motivo}."
        )

        lineas = simpleSplit(texto_nota, "Helvetica", 12, width - 140)
        y_text = y_offset_titulos - 180
        for linea in lineas:
            c.drawString(70, y_text, linea)
            y_text -= 20

        # Las firmas fueron eliminadas a petición

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer