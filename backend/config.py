"""
Configuración centralizada de la aplicación.
Todos los módulos leen sus valores desde acá para no repetir load_dotenv().
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Base de datos (el valor real se define en .env)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/tesoreria_db",
)

# JWT / Seguridad
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cambiar_esta_clave_secreta")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# CORS
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
    if origin.strip()
]