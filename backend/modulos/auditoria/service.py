from sqlalchemy.orm import Session
from backend.modulos.auditoria.models import RegistroAuditoria


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
