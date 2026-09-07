from fastapi import APIRouter, Depends, Query, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
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
from .service import PatrimonioService, es_nombre_persona
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

class _ArchivoMemoria:
    """Envuelve un archivo ya leído en memoria para pasarlo a los servicios (misma interfaz que UploadFile)."""
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content
    async def read(self):
        return self._content

def _detectar_tipo_excel(contenido: bytes):
    """Detecta el tipo de Excel por sus encabezados:
    'informatica' | 'anio' | 'general' | None"""
    try:
        xls = pd.ExcelFile(io.BytesIO(contenido))
    except Exception:
        return None

    for sheet in xls.sheet_names:
        try:
            df0 = pd.read_excel(xls, sheet_name=sheet, header=None)
        except Exception:
            continue
        for _, row in df0.iterrows():
            celdas = [str(v).strip() for v in row.values if pd.notna(v)]
            texto = " ".join(c.lower() for c in celdas).lower()
            if not texto:
                continue
            if any(k in texto for k in ["nombre de equipo", "usuario/destino", "serie monitor", "caract pc"]):
                return "informatica"
            if "inventario" in texto and "ejercicio" in texto:
                return "anio"
            if "inventario" in texto and "estado" in texto:
                return "general"
    return None

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


@router.get("/destinos")
def listar_destinos(
    buscar: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    """Lista de lugares de destino con la cantidad de elementos activos en cada uno."""
    query = db.query(models.Destino).filter(models.Destino.activo == True)

    if buscar and buscar.strip():
        termino = f"%{buscar.strip()}%"
        query = query.filter(or_(
            models.Destino.nombre.ilike(termino),
            models.Destino.reparticion.ilike(termino),
        ))

    destinos = query.order_by(models.Destino.nombre).all()

    resultado = []
    for d in destinos:
        cantidad = db.query(models.Patrimonio).filter(
            models.Patrimonio.destino_id == d.id,
            models.Patrimonio.activo == True
        ).count()
        resultado.append({
            "id": d.id,
            "nombre": d.nombre,
            "reparticion": d.reparticion or "",
            "cantidad": cantidad,
        })

    return {"destinos": resultado}


class DestinoCreate(BaseModel):
    nombre: str
    reparticion: Optional[str] = None


@router.post("/destinos")
def crear_destino(
    datos: DestinoCreate,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    servicio = PatrimonioService(db)
    destino = servicio._resolver_destino_por_nombre(datos.nombre, reparticion=datos.reparticion, crear=True)
    if destino.reparticion is None and datos.reparticion:
        destino.reparticion = datos.reparticion
    db.commit()
    return {"id": destino.id, "nombre": destino.nombre, "reparticion": destino.reparticion or ""}


@router.put("/destinos/{destino_id}")
def actualizar_destino(
    destino_id: int,
    datos: DestinoCreate,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    destino = db.query(models.Destino).filter(models.Destino.id == destino_id).first()
    if not destino:
        raise HTTPException(status_code=404, detail="Destino no encontrado")
    destino.nombre = datos.nombre.strip()
    destino.reparticion = datos.reparticion
    db.commit()
    return {"id": destino.id, "nombre": destino.nombre, "reparticion": destino.reparticion or ""}


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
    ip: str = Depends(get_client_ip),
    reactivar_desactualizados: bool = Form(False)
):
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato Excel (.xls o .xlsx)")

    service = PatrimonioService(db)
    resultado = await service.importar_excel(file, usuario=usuario_actual, ip=ip, reactivar_desactualizados=reactivar_desactualizados)

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="IMPORTAR_PATRIMONIO",
            detalle=f"Importación de patrimonio desde archivo: {file.filename}",
            ip_address=request.client.host if request else ip
        )
    return resultado

@router.post("/importar-todos")
async def importar_excel_todos(
    files: List[UploadFile] = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY),
    ip: str = Depends(get_client_ip),
    reactivar_desactualizados: bool = Form(False)
):
    """Recibe varios Excel a la vez, detecta cada tipo por sus encabezados
    (general / año-detalles / informática) y los procesa en orden."""
    if not files:
        raise HTTPException(status_code=400, detail="No se recibió ningún archivo.")

    for f in files:
        if not f.filename.endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail=f"El archivo {f.filename} no es formato Excel (.xls o .xlsx)")

    leidos = []
    for f in files:
        contenido = await f.read()
        tipo = _detectar_tipo_excel(contenido)
        if not tipo:
            raise HTTPException(status_code=400, detail=f"No se pudo reconocer el tipo del archivo {f.filename}. Verificá que sea uno de los 3 formatos de importación.")
        leidos.append((f.filename, tipo, contenido))

    # ⚠️ ORDEN OBLIGADO para no alterar la importación:
    # 1) Excel general (todos los estados) → 2) Año/Detalles (solo autorizados) → 3) Informática.
    # Así la Informática (fuente autoritativa de asignaciones) se aplica al final.
    orden_tipos = {"general": 0, "anio": 1, "informatica": 2}
    leidos.sort(key=lambda x: orden_tipos[x[1]])

    service = PatrimonioService(db)
    resultados = []
    desactualizados = {}
    reactivados = 0

    try:
        for filename, tipo, contenido in leidos:
            archivo = _ArchivoMemoria(filename, contenido)
            if tipo == "general":
                r = await service.importar_excel(archivo, usuario=usuario_actual, ip=ip, reactivar_desactualizados=reactivar_desactualizados)
                des = r.get("resumen", {}).get("usuarios_desactualizados") or {}
                for k, v in des.items():
                    desactualizados[k] = desactualizados.get(k, 0) + v
                reactivados += r.get("resumen", {}).get("usuarios_reactivados") or 0
                resultados.append({"archivo": filename, "tipo": tipo, "mensaje": r.get("mensaje", ""), "resumen": r.get("resumen", {})})
            elif tipo == "informatica":
                r = await service.importar_excel_informatica(archivo, usuario_actual, ip, reactivar_desactualizados=reactivar_desactualizados)
                des = r.get("resumen", {}).get("usuarios_desactualizados") or {}
                for k, v in des.items():
                    desactualizados[k] = desactualizados.get(k, 0) + v
                reactivados += r.get("resumen", {}).get("usuarios_reactivados") or 0
                resultados.append({"archivo": filename, "tipo": tipo, "mensaje": r.get("mensaje", ""), "resumen": r.get("resumen", {})})
            else:  # anio
                r = service.importar_excel_anio(contenido, filename)
                resultados.append({"archivo": filename, "tipo": tipo, "mensaje": r.get("mensaje", ""), "resumen": r})
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error procesando la importación múltiple: {str(e)}")

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="IMPORTAR_EXCEL_MULTIPLE",
            detalle=f"Importación múltiple ({len(leidos)} archivos): {', '.join(f for f, _, _ in leidos)}",
            ip_address=request.client.host if request else ip
        )
    return {
        "mensaje": "Importación múltiple finalizada",
        "resultados": resultados,
        "resumen": {
            "total_archivos": len(leidos),
            "usuarios_reactivados": reactivados,
            "usuarios_desactualizados": desactualizados
        }
    }

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
        return PatrimonioService(db).importar_excel_anio(contents, file.filename)
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
        ip=ip,
        destino_id=datos.destino_id,
        destino_nuevo=datos.destino_nuevo
    )

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="ASIGNAR_EQUIPO",
            detalle=f"Equipo {numero} asignado (usuario {datos.usuario_id}, destino {datos.destino_id or datos.destino_nuevo or 'stock'})",
            ip_address=request.client.host
        )
    return {"mensaje": "Equipo asignado correctamente", "equipo": equipo.numero_inventario}


# --------------------------------------------------
# CONSULTA: ¿QUÉ ELEMENTOS TIENE CADA USUARIO?
# --------------------------------------------------
@router.get("/asignaciones/usuarios")
def listar_usuarios_con_elementos(
    buscar: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    from backend.modulos.usuarios.models import User

    query = (
        db.query(User)
        .join(models.Patrimonio, models.Patrimonio.usuario_id == User.id)
        .filter(models.Patrimonio.activo == True)
    )

    if buscar and buscar.strip():
        termino = f"%{buscar.strip()}%"
        query = query.filter(or_(
            User.nombre.ilike(termino),
            User.apellido.ilike(termino),
            User.cuil.ilike(termino),
            User.reparticion.ilike(termino),
            User.puesto.ilike(termino),
        ))

    query = query.distinct().order_by(User.apellido, User.nombre)
    usuarios = query.all()

    resultado = []
    for u in usuarios:
        cantidad = db.query(models.Patrimonio).filter(
            models.Patrimonio.usuario_id == u.id,
            models.Patrimonio.activo == True
        ).count()
        resultado.append({
            "id": u.id,
            "nombre_completo": f"{u.apellido}, {u.nombre}",
            "cuil": u.cuil,
            "reparticion": u.reparticion,
            "sector": u.sector.nombre if u.sector else "",
            "puesto": u.puesto or "",
            "cantidad": cantidad,
        })

    return {"usuarios": resultado}


@router.get("/asignaciones/por-usuario/{usuario_id}")
def elementos_por_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    bienes = db.query(models.Patrimonio).filter(
        models.Patrimonio.usuario_id == usuario_id,
        models.Patrimonio.activo == True
    ).order_by(models.Patrimonio.tipo, models.Patrimonio.numero_inventario).all()

    items = []
    for b in bienes:
        items.append({
            "numero_inventario": b.numero_inventario,
            "tipo": b.tipo or "",
            "descripcion": b.descripcion_bien or b.descripcion_item or "",
            "marca": b.marca or "",
            "modelo": b.modelo or "",
            "serie": b.serie or "",
            "nombre_de_equipo": b.nombre_de_equipo or "",
            "puesto": b.puesto or "",
            "anio": b.anio or "",
            "estado": b.estado or "",
        })

    return {"usuario_id": usuario_id, "items": items, "total": len(items)}

@router.get("/asignaciones/por-lugar/{destino_id}")
def elementos_por_lugar(
    destino_id: int,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    """Elementos que están en un lugar de destino (Destino)."""
    destino = db.query(models.Destino).filter(models.Destino.id == destino_id).first()
    if not destino:
        raise HTTPException(status_code=404, detail="Destino no encontrado")

    bienes = db.query(models.Patrimonio).filter(
        models.Patrimonio.destino_id == destino_id,
        models.Patrimonio.activo == True
    ).order_by(models.Patrimonio.tipo, models.Patrimonio.numero_inventario).all()

    items = []
    for b in bienes:
        items.append({
            "numero_inventario": b.numero_inventario,
            "tipo": b.tipo or "",
            "descripcion": b.descripcion_bien or b.descripcion_item or "",
            "marca": b.marca or "",
            "modelo": b.modelo or "",
            "serie": b.serie or "",
            "nombre_de_equipo": b.nombre_de_equipo or "",
            "puesto": b.puesto or "",
            "anio": b.anio or "",
            "estado": b.estado or "",
        })

    return {"destino_id": destino_id, "destino_nombre": destino.nombre, "items": items, "total": len(items)}

@router.get("/asignaciones/lista-completa")
def lista_completa_asignaciones(
    buscar: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    """Vista unificada: TODOS los usuarios y destinos (lugares) con la cantidad de
    elementos en teletrabajo (puesto HOME) y el total de elementos asignados."""
    from backend.modulos.usuarios.models import User

    termino = f"%{buscar.strip()}%" if buscar and buscar.strip() else None

    # --- Usuarios (personas) ---
    q_usuarios = db.query(User).filter(User.activo == True)
    if termino:
        q_usuarios = q_usuarios.filter(or_(
            User.nombre.ilike(termino),
            User.apellido.ilike(termino),
            User.cuil.ilike(termino),
            User.reparticion.ilike(termino),
            User.puesto.ilike(termino),
        ))
    usuarios = q_usuarios.order_by(User.apellido, User.nombre).all()

    resultados = []
    for u in usuarios:
        q_bienes = db.query(models.Patrimonio).filter(
            models.Patrimonio.usuario_id == u.id,
            models.Patrimonio.activo == True
        )
        cantidad_total = q_bienes.count()
        cantidad_home = q_bienes.filter(models.Patrimonio.puesto.ilike("home%")).count()
        sector = u.sector.nombre if u.sector else ""
        resultados.append({
            "tipo": "usuario",
            "id": u.id,
            "nombre": f"{u.apellido}, {u.nombre}".upper(),
            "sub": " · ".join(x for x in [sector, u.reparticion or ""] if x),
            "cantidad_home": cantidad_home,
            "cantidad_total": cantidad_total,
        })

    # --- Destinos (lugares) ---
    q_destinos = db.query(models.Destino).filter(models.Destino.activo == True)
    if termino:
        q_destinos = q_destinos.filter(or_(
            models.Destino.nombre.ilike(termino),
            models.Destino.reparticion.ilike(termino),
        ))
    destinos = q_destinos.order_by(models.Destino.nombre).all()

    for d in destinos:
        q_bienes = db.query(models.Patrimonio).filter(
            models.Patrimonio.destino_id == d.id,
            models.Patrimonio.activo == True
        )
        cantidad_total = q_bienes.count()
        cantidad_home = q_bienes.filter(models.Patrimonio.puesto.ilike("home%")).count()
        resultados.append({
            "tipo": "destino",
            "id": d.id,
            "nombre": d.nombre.upper(),
            "sub": d.reparticion or "",
            "cantidad_home": cantidad_home,
            "cantidad_total": cantidad_total,
        })

    # --- Textos de Usuario/Destino aún sin vincular (ej: "CEMENTERIO") ---
    texto_norm = func.upper(func.trim(models.Patrimonio.usuario_destino))
    texto_q = db.query(
        texto_norm.label("texto_norm"),
        func.count(models.Patrimonio.numero_inventario).label("n_home"),
    ).filter(
        models.Patrimonio.usuario_destino.isnot(None),
        models.Patrimonio.usuario_destino != "",
        models.Patrimonio.activo == True,
        models.Patrimonio.puesto.ilike("home%"),
        models.Patrimonio.usuario_id.is_(None),
        models.Patrimonio.destino_id.is_(None),
    )
    if termino:
        texto_q = texto_q.filter(texto_norm.ilike(termino))
    filas_texto = texto_q.group_by(texto_norm).all()

    for texto, n_home in filas_texto:
        total_texto = db.query(models.Patrimonio).filter(
            texto_norm == texto,
            models.Patrimonio.activo == True,
            models.Patrimonio.usuario_id.is_(None),
            models.Patrimonio.destino_id.is_(None),
        ).count()
        # Convención: nombre y apellido sin CUIL → persona EXTERNA; lo demás → lugar pendiente
        es_externo = es_nombre_persona(texto)
        resultados.append({
            "tipo": "externo" if es_externo else "pendiente",
            "id": None,
            "texto": texto,
            "nombre": texto,
            "sub": "Persona externa al sistema (sin CUIL)" if es_externo else "Lugar sin registrar — texto aún sin vincular",
            "cantidad_home": n_home,
            "cantidad_total": total_texto,
        })

    # --- Solo mostramos quienes tienen AL MENOS UN elemento en HOME ---
    resultados = [r for r in resultados if r["cantidad_home"] > 0]

    # Orden: personas, lugares, luego textos pendientes; dentro de cada grupo por nombre
    orden_tipo = {"usuario": 0, "destino": 1, "pendiente": 2}
    resultados.sort(key=lambda r: (orden_tipo.get(r["tipo"], 3), r["nombre"]))
    return {"resultados": resultados, "total": len(resultados)}


@router.get("/asignaciones/detalle-unificado")
def detalle_unificado_asignaciones(
    tipo: str = Query(..., pattern="^(usuario|destino|externo|pendiente)$"),
    id: Optional[int] = None,
    texto: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    """Elementos con puesto HOME (teletrabajo) de un usuario, un destino o un
    texto Usuario/Destino aún sin vincular (ej: "CEMENTERIO")."""
    query = db.query(models.Patrimonio).filter(
        models.Patrimonio.activo == True,
        models.Patrimonio.puesto.ilike("home%"),
    )

    nombre = ""
    if tipo == "usuario":
        from backend.modulos.usuarios.models import User
        u = db.query(User).filter(User.id == id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        nombre = f"{u.nombre} {u.apellido}"
        query = query.filter(models.Patrimonio.usuario_id == id)
    elif tipo == "destino":
        d = db.query(models.Destino).filter(models.Destino.id == id).first()
        if not d:
            raise HTTPException(status_code=404, detail="Destino no encontrado")
        nombre = d.nombre
        query = query.filter(models.Patrimonio.destino_id == id)
    else:
        if not texto:
            raise HTTPException(status_code=400, detail="Falta el parámetro texto")
        nombre = texto
        texto_norm = func.upper(func.trim(models.Patrimonio.usuario_destino))
        query = query.filter(
            texto_norm == texto.upper(),
            models.Patrimonio.usuario_id.is_(None),
            models.Patrimonio.destino_id.is_(None),
        )

    bienes = query.order_by(models.Patrimonio.tipo, models.Patrimonio.numero_inventario).all()

    items = []
    for b in bienes:
        items.append({
            "numero_inventario": b.numero_inventario,
            "tipo": b.tipo or "",
            "descripcion": b.descripcion_bien or b.descripcion_item or "",
            "marca": b.marca or "",
            "modelo": b.modelo or "",
            "serie": b.serie or "",
            "nombre_de_equipo": b.nombre_de_equipo or "",
            "puesto": b.puesto or "",
            "anio": b.anio or "",
            "estado": b.estado or "",
        })

    return {"tipo": tipo, "id": id, "nombre": nombre, "items": items, "total": len(items)}

@router.post("/asignaciones/reconciliar")
def reconciliar_asignaciones_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY),
    ip: str = Depends(get_client_ip)
):
    """Vincula retroactivamente los bienes que tienen texto de usuario/destino
    pero ningún vínculo a usuario o lugar."""
    servicio = PatrimonioService(db)
    resultado = servicio.reconciliar_asignaciones(usuario_admin=usuario_actual, ip=ip)

    uid = _obtener_usuario_id(db, usuario_actual)
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="RECONCILIAR_ASIGNACIONES",
            detalle=f"Reconciliación: {resultado['vinculados_a_usuario']} usuarios, {resultado['vinculados_a_lugar']} lugares, {len(resultado['pendientes'])} tipos pendientes",
            ip_address=request.client.host
        )
    return resultado

@router.post("/importar-informatica")
async def importar_excel_informatica_endpoint(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: dict = Depends(verificar_usuario_autenticado),
    reactivar_desactualizados: bool = Form(False)
):
    ip = request.client.host
    service = PatrimonioService(db)
    resultado = await service.importar_excel_informatica(file, usuario.get("sub"), ip, reactivar_desactualizados=reactivar_desactualizados)

    uid = usuario.get("id")
    if uid:
        registrar_evento(
            db, usuario_id=uid, accion="IMPORTAR_INFORMATICA",
            detalle=f"Importación informática desde archivo: {file.filename}",
            ip_address=request.client.host
        )
    return resultado