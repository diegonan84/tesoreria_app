from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from backend import models, utils, database
from backend.database import get_db
from collections import defaultdict
from backend.modulos.patrimonio.models import Patrimonio
from typing import List
import json
import secrets
import string

# Importamos las dependencias de seguridad desde nuestro nuevo módulo auth
from backend.modulos.auth.dependencies import verificar_admin_actual, verificar_usuario_autenticado
from backend.modulos.usuarios import schemas
from backend.modulos.auditoria.service import registrar_evento

router = APIRouter()

def _generar_clave_aleatoria(longitud: int = 12) -> str:
    """Genera una contraseña aleatoria segura."""
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        clave = ''.join(secrets.choice(chars) for _ in range(longitud))
        if (any(c.islower() for c in clave) and
            any(c.isupper() for c in clave) and
            any(c.isdigit() for c in clave) and
            any(c in "!@#$%&*" for c in clave)):
            return clave

# ✨ ENDPOINTS PARA SECTORES ✨

@router.post("/sectores", response_model=schemas.SectorResponse)
def crear_sector(sector: schemas.SectorCreate, request: Request, db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    existe = db.query(models.Sector).filter(models.Sector.nombre == sector.nombre).first()
    if existe:
        raise HTTPException(status_code=400, detail="El sector ya existe")
    
    nuevo_sector = models.Sector(nombre=sector.nombre)
    db.add(nuevo_sector)
    db.commit()
    db.refresh(nuevo_sector)

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="CREAR_SECTOR",
        detalle=f"Sector creado: {sector.nombre}",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return nuevo_sector

@router.get("/sectores", response_model=list[schemas.SectorResponse])
def listar_sectores(db: Session = Depends(get_db)):
    return db.query(models.Sector).filter(models.Sector.activo == True).all()

@router.put("/sectores/{sector_id}", response_model=schemas.SectorResponse)
def editar_sector(sector_id: int, datos: schemas.SectorCreate, request: Request, db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    sector = db.query(models.Sector).filter(models.Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector no encontrado")
    
    existe = db.query(models.Sector).filter(models.Sector.nombre == datos.nombre, models.Sector.id != sector_id).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe otro sector con ese nombre")
    
    sector.nombre = datos.nombre
    sector.color = datos.color
    db.commit()
    db.refresh(sector)

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="EDITAR_SECTOR",
        detalle=f"Sector editado: {sector.nombre} (ID: {sector_id})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return sector

# ✨ ENDPOINTS PARA USUARIOS ✨

@router.get("/admin/usuarios", response_model=list[schemas.UserResponse])
def listar_usuarios(db: Session = Depends(database.get_db), admin=Depends(verificar_admin_actual)):
    return db.query(models.User).all()

@router.put("/admin/usuarios/{user_id}/aprobar")
def aprobar_usuario(user_id: int, request: Request, db: Session = Depends(database.get_db), admin=Depends(verificar_admin_actual)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.activo = True
    user.aprobado = True
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="APROBAR_USUARIO",
        detalle=f"Usuario aprobado: {user.nombre} {user.apellido} ({user.email})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": f"Usuario {user.email} aprobado correctamente"}

@router.put("/admin/usuarios/{user_id}/baja")
def dar_de_baja_usuario(user_id: int, request: Request, db: Session = Depends(database.get_db), admin=Depends(verificar_admin_actual)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not user.activo:
        raise HTTPException(status_code=400, detail="El usuario ya se encuentra dado de baja")
    user.activo = False
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="BAJA_USUARIO",
        detalle=f"Usuario dado de baja: {user.nombre} {user.apellido} ({user.email})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": f"Usuario {user.email} dado de baja correctamente"}

@router.put("/admin/usuarios/{user_id}/alta")
def dar_de_alta_usuario(user_id: int, request: Request, db: Session = Depends(database.get_db), admin=Depends(verificar_admin_actual)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.activo:
        raise HTTPException(status_code=400, detail="El usuario ya se encuentra activo")
    user.activo = True
    user.aprobado = True
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="ALTA_USUARIO",
        detalle=f"Usuario reactivado: {user.nombre} {user.apellido} ({user.email})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": f"Usuario {user.email} dado de alta correctamente"}

@router.put("/admin/usuarios/{user_id}/editar")
def editar_usuario_completo(user_id: int, datos: schemas.UserUpdate, request: Request, db: Session = Depends(database.get_db), admin=Depends(verificar_admin_actual)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.nombre = datos.nombre
    user.apellido = datos.apellido
    user.cuil = datos.cuil
    user.email = datos.email
    user.reparticion = datos.reparticion
    user.puesto = datos.puesto  
    user.sector_id = datos.sector_id 
    user.roles = ",".join(datos.roles) if datos.roles else "Operador"
    
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="EDITAR_USUARIO",
        detalle=f"Usuario editado: {user.nombre} {user.apellido} (ID: {user_id})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": "Usuario modificado con éxito"}

@router.post("/admin/usuarios/manual")
def crear_usuario_manual(datos: schemas.UserUpdate, request: Request, db: Session = Depends(database.get_db), admin=Depends(verificar_admin_actual)):
    if db.query(models.User).filter(models.User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="Error: El correo electrónico ya está registrado.")
    if db.query(models.User).filter(models.User.cuil == datos.cuil).first():
        raise HTTPException(status_code=400, detail="Error: El CUIL ya se encuentra registrado.")
        
    nuevo_usuario = models.User(
        nombre=datos.nombre, 
        apellido=datos.apellido, 
        cuil=datos.cuil,
        email=datos.email, 
        reparticion=datos.reparticion,
        puesto=datos.puesto,
        sector_id=datos.sector_id,
        password_hash=utils.get_password_hash(_generar_clave_aleatoria()),
        activo=True,
        aprobado=True,
        roles=",".join(datos.roles) if datos.roles else "Operador"
    )
    db.add(nuevo_usuario)
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="CREAR_USUARIO_MANUAL",
        detalle=f"Usuario creado: {datos.nombre} {datos.apellido} ({datos.email})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": "Usuario creado exitosamente. Se generó una contraseña aleatoria segura."}

@router.put("/usuarios/me/cambiar-clave")
def cambiar_mi_clave(datos: schemas.PasswordChange, request: Request, db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    email_usuario = usuario.get("sub")
    user = db.query(models.User).filter(models.User.email == email_usuario).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if not utils.verify_password(datos.clave_actual, user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual ingresada es incorrecta.")
        
    user.password_hash = utils.get_password_hash(datos.nueva_clave)
    db.commit()

    registrar_evento(
        db, usuario_id=usuario.get("id"), accion="CAMBIAR_CONTRASENA",
        detalle=f"Usuario cambió su propia contraseña",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": "Contraseña actualizada correctamente"}

# ✨ NUEVOS ENDPOINTS PARA EL MAPA INTERACTIVO CON PATRIMONIO ✨

@router.get("/mapas-disponibles")
def listar_mapas(db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    mapas = db.query(models.MapaGrid).all()
    return [{"id": m.id, "titulo": m.titulo} for m in mapas]

@router.get("/mapa-puestos")
def obtener_estado_mapa(mapa_id: int = Query(...), db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    mapa_db = db.query(models.MapaGrid).filter(models.MapaGrid.id == mapa_id).first()
    if not mapa_db:
        raise HTTPException(status_code=404, detail="Mapa no encontrado.")

    celdas_activas = [c for c in mapa_db.celdas if c.habilitado and c.numero_puesto]
    puestos_ids = [c.numero_puesto for c in celdas_activas]

    equipos = db.query(Patrimonio).filter(Patrimonio.puesto.in_(puestos_ids)).all()
    puesto_a_equipos = defaultdict(list)
    for eq in equipos:
        if eq.puesto:
            puesto_a_equipos[eq.puesto].append(eq)

    usuarios = db.query(models.User).filter(models.User.puesto.in_(puestos_ids)).all()
    puesto_a_usuarios = defaultdict(list)
    for u in usuarios:
        if u.puesto:
            puesto_a_usuarios[u.puesto].append(u)

    resultado = []
    observaciones = []

    for p_id in puestos_ids:
        eqs_en_puesto = puesto_a_equipos.get(p_id, [])
        usrs_en_puesto = puesto_a_usuarios.get(p_id, [])
        
        nombres_equipos, inventarios, usuarios_asignados, colores_sectores = [], [], [], []
        equipos_detalle = [] # ✨ NUEVO: Guardará los specs técnicos

        for eq in eqs_en_puesto:
            if eq.nombre_de_equipo: nombres_equipos.append(eq.nombre_de_equipo)
            if eq.numero_inventario: inventarios.append(eq.numero_inventario)
            
            # ✨ NUEVO: Añadimos detalles para la tarjeta de información
            equipos_detalle.append({
                "nombre": eq.nombre_de_equipo or "Sin nombre",
                "marca": eq.marca or "",
                "procesador": eq.procesador or "",
                "memoria": eq.memoria or "",
                "disco": eq.disco or ""
            })

        for u in usrs_en_puesto:
            nombre_completo = f"{u.nombre} {u.apellido}".strip()
            if nombre_completo not in usuarios_asignados:
                usuarios_asignados.append(nombre_completo)
            
            if u.sector and u.sector.color:
                if u.sector.color not in colores_sectores: colores_sectores.append(u.sector.color)

        if len(eqs_en_puesto) > 1:
            observaciones.append(f"⚠️ Conflicto en {p_id}: {len(eqs_en_puesto)} equipos asignados.")
        if len(usrs_en_puesto) > 1:
            observaciones.append(f"⚠️ Conflicto en {p_id}: Múltiples usuarios asignados.")

        resultado.append({
            "numero_puesto": p_id,
            "nombres_equipos": nombres_equipos,
            "nro_inventarios": inventarios,
            "usuarios_asignados": usuarios_asignados,
            "colores": colores_sectores,
            "equipos_detalle": equipos_detalle # ✨ NUEVO
        })

    estructura_mapa = {
        "titulo": mapa_db.titulo,
        "filas": mapa_db.filas,
        "columnas": mapa_db.columnas,
        "celdas": [{"fila": c.fila, "columna": c.columna, "habilitado": c.habilitado, "numero_puesto": c.numero_puesto, "rotacion": c.rotacion} for c in mapa_db.celdas]
    }

    return {
        "estructura": estructura_mapa,
        "puestos_data": resultado,
        "observaciones": observaciones
    }


@router.put("/mapa-puestos/{piso}/{numero_puesto}")
def actualizar_puesto(piso: str, numero_puesto: str, datos: schemas.PuestoEdit, db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    if datos.nro_inventario:
        equipo = db.query(Patrimonio).filter(Patrimonio.numero_inventario == datos.nro_inventario).first()
        if equipo:
            equipo.puesto = numero_puesto
            equipo.nombre_de_equipo = datos.nombre_equipo
    
    if datos.usuario_id:
        usuario_db = db.query(models.User).filter(models.User.id == datos.usuario_id).first()
        if usuario_db:
            usuario_db.puesto = numero_puesto
            if 'equipo' in locals() and equipo:
                equipo.usuario_destino = f"{usuario_db.nombre} {usuario_db.apellido}"

    db.commit()
    return {"mensaje": "Puesto actualizado correctamente"}

# ✨ ENDPOINTS PARA EL EDITOR DE MATRIZ ✨

@router.get("/editor-matriz/{titulo}")
def obtener_matriz(titulo: str, db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    mapa = db.query(models.MapaGrid).filter(models.MapaGrid.titulo == titulo).first()
    if not mapa:
        return {"existe": False}
    
    return {
        "existe": True,
        "titulo": mapa.titulo,
        "filas": mapa.filas,
        "columnas": mapa.columnas,
        "celdas": [
            {
                "fila": c.fila,
                "columna": c.columna,
                "habilitado": c.habilitado,
                "numero_puesto": c.numero_puesto,
                "rotacion": c.rotacion
            } for c in mapa.celdas
        ]
    }

@router.post("/editor-matriz/guardar")
def guardar_matriz(datos: schemas.MapaGridGuardar, request: Request, db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    mapa = db.query(models.MapaGrid).filter(models.MapaGrid.titulo == datos.titulo).first()
    
    if not mapa:
        mapa = models.MapaGrid(titulo=datos.titulo, filas=datos.filas, columnas=datos.columnas)
        db.add(mapa)
        db.commit()
        db.refresh(mapa)
    else:
        mapa.filas = datos.filas
        mapa.columnas = datos.columnas
        db.query(models.MapaCelda).filter(models.MapaCelda.mapa_id == mapa.id).delete()
        db.commit()

    nuevas_celdas = []
    for c in datos.celdas:
        nueva = models.MapaCelda(
            mapa_id=mapa.id,
            fila=c.fila,
            columna=c.columna,
            habilitado=c.habilitado,
            numero_puesto=c.numero_puesto,
            rotacion=c.rotacion
        )
        nuevas_celdas.append(nueva)
    
    db.add_all(nuevas_celdas)
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="GUARDAR_MAPA",
        detalle=f"Mapa guardado: {datos.titulo} ({datos.filas}x{datos.columnas})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": "Matriz guardada con éxito"}

@router.delete("/editor-matriz/borrar/{titulo}")
def borrar_matriz(titulo: str, request: Request, db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    mapa = db.query(models.MapaGrid).filter(models.MapaGrid.titulo == titulo).first()
    if not mapa:
        raise HTTPException(status_code=404, detail="Mapa no encontrado")
    
    db.delete(mapa)
    db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="BORRAR_MAPA",
        detalle=f"Mapa eliminado: {titulo}",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": f"Mapa '{titulo}' eliminado con éxito"}

# ✨ ENDPOINTS PARA BACKUP DE MAPAS ✨

@router.get("/editor-matriz/backup/exportar")
def exportar_mapas(db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    mapas = db.query(models.MapaGrid).all()
    backup_data = []
    
    for mapa in mapas:
        backup_data.append({
            "titulo": mapa.titulo,
            "filas": mapa.filas,
            "columnas": mapa.columnas,
            "celdas": [
                {
                    "fila": c.fila,
                    "columna": c.columna,
                    "habilitado": c.habilitado,
                    "numero_puesto": c.numero_puesto,
                    "rotacion": c.rotacion
                } for c in mapa.celdas
            ]
        })
    return backup_data

@router.post("/editor-matriz/backup/importar")
def importar_mapas(backup_data: List[schemas.MapaGridGuardar], request: Request, db: Session = Depends(get_db), admin=Depends(verificar_admin_actual)):
    for datos_mapa in backup_data:
        mapa_existente = db.query(models.MapaGrid).filter(models.MapaGrid.titulo == datos_mapa.titulo).first()
        if mapa_existente:
            db.delete(mapa_existente)
            db.commit()

        nuevo_mapa = models.MapaGrid(titulo=datos_mapa.titulo, filas=datos_mapa.filas, columnas=datos_mapa.columnas)
        db.add(nuevo_mapa)
        db.commit()
        db.refresh(nuevo_mapa)

        nuevas_celdas = [
            models.MapaCelda(
                mapa_id=nuevo_mapa.id,
                fila=c.fila,
                columna=c.columna,
                habilitado=c.habilitado,
                numero_puesto=c.numero_puesto,
                rotacion=c.rotacion
            ) for c in datos_mapa.celdas
        ]
        db.add_all(nuevas_celdas)
        db.commit()

    registrar_evento(
        db, usuario_id=admin.get("id"), accion="IMPORTAR_MAPAS_MASIVO",
        detalle=f"Importación masiva de mapas: {len(backup_data)} mapas importados",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    return {"mensaje": f"Se importaron {len(backup_data)} mapas correctamente."}


# ✨ EXPORTAR UN SOLO MAPA ✨
@router.get("/editor-matriz/exportar/{titulo}")
def exportar_mapa_unico(titulo: str, db: Session = Depends(get_db), usuario=Depends(verificar_usuario_autenticado)):
    mapa = db.query(models.MapaGrid).filter(models.MapaGrid.titulo == titulo).first()
    if not mapa:
        raise HTTPException(status_code=404, detail="Mapa no encontrado")
    
    return {
        "titulo": mapa.titulo,
        "filas": mapa.filas,
        "columnas": mapa.columnas,
        "celdas": [
            {
                "fila": c.fila,
                "columna": c.columna,
                "habilitado": c.habilitado,
                "numero_puesto": c.numero_puesto,
                "rotacion": c.rotacion
            } for c in mapa.celdas
        ]
    }

# ✨ IMPORTAR UN SOLO MAPA (Con lógica de confirmación) ✨
@router.post("/editor-matriz/importar-unico")
async def importar_mapa_unico(
    file: UploadFile = File(...),
    reemplazar: bool = Form(False),
    request: Request = None,
    db: Session = Depends(get_db),
    admin=Depends(verificar_admin_actual)
):
    try:
        content = await file.read()
        datos_mapa = json.loads(content)
        titulo_mapa = datos_mapa.get("titulo")
        
        if not titulo_mapa:
            raise HTTPException(status_code=400, detail="El archivo no contiene un título válido.")

        mapa_existente = db.query(models.MapaGrid).filter(models.MapaGrid.titulo == titulo_mapa).first()
        
        if mapa_existente and not reemplazar:
            raise HTTPException(status_code=409, detail=f"El plano '{titulo_mapa}' ya existe.")
            
        if mapa_existente and reemplazar:
            db.delete(mapa_existente)
            db.commit()

        nuevo_mapa = models.MapaGrid(
            titulo=datos_mapa.get("titulo"), 
            filas=datos_mapa.get("filas"), 
            columnas=datos_mapa.get("columnas")
        )
        db.add(nuevo_mapa)
        db.commit()
        db.refresh(nuevo_mapa)

        nuevas_celdas = [
            models.MapaCelda(
                mapa_id=nuevo_mapa.id,
                fila=c.get("fila"),
                columna=c.get("columna"),
                habilitado=c.get("habilitado"),
                numero_puesto=c.get("numero_puesto"),
                rotacion=c.get("rotacion", 0)
            ) for c in datos_mapa.get("celdas", [])
        ]
        db.add_all(nuevas_celdas)
        db.commit()

        accion = "reemplazado" if mapa_existente else "importado"
        accion_aud = "REEMPLAZAR_MAPA" if mapa_existente else "IMPORTAR_MAPA"
        
        registrar_evento(
            db, usuario_id=admin.get("id"), accion=accion_aud,
            detalle=f"Mapa {accion}: {titulo_mapa}",
            ip_address=request.client.host if request else None
        )
        return {"mensaje": f"Plano '{titulo_mapa}' {accion} exitosamente."}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="El archivo no es un JSON válido.")