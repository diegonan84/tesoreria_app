from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import json

from backend import models, database
from backend.modulos.auth.dependencies import verificar_usuario_autenticado
from backend.modulos.chat.manager import manager_chat
from backend.modulos.auditoria.service import registrar_evento
from backend.utils import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

router = APIRouter()

# --- FUNCION AUXILIAR PARA EL EFECTO MSN ---
async def notificar_estado_todos(usuario_id: int, online: bool):
    """Avisa a todos los usuarios conectados que alguien cambió de estado"""
    mensaje_estado = json.dumps({
        "tipo": "estado",
        "usuario_id": usuario_id,
        "online": online
    })
    
    # Iteramos sobre una copia de las claves para evitar errores si alguien se desconecta en el proceso
    for uid, conexion in list(manager_chat.conexiones_activas.items()):
        if uid != usuario_id:  # No nos enviamos el aviso a nosotros mismos
            try:
                await conexion.send_text(mensaje_estado)
            except:
                pass


# --- 1. OBTENER MIS CONTACTOS Y SOLICITUDES PENDIENTES ---
@router.get("/directorio-chat")
def obtener_directorio(db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    mi_id = usuario.get("id")

    # A) Buscar relaciones ACEPTADAS
    relaciones = db.query(models.ContactoChat).filter(
        or_(models.ContactoChat.solicitante_id == mi_id, models.ContactoChat.receptor_id == mi_id),
        models.ContactoChat.estado == "ACEPTADO"
    ).all()

    contactos_ids = set()
    for r in relaciones:
        contactos_ids.add(r.solicitante_id if r.receptor_id == mi_id else r.receptor_id)

    # B) Construir lista de amigos con su estado online
    lista_amigos = []
    if contactos_ids:
        amigos_db = db.query(models.User).filter(models.User.id.in_(contactos_ids), models.User.activo == True).all()
        for u in amigos_db:
            esta_online = u.id in manager_chat.conexiones_activas
            if hasattr(manager_chat, 'usuarios_invisibles') and u.id in manager_chat.usuarios_invisibles:
                esta_online = False
                
            lista_amigos.append({
                "id": u.id, 
                "nombre": f"{u.nombre} {u.apellido}", 
                "reparticion": u.reparticion,
                "online": esta_online 
            })

    # C) Buscar solicitudes PENDIENTES (que YO recibí)
    solicitudes = db.query(models.ContactoChat).filter(
        models.ContactoChat.receptor_id == mi_id,
        models.ContactoChat.estado == "PENDIENTE"
    ).all()

    lista_pendientes = []
    for s in solicitudes:
        solicitante = db.query(models.User).filter(models.User.id == s.solicitante_id).first()
        if solicitante:
            lista_pendientes.append({
                "id_solicitud": s.id, 
                "nombre": f"{solicitante.nombre} {solicitante.apellido}"
            })

    return {"amigos": lista_amigos, "pendientes": lista_pendientes}


# --- 2. BUSCADOR GLOBAL DE USUARIOS ---
@router.get("/chat/buscar")
def buscar_usuarios_global(q: str, db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    mi_id = usuario.get("id")
    resultados = db.query(models.User).filter(
        models.User.activo == True,
        models.User.id != mi_id,
        or_(models.User.nombre.ilike(f"%{q}%"), models.User.apellido.ilike(f"%{q}%"))
    ).limit(15).all()
    
    return [{"id": u.id, "nombre": f"{u.nombre} {u.apellido}"} for u in resultados]


# --- 3. ENVIAR SOLICITUD DE CONTACTO ---
@router.post("/chat/solicitud/{receptor_id}")
def enviar_solicitud(receptor_id: int, request: Request, db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    mi_id = usuario.get("id")
    
    existe = db.query(models.ContactoChat).filter(
        or_(
            and_(models.ContactoChat.solicitante_id == mi_id, models.ContactoChat.receptor_id == receptor_id),
            and_(models.ContactoChat.solicitante_id == receptor_id, models.ContactoChat.receptor_id == mi_id)
        )
    ).first()
    
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe una solicitud o relación.")
        
    nueva = models.ContactoChat(solicitante_id=mi_id, receptor_id=receptor_id, estado="PENDIENTE")
    db.add(nueva)
    db.commit()

    registrar_evento(
        db, usuario_id=mi_id, accion="CHAT_SOLICITUD_ENVIADA",
        detalle=f"Solicitud de contacto enviada al usuario ID {receptor_id}",
        ip_address=request.client.host
    )
    return {"mensaje": "Solicitud enviada"}


# --- 4. ACEPTAR SOLICITUD ---
@router.put("/chat/solicitud/{solicitud_id}/aceptar")
def aceptar_solicitud(solicitud_id: int, request: Request, db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    solicitud = db.query(models.ContactoChat).filter(models.ContactoChat.id == solicitud_id).first()
    if not solicitud or solicitud.receptor_id != usuario.get("id"):
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        
    solicitud.estado = "ACEPTADO"
    db.commit()

    registrar_evento(
        db, usuario_id=usuario.get("id"), accion="CHAT_SOLICITUD_ACEPTADA",
        detalle=f"Solicitud de contacto aceptada: ID {solicitud_id}",
        ip_address=request.client.host
    )
    return {"mensaje": "Contacto agregado"}


# --- 5. ELIMINAR CONTACTO ---
@router.delete("/chat/contacto/{contacto_id}")
def eliminar_contacto(contacto_id: int, request: Request, db: Session = Depends(database.get_db), usuario=Depends(verificar_usuario_autenticado)):
    mi_id = usuario.get("id")
    relacion = db.query(models.ContactoChat).filter(
        or_(
            and_(models.ContactoChat.solicitante_id == mi_id, models.ContactoChat.receptor_id == contacto_id),
            and_(models.ContactoChat.solicitante_id == contacto_id, models.ContactoChat.receptor_id == mi_id)
        )
    ).first()
    
    if relacion:
        db.delete(relacion)
        db.commit()

        registrar_evento(
            db, usuario_id=mi_id, accion="CHAT_CONTACTO_ELIMINADO",
            detalle=f"Contacto eliminado: usuario ID {contacto_id}",
            ip_address=request.client.host
        )
    return {"mensaje": "Contacto eliminado"}


# --- 6. WEBSOCKET (Chat en tiempo real) ---
@router.websocket("/ws/chat/{usuario_id}")
async def websocket_chat_endpoint(websocket: WebSocket, usuario_id: int, db: Session = Depends(database.get_db)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Token de autenticación requerido")
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        await websocket.close(code=4001, reason="Sesión inválida o expirada")
        return

    # Verificar que el usuario_id del token coincide con el de la URL
    if payload.get("id") != usuario_id:
        await websocket.close(code=4003, reason="No autorizado para conectarse como este usuario")
        return

    await manager_chat.conectar(usuario_id, websocket)
    await notificar_estado_todos(usuario_id, True)
    
    try:
        mensajes_pendientes = db.query(models.MensajeChat).filter(
            models.MensajeChat.destinatario_id == usuario_id,
            models.MensajeChat.leido == False
        ).order_by(models.MensajeChat.fecha_envio.asc()).all()

        for msg in mensajes_pendientes:
            await websocket.send_text(json.dumps({
                "remitente_id": msg.remitente_id,
                "contenido": msg.contenido,
                "fecha": msg.fecha_envio.isoformat(),
                "historico": True 
            }))
            msg.leido = True 
        db.commit()

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("accion") == "ESTADO":
                invisible = payload.get("estado") == "offline"
                manager_chat.cambiar_visibilidad(usuario_id, invisible)
                await notificar_estado_todos(usuario_id, not invisible)
                continue

            destinatario_id = int(payload["destinatario_id"])
            contenido_msg = payload["contenido"]

            nuevo_mensaje = models.MensajeChat(
                remitente_id=usuario_id,
                destinatario_id=destinatario_id,
                contenido=contenido_msg,
                leido=False
            )
            db.add(nuevo_mensaje)
            db.commit()
            db.refresh(nuevo_mensaje)

            if destinatario_id in manager_chat.conexiones_activas:
                await manager_chat.conexiones_activas[destinatario_id].send_text(json.dumps({
                    "remitente_id": usuario_id,
                    "contenido": contenido_msg,
                    "fecha": nuevo_mensaje.fecha_envio.isoformat(),
                    "historico": False
                }))

    except WebSocketDisconnect:
        manager_chat.desconectar(usuario_id)
        await notificar_estado_todos(usuario_id, False)