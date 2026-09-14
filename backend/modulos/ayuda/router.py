import os
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.modulos.auth.dependencies import verificar_admin_actual, verificar_usuario_autenticado
from backend.modulos.auditoria.service import registrar_evento
from backend.modulos.ayuda.models import ManualAyuda
from backend.modulos.ayuda import schemas

router = APIRouter()

DIR_MANUALES = os.path.join("frontend", "archivos", "manuales")
EXT_PERMITIDAS = {".pdf"}
MAX_TAMANIO = 25 * 1024 * 1024  # 25 MB

def _guardar_archivo(nombre_original: str, contenido: bytes) -> str:
    """Guarda el PDF y devuelve la URL pública (dentro de /archivos/...)."""
    ext = os.path.splitext(nombre_original or "")[1].lower()
    if ext not in EXT_PERMITIDAS:
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    if len(contenido) > MAX_TAMANIO:
        raise HTTPException(status_code=400, detail="El archivo supera el máximo de 25 MB")

    os.makedirs(DIR_MANUALES, exist_ok=True)
    nombre = f"{secrets.token_hex(8)}{ext}"
    ruta = os.path.join(DIR_MANUALES, nombre)
    with open(ruta, "wb") as f:
        f.write(contenido)
    return f"/archivos/manuales/{nombre}"

def _eliminar_archivo(url: str):
    """Borra el archivo del disco si existe (solo dentro de la carpeta de manuales)."""
    if not url:
        return
    nombre = os.path.basename(url)
    ruta = os.path.join(DIR_MANUALES, nombre)
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError:
        pass

# --- LISTAR MANUALES (cualquier usuario autenticado) ---
@router.get("/ayuda/manuales", response_model=list[schemas.ManualAyudaResponse])
def listar_manuales(db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    return db.query(ManualAyuda).filter(ManualAyuda.activo == True).order_by(ManualAyuda.orden, ManualAyuda.id.desc()).all()

# --- SUBIR MANUAL (admin) ---
@router.post("/ayuda/manuales")
async def subir_manual(
    request: Request,
    file: UploadFile = File(...),
    titulo: str = Form(...),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
    admin=Depends(verificar_admin_actual)
):
    contenido = await file.read()
    url = _guardar_archivo(file.filename or "", contenido)

    manual = ManualAyuda(
        titulo=titulo.strip(),
        descripcion=descripcion.strip(),
        archivo_url=url,
        archivo_nombre=os.path.basename(file.filename or "manual.pdf")
    )
    db.add(manual)
    db.commit()
    db.refresh(manual)

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="SUBIR_MANUAL",
        detalle=f"Manual cargado: {manual.titulo}",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return manual

# --- EDITAR MANUAL (admin) ---
@router.put("/ayuda/manuales/{manual_id}", response_model=schemas.ManualAyudaResponse)
def actualizar_manual(
    manual_id: int,
    datos: schemas.ManualAyudaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(verificar_admin_actual)
):
    manual = db.query(ManualAyuda).filter(ManualAyuda.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")

    if datos.titulo is not None:
        manual.titulo = datos.titulo.strip()
    if datos.descripcion is not None:
        manual.descripcion = datos.descripcion.strip()
    if datos.orden is not None:
        manual.orden = datos.orden
    if datos.activo is not None:
        manual.activo = datos.activo
    db.commit()
    db.refresh(manual)

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="EDITAR_MANUAL",
        detalle=f"Manual editado: {manual.titulo}",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return manual

# --- BORRAR MANUAL (admin) ---
@router.delete("/ayuda/manuales/{manual_id}")
def eliminar_manual(manual_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    manual = db.query(ManualAyuda).filter(ManualAyuda.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")

    _eliminar_archivo(manual.archivo_url)
    db.delete(manual)
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="BORRAR_MANUAL",
        detalle=f"Manual eliminado: {manual.titulo}",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": "Manual eliminado correctamente"}