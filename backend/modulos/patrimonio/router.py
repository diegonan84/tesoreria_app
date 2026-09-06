from fastapi import APIRouter, Depends, Query, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.responses import StreamingResponse
from datetime import datetime
from pydantic import BaseModel
import pandas as pd
import io
from . import models
from fastapi import Request
from backend.modulos.auth.dependencies import verificar_usuario_autenticado
from backend.modulos.auditoria.service import registrar_evento

from . import schemas
from .service import PatrimonioService
from .dependencies import get_db, get_client_ip, get_current_user

# ✨ IMPORTS PARA LOS CÓDIGOS DE BARRAS ✨
import base64
import barcode
from barcode.writer import ImageWriter

# Conectamos directamente la dependencia limpia
JWT_DEPENDENCY = get_current_user 

def _obtener_usuario_id(db, email):
    from backend.modulos.usuarios.models import User
    user = db.query(User).filter(User.email == email).first()
    return user.id if user else None

router = APIRouter(
    prefix="/patrimonio",
    tags=["Patrimonio"],
    responses={404: {"description": "No encontrado"}},
)

# Creamos un pequeño esquema temporal aquí mismo para recibir la lista
class LoteEtiquetasRequest(BaseModel):
    numeros: List[str]

# ✨ ENDPOINT ACTUALIZADO A FORMATO EAN-13 ✨
@router.post("/barcode/lote")
def generar_codigo_barras_lote(req: LoteEtiquetasRequest, db: Session = Depends(get_db), usuario_actual: str = Depends(JWT_DEPENDENCY)):
    # 1. Buscamos los equipos seleccionados
    bienes = db.query(models.Patrimonio).filter(models.Patrimonio.numero_inventario.in_(req.numeros)).all()
    
    etiquetas = []
    # 2. Usamos EAN13 que hace la división 1-6-6 y alarga las barras de los extremos/centro
    EAN = barcode.get_barcode_class('ean13')
    
    for bien in bienes:
        try:
            # 3. EAN-13 necesita exactamente 12 dígitos (el 13° es el checksum y se autocalcula).
            numero_limpio = str(bien.numero_inventario).strip()
            numero_padded = numero_limpio.zfill(12) 
            
            # El ImageWriter usa fuentes sans-serif por defecto, quitando el punto de los ceros
            writer = ImageWriter()
            opciones = {
                'module_height': 15.0, # Altura de las barras
                'font_size': 10,       # Tamaño de los números abajo
                'text_distance': 4.0,  # Distancia del texto a las barras
                'quiet_zone': 2.0      # Márgenes a los costados
            }
            
            # 4. Generamos y guardamos la imagen en memoria
            codigo = EAN(numero_padded, writer=writer)
            buffer = io.BytesIO()
            codigo.write(buffer, options=opciones)
            
            # 5. Convertimos a Base64 para el HTML
            b64_codigo = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            etiquetas.append({
                "numero_inventario": bien.numero_inventario,
                "descripcion": bien.descripcion_bien or bien.descripcion_item or "",
                "codigo_base64": b64_codigo 
            })
        except Exception as e:
            print(f"Error generando código EAN13 para {bien.numero_inventario}: {e}")
            continue
            
    return {"etiquetas": etiquetas}


@router.get("/total")
def obtener_total_patrimonio(
    estado: Optional[str] = None, 
    busqueda: Optional[str] = None, 
    desde: Optional[str] = None, 
    hasta: Optional[str] = None, 
    tipo: Optional[str] = None, 
    anio: Optional[str] = None,
    rubro: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = PatrimonioService(db)
    return {"total": service.get_total(estado=estado, busqueda=busqueda, desde=desde, hasta=hasta, tipo=tipo, anio=anio, rubro=rubro)}


@router.get("/exportar/excel")
def exportar_excel_inventario(
    busqueda: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    anio: Optional[str] = None,
    rubro: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = PatrimonioService(db)
    buffer = service.exportar_excel(busqueda=busqueda, desde=desde, hasta=hasta, anio=anio, rubro=rubro)
    
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
    nombre_archivo = f"Inventario_Tesoreria_{fecha_str}.xlsx"
    
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )

@router.get("", response_model=List[schemas.PatrimonioResponse])
def listar_patrimonio(
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, le=1000), 
    estado: Optional[str] = None, 
    busqueda: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    tipo: Optional[str] = None,
    anio: Optional[str] = None,
    rubro: Optional[str] = None,
    sort_by: Optional[str] = "numero_inventario", 
    orden: Optional[str] = "asc",                
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    service = PatrimonioService(db)
    return service.get_all(skip=skip, limit=limit, estado=estado, busqueda=busqueda, desde=desde, hasta=hasta, tipo=tipo, anio=anio, rubro=rubro, sort_by=sort_by, orden=orden)


@router.get("/{numero}", response_model=schemas.PatrimonioResponse)
def obtener_patrimonio(
    numero: str, 
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    service = PatrimonioService(db)
    return service.get_by_numero(numero)

@router.post("", response_model=List[schemas.PatrimonioResponse])
def crear_patrimonio(
    data: schemas.PatrimonioCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY),
    ip: str = Depends(get_client_ip)
):
    service = PatrimonioService(db)
    resultado = service.create(data, usuario=usuario_actual, ip=ip)

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="CREAR_PATRIMONIO",
            detalle=f"Alta de patrimonio: inventario {data.numero_inventario} (cant: {data.cantidad})",
            ip_address=request.client.host
        )
    return resultado

@router.put("/{numero}", response_model=schemas.PatrimonioResponse)
def actualizar_patrimonio(
    numero: str,
    data: schemas.PatrimonioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY),
    ip: str = Depends(get_client_ip)
):
    service = PatrimonioService(db)
    resultado = service.update(numero, data, usuario=usuario_actual, ip=ip)

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="EDITAR_PATRIMONIO",
            detalle=f"Patrimonio editado: inventario {numero}",
            ip_address=request.client.host
        )
    return resultado

@router.delete("/{numero}")
def baja_logica_patrimonio(
    numero: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY),
    ip: str = Depends(get_client_ip)
):
    service = PatrimonioService(db)
    resultado = service.delete(numero, usuario=usuario_actual, ip=ip)

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="BAJA_PATRIMONIO",
            detalle=f"Patrimonio dado de baja: inventario {numero}",
            ip_address=request.client.host
        )
    return resultado

@router.get("/historial/{numero}", response_model=List[schemas.PatrimonioHistorialResponse])
def ver_historial(
    numero: str,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    service = PatrimonioService(db)
    return service.get_historial(numero)

@router.get("/informatica/tipos")
def obtener_tipos_informatica(db: Session = Depends(get_db), usuario_actual: str = Depends(JWT_DEPENDENCY)):
    service = PatrimonioService(db)
    return {"tipos_otros": service.get_tipos_informatica()}

@router.post("/importar")
async def importar_excel(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY),
    ip: str = Depends(get_client_ip)
):
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato Excel (.xls o .xlsx)")

    service = PatrimonioService(db)
    resultado = await service.importar_excel(file, usuario=usuario_actual, ip=ip)

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="IMPORTAR_PATRIMONIO",
            detalle=f"Importación de patrimonio desde archivo: {file.filename}",
            ip_address=request.client.host if request else ip
        )
    return resultado

@router.post("/importar-anio")
async def importar_excel_anio_detalle(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato Excel (.xls o .xlsx)")

    try:
        contents = await file.read()
        df_completo = pd.read_excel(io.BytesIO(contents), header=None)
        
        # 1. Buscamos la fila de encabezados dinámicamente
        header_idx = 0
        for idx, row in df_completo.iterrows():
            row_str = " ".join(str(val).lower() for val in row.values if pd.notna(val))
            # Buscamos combinaciones probables de la palabra inventario y ejercicio
            if "inventario" in row_str and "ejercicio" in row_str:
                header_idx = idx
                break
        
        df_completo.columns = df_completo.iloc[header_idx]
        df = df_completo[header_idx + 1:].reset_index(drop=True)
        df.columns = df.columns.astype(str).str.strip()
        
        # 2. Función auxiliar para encontrar la columna de inventario sin importar cómo se llame exactamente
        def obtener_nombre_columna(nombres_posibles, columnas_df):
            for nombre in nombres_posibles:
                if nombre in columnas_df:
                    return nombre
            return None

        # 3. Detectamos las columnas reales del Excel
        col_inventario = obtener_nombre_columna(["Nº Inventario", "N° Inventario", "Nro Inventario", "N  Inventario", "Inventario", "numero_inventario"], df.columns)
        col_ejercicio = obtener_nombre_columna(["Ejercicio", "Año", "Anio", "anio"], df.columns)
        col_descripcion = obtener_nombre_columna(["Descripción del Bien", "Descripcion del Bien", "Descripción", "descripcion"], df.columns)
        
        col_rubro_num = obtener_nombre_columna(["Rubro Patrimonial Número", "Rubro Patrimonial Numero"], df.columns)
        col_rubro_desc = obtener_nombre_columna(["Rubro Patrimonial Descripción", "Rubro Patrimonial Descripcion"], df.columns)

        if not col_inventario:
            raise HTTPException(status_code=400, detail="El Excel no tiene una columna reconocible para el Número de Inventario.")
        
        actualizados = 0
        omitidos = 0
        
        for index, row in df.iterrows():
            if pd.isna(row.get(col_inventario)):
                continue
                
            nro_inv = str(row[col_inventario]).replace(".0", "").strip()
            
            if not nro_inv or nro_inv.lower() == "nan" or nro_inv == "none":
                continue
            
            # Obtenemos los valores de las columnas encontradas (si existen)
            ejercicio = str(row.get(col_ejercicio, "")).replace(".0", "").strip() if col_ejercicio and pd.notna(row.get(col_ejercicio)) else None
            desc_detallada = str(row.get(col_descripcion, "")).strip() if col_descripcion and pd.notna(row.get(col_descripcion)) else None
            
            val_num = row.get(col_rubro_num) if col_rubro_num else None
            val_desc = row.get(col_rubro_desc) if col_rubro_desc else None
            
            rubro_num = str(val_num).replace(".0", "").strip() if pd.notna(val_num) else ""
            rubro_desc = str(val_desc).strip() if pd.notna(val_desc) else ""
            
            bien = db.query(models.Patrimonio).filter(models.Patrimonio.numero_inventario == nro_inv).first()
            
            if bien:
                modificado = False
                if ejercicio and ejercicio.lower() not in ["nan", "none", ""]:
                    bien.anio = ejercicio
                    modificado = True
                if desc_detallada and desc_detallada.lower() not in ["nan", "none", ""]:
                    bien.descripcion_detallada = desc_detallada
                    modificado = True
                    
                if rubro_num and rubro_num.lower() not in ["nan", "none", ""]:
                    bien.rubro_patrimonial_numero = rubro_num
                    modificado = True
                if rubro_desc and rubro_desc.lower() not in ["nan", "none", ""]:
                    bien.rubro_patrimonial_descripcion = rubro_desc
                    modificado = True
                        
                if modificado:
                    actualizados += 1
            else:
                omitidos += 1
                
        db.commit()
        return {"mensaje": "Carga de Años, Detalles y Rubros finalizada.", "actualizados": actualizados, "omitidos": omitidos}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error leyendo el archivo Excel: {str(e)}")


@router.get("/anios/disponibles")
def obtener_anios(db: Session = Depends(get_db), usuario_actual: str = Depends(JWT_DEPENDENCY)):
    service = PatrimonioService(db)
    return {"anios": service.get_anios_disponibles()}

@router.get("/rubros/disponibles")
def obtener_rubros(db: Session = Depends(get_db), usuario_actual: str = Depends(JWT_DEPENDENCY)):
    rubros = db.query(
        models.Patrimonio.rubro_patrimonial_numero,
        models.Patrimonio.rubro_patrimonial_descripcion
    ).filter(
        models.Patrimonio.rubro_patrimonial_numero.isnot(None),
        models.Patrimonio.rubro_patrimonial_numero != ''
    ).distinct().all()
    
    resultado = [{"numero": r[0], "descripcion": r[1] or ""} for r in rubros if r[0]]
    resultado.sort(key=lambda x: x["numero"])
    return {"rubros": resultado}

@router.post("/barcode")
def generar_codigo_barras(db: Session = Depends(get_db), usuario_actual: str = Depends(JWT_DEPENDENCY)):
    return {"mensaje": "Endpoint de código de barras individual en construcción"}

@router.put("/{numero}/asignar")
def asignar_equipo_endpoint(
    numero: str,
    datos: schemas.AsignarEquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY),
    ip: str = Depends(get_client_ip)
):
    service = PatrimonioService(db)
    equipo = service.asignar_equipo(
        numero_inventario=numero, 
        usuario_id=datos.usuario_id, 
        puesto=datos.puesto, 
        usuario_admin=usuario_actual, 
        ip=ip
    )

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="ASIGNAR_EQUIPO",
            detalle=f"Equipo {numero} asignado al usuario ID {datos.usuario_id} en puesto {datos.puesto}",
            ip_address=request.client.host
        )
    return {"mensaje": "Equipo asignado correctamente", "equipo": equipo.numero_inventario}

@router.post("/importar-informatica")
async def importar_excel_informatica_endpoint(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: dict = Depends(verificar_usuario_autenticado)
):
    ip = request.client.host
    service = PatrimonioService(db)
    resultado = await service.importar_excel_informatica(file, usuario.get("sub"), ip)

    uid = usuario.get("id")
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="IMPORTAR_INFORMATICA",
            detalle=f"Importación informática desde archivo: {file.filename}",
            ip_address=request.client.host
        )
    return resultado