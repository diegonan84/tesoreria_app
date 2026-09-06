from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from backend import models, database
from backend.modulos.auth.dependencies import verificar_admin_actual, verificar_usuario_autenticado
from backend.modulos.notificaciones import schemas
from backend.modulos.auditoria.service import registrar_evento

router = APIRouter()

@router.post("/admin/notificaciones")
def crear_notificacion(datos: schemas.NotificacionCreate, request: Request, db: Session = Depends(database.get_db), admin=Depends(verificar_admin_actual)):
    nueva = models.NotificacionGlobal(titulo=datos.titulo, mensaje=datos.mensaje, creador_id=admin.get("id"))
    db.add(nueva)
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="CREAR_NOTIFICACION",
        detalle=f"Notificación publicada: {datos.titulo}",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": "Notificación publicada exitosamente."}

@router.get("/notificaciones/me")
def obtener_mis_notificaciones(db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    uid = usuario.get("id")
    
    registro = db.query(models.LecturaNotificacion).filter_by(usuario_id=uid).first()
    ultima_fecha = registro.ultima_lectura if registro else datetime.min

    ultimas_tres = db.query(models.NotificacionGlobal).order_by(desc(models.NotificacionGlobal.fecha_creacion)).limit(3).all()
    no_leidas = db.query(models.NotificacionGlobal).filter(models.NotificacionGlobal.fecha_creacion > ultima_fecha).count()

    return {
        "no_leidas": no_leidas,
        "ultimas": [{"titulo": n.titulo, "mensaje": n.mensaje, "fecha": n.fecha_creacion.isoformat()} for n in ultimas_tres]
    }

@router.put("/notificaciones/me/leer")
def marcar_notificaciones_leidas(db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    uid = usuario.get("id")
    registro = db.query(models.LecturaNotificacion).filter_by(usuario_id=uid).first()
    
    if not registro:
        registro = models.LecturaNotificacion(usuario_id=uid, ultima_lectura=datetime.utcnow())
        db.add(registro)
    else:
        registro.ultima_lectura = datetime.utcnow()
    
    db.commit()
    return {"mensaje": "Notificaciones marcadas como leídas"}


