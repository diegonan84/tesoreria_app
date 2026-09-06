from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from backend.config import SECRET_KEY, ALGORITHM

security = HTTPBearer()

# --- BLACKLIST DE TOKENS EN MEMORIA ---
# En producción usar Redis. En memoria para desarrollo.
_token_blacklist: set = set()


def agregar_token_blacklist(token: str):
    _token_blacklist.add(token)


def _token_en_blacklist(token: str) -> bool:
    return token in _token_blacklist


def verificar_usuario_autenticado(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if _token_en_blacklist(token):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")


def verificar_admin_actual(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if _token_en_blacklist(token):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        roles = payload.get("roles", [])
        if "Administrador" not in roles:
            raise HTTPException(status_code=403, detail="Operación no permitida.")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")