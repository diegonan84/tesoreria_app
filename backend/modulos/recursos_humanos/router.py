"""
Recursos Humanos - Control de Fichadas
--------------------------------------
Acceso: módulo "RRHH" / página "RRHH_Fichadas" habilitados por usuario, o rol Administrador.
Los códigos coinciden con CATALOGO_PERMISOS en frontend/js/app.js.
"""
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.modulos.auth.dependencies import verificar_usuario_autenticado
from backend.modulos.usuarios.models import User

from . import schemas
from .models import Marcacion

ROLES_MODULO_RRHH = {"RRHH", "RRHH_Fichadas", "Administrador"}


def _requiere_modulo_rrhh(usuario=Depends(verificar_usuario_autenticado)):
    if not ROLES_MODULO_RRHH.intersection(usuario.get("roles", []) or []):
        raise HTTPException(status_code=403, detail="No tenés habilitado el módulo Recursos Humanos.")
    return usuario


router = APIRouter(prefix="/api/rrhh", tags=["Recursos Humanos"], dependencies=[Depends(_requiere_modulo_rrhh)])


@router.get("/marcaciones", response_model=List[schemas.MarcacionOut])
def listar_marcaciones(
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    q: Optional[str] = Query(None, description="Identificador, nombre o apellido"),
    limite: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """Fichadas crudas del período (por defecto, el día de hoy)."""
    desde = desde or date.today()
    hasta = hasta or desde
    if hasta < desde:
        raise HTTPException(status_code=400, detail="La fecha 'hasta' es anterior a 'desde'.")

    consulta = (
        db.query(Marcacion)
        .options(joinedload(Marcacion.usuario))
        .outerjoin(User, Marcacion.usuario_id == User.id)
        .filter(Marcacion.fecha_hora >= datetime.combine(desde, time.min))
        .filter(Marcacion.fecha_hora < datetime.combine(hasta + timedelta(days=1), time.min))
    )
    if q and q.strip():
        patron = f"%{q.strip()}%"
        consulta = consulta.filter(or_(
            Marcacion.identificador.ilike(patron), User.nombre.ilike(patron), User.apellido.ilike(patron),
        ))

    filas = consulta.order_by(Marcacion.fecha_hora.desc()).limit(limite).all()
    return [
        schemas.MarcacionOut(
            id=m.id, identificador=m.identificador, usuario_id=m.usuario_id,
            empleado=f"{m.usuario.apellido}, {m.usuario.nombre}" if m.usuario else None,
            fecha_hora=m.fecha_hora, tipo=m.tipo, origen=m.origen, dispositivo=m.dispositivo,
        )
        for m in filas
    ]
