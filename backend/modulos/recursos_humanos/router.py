"""
Recursos Humanos - Control de Fichadas
--------------------------------------
Acceso por página, con los mismos códigos que CATALOGO_PERMISOS en frontend/js/app.js:
  - RRHH_Fichadas   → Control de Fichadas
  - RRHH_HomeOffice → Tablero de Home Office
Igual que en el frontend: el código de módulo "RRHH" sin ninguna página tildada da acceso a todas,
y Administrador entra a todo.
"""
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.modulos.auth.dependencies import verificar_usuario_autenticado
from backend.modulos.usuarios.models import User
from backend.modulos.auditoria.service import registrar_evento

from . import schemas, excel_home_office
from .models import Marcacion, HomeOfficeDia, PeriodoSinControl, DIAS_SEMANA, TIPOS_DIA, TIPO_POR_DEFECTO

PAGINAS_RRHH = ("RRHH_Fichadas", "RRHH_HomeOffice")


def _tiene_pagina(roles, pagina: str) -> bool:
    if "Administrador" in roles or pagina in roles:
        return True
    return "RRHH" in roles and not any(p in roles for p in PAGINAS_RRHH)


def _requiere_pagina(pagina: str, nombre: str):
    def dependencia(usuario=Depends(verificar_usuario_autenticado)):
        if not _tiene_pagina(usuario.get("roles", []) or [], pagina):
            raise HTTPException(status_code=403, detail=f"No tenés habilitado {nombre}.")
        return usuario
    return dependencia


_fichadas = _requiere_pagina("RRHH_Fichadas", "Control de Fichadas")
_home_office = _requiere_pagina("RRHH_HomeOffice", "el Tablero de Home Office")

router = APIRouter(prefix="/api/rrhh", tags=["Recursos Humanos"])


@router.get("/marcaciones", response_model=List[schemas.MarcacionOut], dependencies=[Depends(_fichadas)])
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



# ---------------------------------------------------------------------------
# Tablero de Home Office
# ---------------------------------------------------------------------------
def _auditar(db: Session, actual: dict, request: Request, detalle: str):
    registrar_evento(
        db, usuario_id=actual.get("id"), accion="RRHH_HOME_OFFICE", detalle=detalle,
        ip_address=request.client.host if request.client else None,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido"),
    )


def _semana_por_defecto() -> List[str]:
    return [TIPO_POR_DEFECTO] * len(DIAS_SEMANA)


def _semanas_guardadas(db: Session) -> dict:
    """{usuario_id: [tipo lunes..viernes]}; los días sin fila quedan CONVOCADO."""
    semanas = {}
    for usuario_id, dia, tipo in db.query(HomeOfficeDia.usuario_id, HomeOfficeDia.dia_semana, HomeOfficeDia.tipo):
        if 0 <= dia < len(DIAS_SEMANA):
            semanas.setdefault(usuario_id, _semana_por_defecto())[dia] = tipo
    return semanas


def _guardar_semana(db: Session, usuario_id: int, dias: List[str], actual: dict):
    db.query(HomeOfficeDia).filter(HomeOfficeDia.usuario_id == usuario_id).delete()
    for d, tipo in enumerate(dias):
        db.add(HomeOfficeDia(usuario_id=usuario_id, dia_semana=d, tipo=tipo, modificado_por_id=actual.get("id")))


@router.get("/home-office", response_model=List[schemas.HomeOfficeUsuario], dependencies=[Depends(_home_office)])
def tablero_home_office(db: Session = Depends(get_db)):
    """Usuarios activos con la marca de cada día (Home / Convocado; por defecto Convocado)."""
    usuarios = (
        db.query(User).options(joinedload(User.sector))
        .filter(User.estado == "ACTIVO")
        .order_by(User.apellido, User.nombre).all()
    )
    dias = _semanas_guardadas(db)
    sin_control = _sin_control_hoy(db)
    return [
        schemas.HomeOfficeUsuario(
            usuario_id=u.id, apellido=u.apellido, nombre=u.nombre, cuil=u.cuil,
            sector=u.sector.nombre if u.sector else None, dias=dias.get(u.id, _semana_por_defecto()),
            sin_control=sin_control.get(u.id, sin_control.get(None)),
        )
        for u in usuarios
    ]


@router.get("/home-office/exportar", dependencies=[Depends(_home_office)])
def exportar_home_office(db: Session = Depends(get_db)):
    """Excel con CUIL, nombre, apellido y la marca de cada día (texto + color)."""
    filas = [f.model_dump() if hasattr(f, "model_dump") else f.dict() for f in tablero_home_office(db)]
    return Response(
        excel_home_office.exportar(filas),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Home_Office_{date.today():%Y-%m-%d}.xlsx"},
    )


MAX_EXCEL_BYTES = 5 * 1024 * 1024


@router.post("/home-office/importar")
async def importar_home_office(
    request: Request, archivo: UploadFile = File(...),
    simular: bool = Query(False, description="true = solo comparar con lo guardado, sin grabar"),
    db: Session = Depends(get_db), actual=Depends(_home_office),
):
    """Carga la semana de cada persona del Excel, buscándola por CUIL.
    Con simular=true devuelve la comparación (antes / después por persona) y no graba nada.
    La fila manda: un día vacío o verde queda Convocado. Quien no está en el archivo no se toca."""
    contenido = await archivo.read()
    if len(contenido) > MAX_EXCEL_BYTES:
        raise HTTPException(status_code=400, detail="El archivo supera los 5 MB.")
    try:
        datos = excel_home_office.leer(contenido)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo. Tiene que ser un Excel .xlsx.")

    por_cuil = {excel_home_office.solo_digitos(u.cuil): u for u in db.query(User).filter(User.estado == "ACTIVO")}
    actuales = _semanas_guardadas(db)

    actualizados, sin_cambios, problemas, vistos, diferencias = 0, 0, list(datos["problemas"]), {}, []
    for f in datos["filas"]:
        u = por_cuil.get(excel_home_office.solo_digitos(f["cuil"]))
        if not u:
            quien = f"{f['apellido']}, {f['nombre']}".strip(", ")
            problemas.append(f"Fila {f['fila']}: no hay un usuario activo con CUIL {f['cuil']}" + (f" ({quien})." if quien else "."))
            continue
        if u.id in vistos:
            problemas.append(f"Fila {f['fila']}: el CUIL {f['cuil']} ya estaba en la fila {vistos[u.id]}; vale la última.")
        vistos[u.id] = f["fila"]
        semana = [t or TIPO_POR_DEFECTO for t in f["dias"]]
        antes = actuales.get(u.id, _semana_por_defecto())
        if antes == semana:
            sin_cambios += 1
            continue
        diferencias.append({"usuario_id": u.id, "apellido": u.apellido, "nombre": u.nombre, "cuil": u.cuil,
                            "antes": antes, "despues": semana})
        if not simular:
            _guardar_semana(db, u.id, semana, actual)
        actuales[u.id] = semana
        actualizados += 1

    if simular:
        db.rollback()
        return {"simulacion": True, "actualizados": actualizados, "sin_cambios": sin_cambios,
                "problemas": problemas, "diferencias": diferencias}
    db.commit()

    _auditar(db, actual, request, f"Importación Excel ({archivo.filename}): {actualizados} actualizados, "
                                  f"{sin_cambios} sin cambios, {len(problemas)} avisos")
    return {"simulacion": False, "actualizados": actualizados, "sin_cambios": sin_cambios,
            "problemas": problemas, "diferencias": diferencias}


def _validar_semana(dias: List[Optional[str]]) -> List[str]:
    nuevos = [(t or "").strip().upper() or TIPO_POR_DEFECTO for t in dias]
    if len(nuevos) != len(DIAS_SEMANA):
        raise HTTPException(status_code=400, detail="Hay que mandar un valor por cada día de lunes a viernes.")
    if any(t not in TIPOS_DIA for t in nuevos):
        raise HTTPException(status_code=400, detail="Cada día tiene que ser Home o Convocado.")
    return nuevos


def _texto_semana(u: User, dias: List[str]) -> str:
    home = ", ".join(DIAS_SEMANA[d] for d, t in enumerate(dias) if t == "HOME") or "ninguno"
    return f"Home office de {u.apellido}, {u.nombre}: días de Home: {home}"


@router.put("/home-office", dependencies=[Depends(_home_office)])
def guardar_home_office_lote(
    datos: schemas.HomeOfficeLote, request: Request,
    db: Session = Depends(get_db), actual=Depends(_home_office),
):
    """Botón Guardar del tablero: guarda todos los cambios pendientes juntos (todo o nada)."""
    if not datos.cambios:
        return {"guardados": 0}
    semanas = {c.usuario_id: _validar_semana(c.dias) for c in datos.cambios}
    usuarios = {u.id: u for u in db.query(User).filter(User.id.in_(semanas.keys()))}
    faltan = [str(i) for i in semanas if i not in usuarios]
    if faltan:
        raise HTTPException(status_code=404, detail=f"No se encontraron los usuarios: {', '.join(faltan)}. No se guardó nada.")

    for usuario_id, dias in semanas.items():
        _guardar_semana(db, usuario_id, dias, actual)
    db.commit()
    for usuario_id, dias in semanas.items():
        _auditar(db, actual, request, _texto_semana(usuarios[usuario_id], dias))
    return {"guardados": len(semanas)}


@router.put("/home-office/{usuario_id}", response_model=schemas.HomeOfficeUsuario)
def guardar_home_office(
    usuario_id: int, datos: schemas.HomeOfficeIn, request: Request,
    db: Session = Depends(get_db), actual=Depends(_home_office),
):
    """Reemplaza las marcas de la semana del usuario (5 valores: HOME o CONVOCADO; null = CONVOCADO)."""
    u = db.query(User).options(joinedload(User.sector)).filter(User.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    nuevos = _validar_semana(datos.dias)

    _guardar_semana(db, usuario_id, nuevos, actual)
    db.commit()
    _auditar(db, actual, request, _texto_semana(u, nuevos))
    return schemas.HomeOfficeUsuario(
        usuario_id=u.id, apellido=u.apellido, nombre=u.nombre, cuil=u.cuil,
        sector=u.sector.nombre if u.sector else None, dias=nuevos,
    )



# ---------------------------------------------------------------------------
# Períodos sin control de Home / Convocado
# ---------------------------------------------------------------------------
def _fecha_corta(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _sin_control_hoy(db: Session) -> dict:
    """{usuario_id | None: "Licencia hasta 20/11/2026"} con los períodos vigentes hoy."""
    hoy = date.today()
    vigentes = {}
    for p in (db.query(PeriodoSinControl)
              .filter(PeriodoSinControl.desde <= hoy, PeriodoSinControl.hasta >= hoy)
              .order_by(PeriodoSinControl.hasta.desc())):
        vigentes.setdefault(p.usuario_id, f"{p.motivo or 'Sin control'} hasta {_fecha_corta(p.hasta)}")
    return vigentes


def _periodo_out(p: PeriodoSinControl, u: Optional[User]) -> schemas.PeriodoSinControlOut:
    hoy = date.today()
    return schemas.PeriodoSinControlOut(
        id=p.id, usuario_id=p.usuario_id, desde=p.desde, hasta=p.hasta, motivo=p.motivo,
        persona=f"{u.apellido}, {u.nombre}" if u else "Todo el personal",
        vigente=p.desde <= hoy <= p.hasta,
    )


@router.get("/sin-control", response_model=List[schemas.PeriodoSinControlOut], dependencies=[Depends(_home_office)])
def listar_sin_control(incluir_vencidos: bool = False, db: Session = Depends(get_db)):
    """Períodos vigentes y futuros (con incluir_vencidos=true, también los pasados)."""
    q = db.query(PeriodoSinControl, User).outerjoin(User, PeriodoSinControl.usuario_id == User.id)
    if not incluir_vencidos:
        q = q.filter(PeriodoSinControl.hasta >= date.today())
    return [_periodo_out(p, u) for p, u in q.order_by(PeriodoSinControl.desde, PeriodoSinControl.id)]


@router.post("/sin-control", response_model=schemas.PeriodoSinControlOut)
def crear_sin_control(
    datos: schemas.PeriodoSinControlIn, request: Request,
    db: Session = Depends(get_db), actual=Depends(_home_office),
):
    if datos.hasta < datos.desde:
        raise HTTPException(status_code=400, detail="La fecha 'hasta' es anterior a 'desde'.")
    u = None
    if datos.usuario_id is not None:
        u = db.query(User).filter(User.id == datos.usuario_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    p = PeriodoSinControl(usuario_id=datos.usuario_id, desde=datos.desde, hasta=datos.hasta,
                          motivo=(datos.motivo or "").strip()[:150] or None, creado_por_id=actual.get("id"))
    db.add(p)
    db.commit()
    db.refresh(p)
    salida = _periodo_out(p, u)
    _auditar(db, actual, request, f"Sin control Home/Convocado: {salida.persona}, "
                                  f"{_fecha_corta(p.desde)} al {_fecha_corta(p.hasta)}" + (f" ({p.motivo})" if p.motivo else ""))
    return salida


@router.delete("/sin-control/{periodo_id}")
def borrar_sin_control(periodo_id: int, request: Request, db: Session = Depends(get_db), actual=Depends(_home_office)):
    p = db.query(PeriodoSinControl).filter(PeriodoSinControl.id == periodo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Período no encontrado.")
    u = db.query(User).filter(User.id == p.usuario_id).first() if p.usuario_id else None
    texto = f"{_periodo_out(p, u).persona}, {_fecha_corta(p.desde)} al {_fecha_corta(p.hasta)}"
    db.delete(p)
    db.commit()
    _auditar(db, actual, request, f"Se quitó el período sin control: {texto}")
    return {"ok": True}
