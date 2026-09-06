from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend import models, database
from backend.modulos.auth.dependencies import verificar_admin_actual
from backend.modulos.auditoria.models import RegistroAuditoria

router = APIRouter()


@router.get("/admin/auditoria")
def listar_auditoria(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    usuario_id: int = Query(None),
    accion: str = Query(None),
    fecha_desde: str = Query(None),
    fecha_hasta: str = Query(None),
    buscar: str = Query(None),
    db: Session = Depends(database.get_db),
    admin=Depends(verificar_admin_actual)
):
    query = db.query(RegistroAuditoria)

    if usuario_id:
        query = query.filter(RegistroAuditoria.usuario_id == usuario_id)

    if accion:
        query = query.filter(RegistroAuditoria.accion == accion)

    if fecha_desde:
        from datetime import datetime
        try:
            fd = datetime.fromisoformat(fecha_desde)
            query = query.filter(RegistroAuditoria.fecha >= fd)
        except ValueError:
            pass

    if fecha_hasta:
        from datetime import datetime
        try:
            fh = datetime.fromisoformat(fecha_hasta)
            query = query.filter(RegistroAuditoria.fecha <= fh)
        except ValueError:
            pass

    if buscar:
        query = query.join(RegistroAuditoria.usuario).filter(
            models.User.nombre.ilike(f"%{buscar}%") |
            models.User.apellido.ilike(f"%{buscar}%") |
            RegistroAuditoria.detalle.ilike(f"%{buscar}%") |
            RegistroAuditoria.accion.ilike(f"%{buscar}%")
        )

    total = query.count()
    logs = query.order_by(desc(RegistroAuditoria.fecha)).offset(skip).limit(limit).all()

    resultado = []
    for log in logs:
        resultado.append({
            "id": log.id,
            "fecha": log.fecha,
            "accion": log.accion,
            "detalle": log.detalle,
            "usuario": f"{log.usuario.nombre} {log.usuario.apellido}",
            "usuario_id": log.usuario_id,
            "reparticion": log.usuario.reparticion,
            "ip_address": log.ip_address,
            "pc_nombre": log.pc_nombre,
            "pc_usuario": log.pc_usuario
        })

    return {"total": total, "registros": resultado}


@router.get("/admin/auditoria/acciones")
def listar_acciones_disponibles(
    db: Session = Depends(database.get_db),
    admin=Depends(verificar_admin_actual)
):
    acciones = db.query(RegistroAuditoria.accion).distinct().all()
    return [a[0] for a in acciones]


@router.get("/admin/auditoria/usuarios")
def listar_usuarios_en_auditoria(
    db: Session = Depends(database.get_db),
    admin=Depends(verificar_admin_actual)
):
    usuarios = db.query(
        RegistroAuditoria.usuario_id,
        models.User.nombre,
        models.User.apellido
    ).join(models.User, RegistroAuditoria.usuario_id == models.User.id).distinct().all()

    return [{"id": u[0], "nombre": f"{u[1]} {u[2]}"} for u in usuarios]
