from fastapi import Request, Depends
from backend.database import SessionLocal  

# Importamos tu función real
from backend.modulos.auth.dependencies import verificar_usuario_autenticado

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_client_ip(request: Request) -> str:
    """Captura la IP del cliente para el historial."""
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

# Extraemos el nombre directamente del payload de tu JWT
def get_current_user(payload: dict = Depends(verificar_usuario_autenticado)) -> str:
    # Como en tu login guardaste el nombre completo en "nombre", lo leemos de ahí
    return payload.get("nombre", "Usuario Desconocido")