from sqlalchemy.orm import Session
from backend.modulos.auditoria.models import RegistroAuditoria
import socket
from sqlalchemy import func


def obtener_nombre_pc_cliente(client_ip: str):
    """Resuelve el nombre del equipo (hostname) desde la IP del cliente por
    reverse DNS. Devuelve solo el primer label (ej: 'PC-102').
    Retorna None si no se pudo resolver."""
    if not client_ip or client_ip in ("127.0.0.1", "::1"):
        return "LOCAL"
    try:
        nombre = socket.gethostbyaddr(client_ip)[0]
        return nombre.split(".")[0].upper()
    except Exception:
        return None


def vincular_equipo_patrimonio(db: Session, pc_nombre: str, usuario_id: int):
    """Cruza el hostname detectado con el registro de Informática
    (patrimonio.nombre_de_equipo). Devuelve (bien, es_suya).
      - bien: objeto Patrimonio que coincide o None
      - es_suya: True si el equipo está asignado a ese usuario_id"""
    if not pc_nombre:
        return None, False

    from backend.modulos.patrimonio.models import Patrimonio
    # Normalizamos: solo primer label (quita dominio) y sin diferenciar mayúsculas
    label = str(pc_nombre).split(".")[0].upper()
    if not label:
        return None, False
    bien = (
        db.query(Patrimonio)
        .filter(
            Patrimonio.activo == True,
            func.lower(Patrimonio.nombre_de_equipo) == label.lower(),
        )
        .first()
    )
    if not bien:
        return None, False
    return bien, (bien.usuario_id == usuario_id)


def registrar_evento(
    db: Session,
    usuario_id: int,
    accion: str,
    detalle: str = None,
    ip_address: str = None,
    pc_nombre: str = None,
    pc_usuario: str = None
):
    """
    Registra un evento en la tabla de auditoría centralizada.
    
    Ejemplo de uso:
        from backend.modulos.auditoria.service import registrar_evento
        registrar_evento(db, usuario_id=1, accion="CREAR_SECTOR", detalle="Sector: Administración")
    """
    log = RegistroAuditoria(
        usuario_id=usuario_id,
        accion=accion,
        detalle=detalle,
        ip_address=ip_address,
        pc_nombre=pc_nombre,
        pc_usuario=pc_usuario
    )
    db.add(log)
    db.commit()
