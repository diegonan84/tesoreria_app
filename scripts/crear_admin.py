"""Crea el primer usuario Administrador (para una instalación con base vacía).

Pide los datos por consola; la contraseña no queda en ningún archivo.

Uso (en el servidor):
    docker compose exec app python -m scripts.crear_admin
"""
from getpass import getpass

from backend import models, utils
from backend.database import SessionLocal

db = SessionLocal()
try:
    nombre = input("Nombre: ").strip()
    apellido = input("Apellido: ").strip()
    email = input("Email: ").strip()
    cuil = input("CUIL: ").strip()
    reparticion = input("Repartición: ").strip()
    clave = getpass("Contraseña: ")
    if clave != getpass("Repetir contraseña: "):
        raise SystemExit("Las contraseñas no coinciden.")
    if not all([nombre, apellido, email, cuil, reparticion, clave]):
        raise SystemExit("Todos los datos son obligatorios.")
    if db.query(models.User).filter((models.User.email == email) | (models.User.cuil == cuil)).first():
        raise SystemExit("Ya existe un usuario con ese email o CUIL.")

    admin = models.User(
        nombre=nombre, apellido=apellido, email=email, cuil=cuil, reparticion=reparticion,
        password_hash=utils.get_password_hash(clave),
        roles=models.roles_con_defecto("Administrador"),
    )
    models.aplicar_estado(admin, "ACTIVO")
    db.add(admin)
    db.commit()
    print(f"Administrador creado: {email}")
finally:
    db.close()
