from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from backend.config import SECRET_KEY, ALGORITHM
from backend.database import get_db

security = HTTPBearer()

# --- BLACKLIST DE TOKENS EN MEMORIA ---
# En producción usar Redis. En memoria para desarrollo.
_token_blacklist: set = set()


def agregar_token_blacklist(token: str):
    _token_blacklist.add(token)


def _token_en_blacklist(token: str) -> bool:
    return token in _token_blacklist


def _decodificar_token(token: str) -> dict:
    if _token_en_blacklist(token):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")


def _validar_usuario_vigente(payload: dict, db: Session) -> dict:
    """El JWT vive hasta su expiración; consultamos la base para que una suspensión o baja
    corte la sesión al instante y para que los cambios de roles apliquen sin re-loguearse."""
    from backend.modulos.usuarios.models import User  # import diferido: evita ciclos entre módulos

    user = db.query(User.activo, User.roles).filter(User.id == payload.get("id")).first()
    if not user or not user.activo:
        raise HTTPException(status_code=401, detail="Tu usuario ya no está habilitado en el sistema.")
    payload["roles"] = [r.strip() for r in (user.roles or "").split(",") if r.strip()]
    return payload


def verificar_usuario_autenticado(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    return _validar_usuario_vigente(_decodificar_token(credentials.credentials), db)


def verificar_admin_actual(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    payload = verificar_usuario_autenticado(credentials, db)
    if "Administrador" not in payload["roles"]:
        raise HTTPException(status_code=403, detail="Operación no permitida.")
    return payload
