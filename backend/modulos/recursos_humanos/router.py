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

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.modulos.auth.dependencies import verificar_usuario_autenticado
from backend.modulos.usuarios.models import User
from backend.modulos.auditoria.service import registrar_evento

import json

from . import schemas, excel_home_office, excel_horarios, nombres
from .franjas import leer_franja
from .models import (Marcacion, HomeOfficeDia, PeriodoSinControl, PersonalHorario, HorarioHistorial,
                     DIAS_SEMANA, TIPOS_DIA, TIPO_POR_DEFECTO)

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


def _franjas_guardadas(db: Session) -> dict:
    """{usuario_id: [texto de la franja lunes..viernes]}"""
    salida = {}
    for usuario_id, dia, franja in db.query(HomeOfficeDia.usuario_id, HomeOfficeDia.dia_semana, HomeOfficeDia.franja):
        if 0 <= dia < len(DIAS_SEMANA):
            salida.setdefault(usuario_id, [None] * len(DIAS_SEMANA))[dia] = franja
    return salida


def _guardar_semana(db: Session, usuario_id: int, dias: List[str], actual: dict,
                    franjas: Optional[List[Optional[str]]] = None):
    """Cambia Home / Convocado de cada día. Si vienen `franjas`, también el horario de cada día
    (vacío = sin horario); si no vienen, se conserva el horario cargado."""
    filas = {f.dia_semana: f for f in db.query(HomeOfficeDia).filter(HomeOfficeDia.usuario_id == usuario_id)}
    for d, tipo in enumerate(dias):
        fila = filas.get(d)
        if fila is None:
            fila = HomeOfficeDia(usuario_id=usuario_id, dia_semana=d, tipo=tipo)
            db.add(fila)
        if franjas is not None:
            f = leer_franja(franjas[d])
            if f is None:
                tipo = "SIN_HORARIO"
                fila.franja = fila.hora_desde = fila.hora_hasta = fila.lugar = None
            else:
                if tipo == "SIN_HORARIO":
                    tipo = "CONVOCADO"
                if f.remoto:  # escribieron la R en el horario
                    tipo = "HOME"
                fila.franja = (f.limpio or f.texto)[:80] if f.limpio or not f.remoto else None
                fila.hora_desde, fila.hora_hasta = f.desde, f.hasta
                fila.lugar = f.lugar[:60] if f.lugar else None
        fila.tipo = tipo
        fila.modificado_por_id = actual.get("id")
        fila.fecha_modificacion = datetime.utcnow()
    registrar_historial(db, usuario_id, actual)


def registrar_historial(db: Session, usuario_id: int, actual: dict, hoy: Optional[date] = None):
    """Compara la semana actual de la persona con su historial y registra los días que cambiaron:
    cierra la vigencia anterior el día de ayer y abre una nueva desde hoy (si cambió dos veces
    en el mismo día, se corrige la de hoy)."""
    hoy = hoy or date.today()
    db.flush()
    actuales = {f.dia_semana: f for f in db.query(HomeOfficeDia).filter(HomeOfficeDia.usuario_id == usuario_id)}
    abiertos = {h.dia_semana: h for h in db.query(HorarioHistorial).filter(
        HorarioHistorial.usuario_id == usuario_id, HorarioHistorial.vigente_hasta.is_(None))}
    for d in range(len(DIAS_SEMANA)):
        f = actuales.get(d)
        valores = (f.tipo, f.franja, f.hora_desde, f.hora_hasta, f.lugar) if f else (TIPO_POR_DEFECTO, None, None, None, None)
        h = abiertos.get(d)
        if h is not None and (h.tipo, h.franja, h.hora_desde, h.hora_hasta, h.lugar) == valores:
            continue
        if h is not None and h.vigente_desde >= hoy:
            h.tipo, h.franja, h.hora_desde, h.hora_hasta, h.lugar = valores
            h.modificado_por_id = actual.get("id")
            h.fecha_registro = datetime.utcnow()
            continue
        if h is not None:
            h.vigente_hasta = hoy - timedelta(days=1)
        tipo, franja, desde, hasta, lugar = valores
        db.add(HorarioHistorial(usuario_id=usuario_id, dia_semana=d, tipo=tipo, franja=franja,
                                hora_desde=desde, hora_hasta=hasta, lugar=lugar, vigente_desde=hoy,
                                modificado_por_id=actual.get("id")))


def horario_en_fecha(db: Session, usuario_id: int, fecha: date) -> Optional[HorarioHistorial]:
    """Horario que tenía la persona ese día (None si es fin de semana o no había nada registrado)."""
    if fecha.weekday() >= len(DIAS_SEMANA):
        return None
    return (db.query(HorarioHistorial)
            .filter(HorarioHistorial.usuario_id == usuario_id, HorarioHistorial.dia_semana == fecha.weekday(),
                    HorarioHistorial.vigente_desde <= fecha,
                    or_(HorarioHistorial.vigente_hasta.is_(None), HorarioHistorial.vigente_hasta >= fecha))
            .order_by(HorarioHistorial.vigente_desde.desc()).first())


def _guardar_observacion(db: Session, usuario_id: int, observacion: Optional[str]):
    ph = db.query(PersonalHorario).filter(PersonalHorario.usuario_id == usuario_id).first()
    if ph is None:
        ph = PersonalHorario(usuario_id=usuario_id)
        db.add(ph)
    ph.observacion = (observacion or "").strip() or None


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
    franjas = _franjas_guardadas(db)
    planilla = {p.usuario_id: p for p in db.query(PersonalHorario)}
    # Sector y datos personales salen del módulo de Usuarios; de la planilla solo los horarios y observaciones
    usuarios.sort(key=lambda u: ((u.sector.nombre if u.sector else "￿").upper(),
                                 (u.apellido or "").upper(), (u.nombre or "").upper()))
    return [
        schemas.HomeOfficeUsuario(
            usuario_id=u.id, apellido=u.apellido, nombre=u.nombre, cuil=u.cuil,
            sector=u.sector.nombre if u.sector else None, dias=dias.get(u.id, _semana_por_defecto()),
            sin_control=sin_control.get(u.id, sin_control.get(None)),
            franjas=franjas.get(u.id, [None] * len(DIAS_SEMANA)),
            area=planilla[u.id].area if u.id in planilla else None,
            subsector=planilla[u.id].subsector if u.id in planilla else None,
            observacion=planilla[u.id].observacion if u.id in planilla else None,
            cod_reg=u.cod_reg,
            puesto=u.puesto,
            reparticion=u.reparticion,
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
    cambios = {c.usuario_id: c for c in datos.cambios}
    semanas = {c.usuario_id: _validar_semana(c.dias) for c in datos.cambios}
    for c in datos.cambios:
        if c.franjas is not None and len(c.franjas) != len(DIAS_SEMANA):
            raise HTTPException(status_code=400, detail="Hay que mandar un horario por cada día de lunes a viernes.")
    usuarios = {u.id: u for u in db.query(User).filter(User.id.in_(semanas.keys()))}
    faltan = [str(i) for i in semanas if i not in usuarios]
    if faltan:
        raise HTTPException(status_code=404, detail=f"No se encontraron los usuarios: {', '.join(faltan)}. No se guardó nada.")

    for usuario_id, dias in semanas.items():
        c = cambios[usuario_id]
        _guardar_semana(db, usuario_id, dias, actual, c.franjas)
        if "observacion" in c.model_fields_set:
            _guardar_observacion(db, usuario_id, c.observacion)
    db.commit()
    guardadas = _semanas_guardadas(db)
    franjas = _franjas_guardadas(db)
    for usuario_id in semanas:
        u, c = usuarios[usuario_id], cambios[usuario_id]
        texto = _texto_semana(u, guardadas.get(usuario_id, semanas[usuario_id]))
        if c.franjas is not None:
            texto += " | horarios: " + ", ".join(f"{DIAS_SEMANA[d][:3]} {f or '—'}" for d, f in enumerate(franjas.get(usuario_id, [None] * 5)))
        if "observacion" in c.model_fields_set:
            texto += f" | observaciones: {(c.observacion or '').strip() or '(vacío)'}"
        _auditar(db, actual, request, texto[:1000])
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



# ---------------------------------------------------------------------------
# Planilla de horarios de RRHH ("2026 HORARIOS.xlsx"): importar y exportar
# ---------------------------------------------------------------------------
def _clave_fila(p: dict) -> str:
    return f"{p['hoja']}|{p['fila']}"


def _dia_resumen(tipo: Optional[str], texto: Optional[str]) -> dict:
    return {"tipo": tipo or TIPO_POR_DEFECTO, "texto": texto}


def aplicar_fila_planilla(db: Session, usuario_id: int, p: dict, orden: int, actual: dict) -> PersonalHorario:
    """Carga una fila de la planilla de horarios para un usuario: reemplaza su semana y sus datos de planilla."""
    db.query(HomeOfficeDia).filter(HomeOfficeDia.usuario_id == usuario_id).delete()
    for i, d in enumerate(p["dias"]):
        db.add(HomeOfficeDia(
            usuario_id=usuario_id, dia_semana=i, tipo=d["tipo"], franja=d["texto"],
            hora_desde=d["desde"], hora_hasta=d["hasta"], lugar=d["lugar"],
            modificado_por_id=actual.get("id"),
        ))
    ph = db.query(PersonalHorario).filter(PersonalHorario.usuario_id == usuario_id).first()
    if ph is None:
        ph = PersonalHorario(usuario_id=usuario_id)
        db.add(ph)
    ph.area, ph.subsector, ph.observacion, ph.color = p["hoja"], p["subsector"], p["observacion"], p["color"]
    ph.nombre_planilla = p["nombre"][:150]
    ph.orden = orden
    ph.fecha_importacion = datetime.utcnow()
    registrar_historial(db, usuario_id, actual)
    return ph


@router.post("/horarios/importar")
async def importar_horarios(
    request: Request,
    archivo: UploadFile = File(...),
    vinculos: Optional[str] = Form(None, description='JSON {"HOJA|fila": usuario_id} para los nombres elegidos a mano'),
    simular: bool = Query(False, description="true = solo comparar con lo guardado, sin grabar"),
    db: Session = Depends(get_db), actual=Depends(_home_office),
):
    """Importa la planilla de horarios de RRHH (una hoja por área).
    Busca a cada persona por apellido y nombre; los que no se encuentran se pueden vincular a mano
    con `vinculos`. A quien está en la planilla se le reemplaza la semana completa (franja + Home/Convocado);
    a quien no está, no se le toca nada."""
    contenido = await archivo.read()
    if len(contenido) > MAX_EXCEL_BYTES:
        raise HTTPException(status_code=400, detail="El archivo supera los 5 MB.")
    try:
        datos = excel_horarios.leer(contenido)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo. Tiene que ser un Excel .xlsx.")
    if not datos["personas"]:
        raise HTTPException(status_code=400, detail="No encontré personas: revisá que cada hoja tenga APELLIDO Y NOMBRES y LUNES a VIERNES.")
    try:
        elegidos = {str(k): int(v) for k, v in (json.loads(vinculos) if vinculos else {}).items() if v}
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=400, detail="El campo vinculos no es válido.")

    usuarios = db.query(User).filter(User.estado == "ACTIVO").all()
    por_id = {u.id: u for u in usuarios}
    actuales = {}
    for f in db.query(HomeOfficeDia):
        if 0 <= f.dia_semana < len(DIAS_SEMANA):
            actuales.setdefault(f.usuario_id, [_dia_resumen(None, None) for _ in DIAS_SEMANA])[f.dia_semana] = \
                _dia_resumen(f.tipo, f.franja)
    planilla = {p.usuario_id: p for p in db.query(PersonalHorario)}

    avisos = list(datos["avisos"])
    no_encontrados, diferencias, asignados = [], [], {}
    actualizados = sin_cambios = 0
    colores = {}

    for orden, p in enumerate(datos["personas"]):
        clave = _clave_fila(p)
        if p["color"]:
            c = colores.setdefault(p["color"], {"color": p["color"], "cantidad": 0, "ejemplos": []})
            c["cantidad"] += 1
            if len(c["ejemplos"]) < 4:
                c["ejemplos"].append(p["nombre"])

        u = por_id.get(elegidos[clave]) if clave in elegidos else None
        if u is None:
            u, candidatos = nombres.vincular(p["nombre"], usuarios)
            if u is None:
                no_encontrados.append({
                    "clave": clave, "hoja": p["hoja"], "fila": p["fila"], "nombre": p["nombre"],
                    "candidatos": [{"id": c.id, "nombre": f"{c.apellido}, {c.nombre}"} for c in candidatos],
                })
                continue
        if u.id in asignados:
            avisos.append(f"{p['hoja']}, fila {p['fila']} ({p['nombre']}): ya estaba en {asignados[u.id]}; vale esta fila.")
        asignados[u.id] = f"{p['hoja']}, fila {p['fila']}"

        despues = [_dia_resumen(d["tipo"], d["texto"]) for d in p["dias"]]
        antes = actuales.get(u.id, [_dia_resumen(None, None) for _ in DIAS_SEMANA])
        ph = planilla.get(u.id)
        # El sector sale de Usuarios: de la planilla solo importan horarios, observación y color
        mismos_datos = ph is not None and (ph.observacion, ph.color) == (p["observacion"], p["color"])
        if antes == despues and mismos_datos:
            sin_cambios += 1
        else:
            actualizados += 1
            if antes != despues:
                diferencias.append({"usuario_id": u.id, "nombre": f"{u.apellido}, {u.nombre}",
                                    "planilla": p["nombre"], "hoja": p["hoja"], "antes": antes, "despues": despues})

        if not simular:
            planilla[u.id] = aplicar_fila_planilla(db, u.id, p, orden, actual)

    resultado = {
        "simulacion": simular, "personas": len(datos["personas"]), "hojas": datos["hojas"],
        "vinculados": len(asignados), "actualizados": actualizados, "sin_cambios": sin_cambios,
        "no_encontrados": no_encontrados, "diferencias": diferencias, "avisos": avisos,
        "colores": sorted(colores.values(), key=lambda c: -c["cantidad"]),
    }
    if simular:
        db.rollback()
        return resultado
    db.commit()
    _auditar(db, actual, request, f"Importación de horarios ({archivo.filename}): {len(asignados)} personas, "
                                  f"{actualizados} con cambios, {len(no_encontrados)} sin vincular")
    return resultado


@router.get("/horarios/exportar", dependencies=[Depends(_home_office)])
def exportar_horarios(db: Session = Depends(get_db)):
    """Excel con el mismo formato que la planilla de RRHH: una hoja por área, R en amarillo."""
    colores = {p.usuario_id: p.color for p in db.query(PersonalHorario)}
    personas = [{
        "area": u.sector or "SIN SECTOR", "subsector": None, "apellido": u.apellido, "nombre": u.nombre,
        "observacion": u.observacion, "cod_reg": u.cod_reg, "color": colores.get(u.usuario_id),
        "dias": [{"tipo": t, "texto": f} for t, f in zip(u.dias, u.franjas)],
    } for u in tablero_home_office(db)]
    return Response(
        excel_horarios.exportar(personas),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Horarios_{date.today():%Y-%m-%d}.xlsx"},
    )



# ---------------------------------------------------------------------------
# Historial de horarios
# ---------------------------------------------------------------------------
def _hora(t) -> Optional[str]:
    return t.strftime("%H:%M") if t else None


@router.get("/horarios/historial/{usuario_id}", dependencies=[Depends(_home_office)])
def historial_horarios(usuario_id: int, db: Session = Depends(get_db)):
    """Vigencias del horario de una persona, de la más reciente a la más vieja."""
    u = db.query(User).filter(User.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    filas = (db.query(HorarioHistorial).filter(HorarioHistorial.usuario_id == usuario_id)
             .order_by(HorarioHistorial.vigente_desde.desc(), HorarioHistorial.dia_semana).all())
    autores = {x.id: f"{x.apellido}, {x.nombre}" for x in db.query(User).filter(
        User.id.in_({h.modificado_por_id for h in filas if h.modificado_por_id}))}
    return {
        "usuario": f"{u.apellido}, {u.nombre}",
        "vigencias": [{
            "dia": DIAS_SEMANA[h.dia_semana], "dia_semana": h.dia_semana, "tipo": h.tipo, "franja": h.franja,
            "desde": _hora(h.hora_desde), "hasta": _hora(h.hora_hasta), "lugar": h.lugar,
            "vigente_desde": h.vigente_desde, "vigente_hasta": h.vigente_hasta,
            "modificado_por": autores.get(h.modificado_por_id),
        } for h in filas],
    }


@router.get("/horarios/en-fecha", dependencies=[Depends(_home_office)])
def horarios_en_fecha(fecha: date, db: Session = Depends(get_db)):
    """Horario de cada persona en una fecha (para cruzar con las fichadas de ese día)."""
    if fecha.weekday() >= len(DIAS_SEMANA):
        return {"fecha": fecha, "dia": None, "personas": []}
    filas = (db.query(HorarioHistorial, User).join(User, HorarioHistorial.usuario_id == User.id)
             .filter(HorarioHistorial.dia_semana == fecha.weekday(), HorarioHistorial.vigente_desde <= fecha,
                     or_(HorarioHistorial.vigente_hasta.is_(None), HorarioHistorial.vigente_hasta >= fecha))
             .order_by(User.apellido, User.nombre).all())
    return {
        "fecha": fecha, "dia": DIAS_SEMANA[fecha.weekday()],
        "personas": [{
            "usuario_id": u.id, "nombre": f"{u.apellido}, {u.nombre}", "cuil": u.cuil,
            "tipo": h.tipo, "franja": h.franja, "desde": _hora(h.hora_desde), "hasta": _hora(h.hora_hasta), "lugar": h.lugar,
        } for h, u in filas],
    }
