from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.modulos.auth.dependencies import verificar_usuario_autenticado
from backend.modulos.auditoria.service import registrar_evento
from backend.modulos.agenda.models import RecordatorioCalendario
from backend.modulos.agenda import schemas

router = APIRouter()

def _emitir_evento(db, uid, accion, detalle, request):
    registrar_evento(
        db, usuario_id=uid, accion=accion, detalle=detalle,
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )

def _serie(ev):
    return schemas.RecordatorioResponse(
        id=ev.id, usuario_id=ev.usuario_id, titulo=ev.titulo,
        descripcion=ev.descripcion, fecha_evento=ev.fecha_evento,
        recordar_antes_min=ev.recordar_antes_min, visto=ev.visto
    ).model_dump()

# --- LISTAR EVENTOS DEL USUARIO EN UN RANGO (para el calendario) ---
@router.get("/agenda/eventos", response_model=list[schemas.RecordatorioResponse])
def listar_eventos(
    desde: datetime = None,
    hasta: datetime = None,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_usuario_autenticado)
):
    q = db.query(RecordatorioCalendario).filter(RecordatorioCalendario.usuario_id == usuario.get("id"))
    if desde:
        q = q.filter(RecordatorioCalendario.fecha_evento >= desde)
    if hasta:
        q = q.filter(RecordatorioCalendario.fecha_evento <= hasta)
    return q.order_by(RecordatorioCalendario.fecha_evento.asc()).all()

# --- CREAR EVENTO ---
@router.post("/agenda/eventos", response_model=schemas.RecordatorioResponse)
def crear_evento(
    datos: schemas.RecordatorioCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_usuario_autenticado)
):
    titulo = (datos.titulo or "").strip()
    if not titulo:
        raise HTTPException(status_code=400, detail="El título es obligatorio")
    if len(titulo) > 100:
        raise HTTPException(status_code=400, detail="El título no puede superar 100 caracteres")
    if datos.recordar_antes_min < 0 or datos.recordar_antes_min > 10080:
        raise HTTPException(status_code=400, detail="El aviso previo no es válido")

    ev = RecordatorioCalendario(
        usuario_id=usuario.get("id"),
        titulo=titulo,
        descripcion=(datos.descripcion or "").strip() or None,
        fecha_evento=datos.fecha_evento,
        recordar_antes_min=datos.recordar_antes_min
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    _emitir_evento(db, usuario.get("id"), "AGENDA_CREAR", f"Evento creado en agenda: {ev.titulo}", request)
    return ev

# --- EDITAR EVENTO ---
@router.put("/agenda/eventos/{evento_id}", response_model=schemas.RecordatorioResponse)
def actualizar_evento(
    evento_id: int,
    datos: schemas.RecordatorioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_usuario_autenticado)
):
    ev = db.query(RecordatorioCalendario).filter(
        RecordatorioCalendario.id == evento_id,
        RecordatorioCalendario.usuario_id == usuario.get("id")
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if datos.titulo is not None:
        if not (datos.titulo or "").strip():
            raise HTTPException(status_code=400, detail="El título es obligatorio")
        ev.titulo = datos.titulo.strip()
    if datos.descripcion is not None:
        ev.descripcion = datos.descripcion.strip() or None
    if datos.fecha_evento is not None:
        ev.fecha_evento = datos.fecha_evento
    if datos.recordar_antes_min is not None:
        ev.recordar_antes_min = datos.recordar_antes_min
    ev.visto = False
    db.commit()
    db.refresh(ev)

    _emitir_evento(db, usuario.get("id"), "AGENDA_EDITAR", f"Evento editado: {ev.titulo}", request)
    return ev

# --- BORRAR EVENTO ---
@router.delete("/agenda/eventos/{evento_id}")
def eliminar_evento(
    evento_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario=Depends(verificar_usuario_autenticado)
):
    ev = db.query(RecordatorioCalendario).filter(
        RecordatorioCalendario.id == evento_id,
        RecordatorioCalendario.usuario_id == usuario.get("id")
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    db.delete(ev)
    db.commit()

    _emitir_evento(db, usuario.get("id"), "AGENDA_BORRAR", f"Evento eliminado de agenda: {ev.titulo}", request)
    return {"mensaje": "Evento eliminado correctamente"}

# --- PENDIENTES / PRÓXIMOS PARA LA CAMPANA ---
# pendientes: el momento del recordatorio ya llegó y no fue visto aún (cuentan en el globo)
# proximos: eventos por vencer dentro de 7 días (informativo, sin globo)
@router.get("/agenda/pendientes")
def obtener_pendientes(db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    ahora = datetime.utcnow()
    uid = usuario.get("id")

    pendientes = []
    proximos = []
    cuenta = 0

    eventos = db.query(RecordatorioCalendario).filter(
        RecordatorioCalendario.usuario_id == uid,
        RecordatorioCalendario.fecha_evento >= ahora - timedelta(minutes=30)
    ).order_by(RecordatorioCalendario.fecha_evento.asc()).all()

    for ev in eventos:
        horario_recordatorio = ev.fecha_evento - timedelta(minutes=ev.recordar_antes_min or 0)
        item = _serie(ev)
        if horario_recordatorio <= ahora and not ev.visto:
            pendientes.append(item)
            cuenta += 1
        elif len(proximos) < 5 and ev.fecha_evento <= ahora + timedelta(days=7):
            proximos.append(item)

    return {"cuenta": cuenta, "pendientes": pendientes, "proximos": proximos}

# --- MARCAR UNO COMO VISTO (descartar) ---
@router.post("/agenda/eventos/{evento_id}/visto")
def marcar_visto(evento_id: int, db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    ev = db.query(RecordatorioCalendario).filter(
        RecordatorioCalendario.id == evento_id,
        RecordatorioCalendario.usuario_id == usuario.get("id")
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    ev.visto = True
    db.commit()
    return {"mensaje": "Recordatorio marcado como leído"}

# --- MARCAR TODOS LOS PENDIENTES COMO VISTOS (al abrir la campana) ---
@router.put("/agenda/pendientes/visto")
def marcar_todos_visto(db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    uid = usuario.get("id")
    ahora = datetime.utcnow()
    pendientes = db.query(RecordatorioCalendario).filter(
        RecordatorioCalendario.usuario_id == uid,
        RecordatorioCalendario.visto == False,
        RecordatorioCalendario.fecha_evento >= ahora - timedelta(minutes=30)
    ).all()
    for ev in pendientes:
        horario_recordatorio = ev.fecha_evento - timedelta(minutes=ev.recordar_antes_min or 0)
        if horario_recordatorio <= ahora:
            ev.visto = True
    db.commit()
    return {"mensaje": "Recordatorios marcados como leídos"}