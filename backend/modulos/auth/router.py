from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import string
import io
import pandas as pd
from jose import jwt, JWTError

# Importes relativos a tu nueva estructura
from backend import models, utils, database
from backend.config import SECRET_KEY, ALGORITHM
from backend.modulos.auth import schemas
from backend.modulos.auth.dependencies import (
    security,
    agregar_token_blacklist,
    verificar_usuario_autenticado,
    verificar_admin_actual,
)
from backend.modulos.auditoria.service import registrar_evento

router = APIRouter()

def generar_clave_aleatoria(longitud: int = 12) -> str:
    """Genera una contraseña aleatoria segura con mayúsculas, minúsculas, dígitos y símbolos."""
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        clave = ''.join(secrets.choice(chars) for _ in range(longitud))
        if (any(c.islower() for c in clave) and
            any(c.isupper() for c in clave) and
            any(c.isdigit() for c in clave) and
            any(c in "!@#$%&*" for c in clave)):
            return clave

# NOTA: verificar_usuario_autenticado y verificar_admin_actual ahora viven
# en backend/modulos/auth/dependencies.py

# --- ENDPOINTS DE AUTENTICACIÓN ---
@router.post("/register")
def register(user: schemas.UserCreate, request: Request, db: Session = Depends(database.get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    if db.query(models.User).filter(models.User.cuil == user.cuil).first():
        raise HTTPException(status_code=400, detail="El CUIL ya está registrado")
    
    nuevo_usuario = models.User(
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        cuil=user.cuil,
        reparticion=user.reparticion,
        password_hash=utils.get_password_hash(user.password)
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    registrar_evento(
        db, usuario_id=nuevo_usuario.id, accion="REGISTRO_USUARIO",
        detalle=f"Auto-registro: {user.nombre} {user.apellido} ({user.email})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )

    return {"mensaje": "Usuario registrado exitosamente"}

@router.post("/login")
def login(req: schemas.UserLogin, request: Request, db: Session = Depends(database.get_db)):
    # 1. Capturar la IP automáticamente desde FastAPI
    client_ip = request.client.host
    # Si estás detrás de un reverse proxy (como Nginx), usá esto:
    # client_ip = request.headers.get("x-forwarded-for", request.client.host)

    # 2. (Opcional) Si el frontend te envía el nombre de PC o usuario de red por headers o body:
    pc_nombre = request.headers.get("X-PC-Nombre", "Desconocido")
    pc_usuario = request.headers.get("X-PC-Usuario", "Desconocido")

    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not utils.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
    
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tu usuario está pendiente de aprobación por un administrador."
        )    
    
    # Guardar en auditoría con los nuevos datos
    nuevo_log = models.RegistroAuditoria(
        usuario_id=user.id, 
        accion="INICIO_SESION", 
        detalle="Acceso correcto",
        ip_address=client_ip,
        pc_nombre=pc_nombre,
        pc_usuario=pc_usuario
    )
    db.add(nuevo_log)
    db.commit()

    access_token = utils.create_access_token(data={
        "sub": user.email, 
        "id": user.id,
        "nombre": f"{user.nombre} {user.apellido}",
        "roles": user.roles.split(",") if user.roles else [],
        # ✨ EL FIX: Cambiamos 'usuario' por 'user'
        "sector": user.sector.nombre if user.sector else "Sin Sector"
    })  
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def registrar_logout(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(database.get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(models.User).filter(models.User.email == payload.get("sub")).first()
        if user:
            log = models.RegistroAuditoria(
                usuario_id=user.id, 
                accion="CIERRE_SESION", 
                detalle="Salida manual del sistema"
            )
            db.add(log)
            db.commit()
    except JWTError:
        pass
    # Agregar token a blacklist para invalidarlo
    agregar_token_blacklist(credentials.credentials)
    return {"mensaje": "Sesión cerrada"}

@router.post("/forgot-password")
def forgot_password(req: schemas.ForgotPasswordRequest, request: Request, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    mensaje_exito = {"mensaje": "Si el correo está registrado, recibirás un enlace para restablecer la contraseña."}
    
    if user:
        token = secrets.token_urlsafe(32)
        nuevo_token = models.PasswordResetToken(
            token=token,
            user_id=user.id,
            fecha_expiracion=datetime.utcnow() + timedelta(minutes=30)
        )
        db.add(nuevo_token)
        db.commit()
        print(f"ENLACE DE RECUPERACIÓN PARA {user.email}: http://localhost:8000/restablecer?token={token}")

        registrar_evento(
            db, usuario_id=user.id, accion="SOLICITUD_RECUPERACION",
            detalle=f"Usuario solicitó restablecimiento de contraseña",
            ip_address=request.client.host
        )
        
    return mensaje_exito

@router.post("/reset-password")
def reset_password(req: schemas.ResetPasswordRequest, request: Request, db: Session = Depends(database.get_db)):
    token_db = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == req.token,
        models.PasswordResetToken.usado == False
    ).first()
    
    if not token_db or token_db.fecha_expiracion < datetime.utcnow():
        raise HTTPException(status_code=400, detail="El token es inválido o ha expirado")
        
    user = db.query(models.User).filter(models.User.id == token_db.user_id).first()
    user.password_hash = utils.get_password_hash(req.nueva_password)
    token_db.usado = True
    db.commit()

    registrar_evento(
        db, usuario_id=user.id, accion="RESET_CONTRASENA",
        detalle=f"Contraseña restablecida vía token de recuperación",
        ip_address=request.client.host
    )

    return {"mensaje": "Contraseña actualizada correctamente"}

# --- ENDPOINT PARA ADMIN: RESETEAR CLAVE DE USUARIO ---
@router.put("/admin/usuarios/{usuario_id}/reset-password")
def resetear_clave_admin(
    usuario_id: int, 
    request: Request,
    db: Session = Depends(database.get_db),
    admin_auth: dict = Depends(verificar_admin_actual)
):
    # 1. Buscamos al usuario al que le queremos cambiar la clave
    usuario = db.query(models.User).filter(models.User.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # 2. Generamos una contraseña aleatoria segura
    nueva_clave = generar_clave_aleatoria()
    nueva_clave_hash = utils.get_password_hash(nueva_clave)
    
    # 3. Asignamos la nueva clave y guardamos
    usuario.password_hash = nueva_clave_hash
    db.commit()

    registrar_evento(
        db, usuario_id=admin_auth.get("id"), accion="ADMIN_RESET_CLAVE",
        detalle=f"Admin reseteó la contraseña de {usuario.nombre} {usuario.apellido} (ID: {usuario_id})",
        ip_address=request.client.host,
        pc_nombre=request.headers.get("X-PC-Nombre", "Desconocido"),
        pc_usuario=request.headers.get("X-PC-Usuario", "Desconocido")
    )
    
    return {"mensaje": f"Clave reseteada para {usuario.nombre} {usuario.apellido}", "nueva_clave": nueva_clave}


# --- ENDPOINT PARA IMPORTAR USUARIOS DESDE EXCEL ---
@router.post("/admin/usuarios/importar")
async def importar_usuarios_excel(
    file: UploadFile = File(...), 
    request: Request = None,
    db: Session = Depends(database.get_db),
    admin_auth: dict = Depends(verificar_admin_actual)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato inválido. Sube un archivo .xlsx o .xls")
    
    try:
        # 1. Leemos el archivo en memoria y limpiamos los datos vacíos (NaN)
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents)).fillna("")
        
        # Quitamos espacios en blanco accidentales de los nombres de las columnas
        df.columns = df.columns.str.strip()
        
        # 2. Verificamos que las columnas coincidan con la plantilla
        columnas_esperadas = ["Nombre", "Apellido", "CUIL", "Puesto", "Sector", "Correo Electrónico", "Repartición", "Rol"]
        for col in columnas_esperadas:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Falta la columna requerida en el Excel: {col}")

        usuarios_agregados = 0
        errores = []
        
        # Cacheamos los sectores existentes para no saturar la base de datos
        sectores_db = db.query(models.Sector).all()
        sector_map = {s.nombre.lower(): s.id for s in sectores_db}

        # 3. Recorremos fila por fila
        for index, row in df.iterrows():
            email = str(row["Correo Electrónico"]).strip()
            cuil = str(row["CUIL"]).strip()
            
            # Ignoramos filas totalmente en blanco
            if not email or not cuil:
                continue

            # Verificamos que el usuario no exista previamente
            if db.query(models.User).filter((models.User.email == email) | (models.User.cuil == cuil)).first():
                errores.append(f"Fila {index + 2}: CUIL o Email ya registrado ({cuil})")
                continue
            
            # Procesamos el Sector
            sector_nombre = str(row["Sector"]).strip()
            sector_id = None
            if sector_nombre:
                if sector_nombre.lower() in sector_map:
                    sector_id = sector_map[sector_nombre.lower()]
                else:
                    # Si el sector es nuevo, lo creamos al instante
                    nuevo_sector = models.Sector(nombre=sector_nombre, color="#1a3644")
                    db.add(nuevo_sector)
                    db.commit()
                    db.refresh(nuevo_sector)
                    sector_map[sector_nombre.lower()] = nuevo_sector.id
                    sector_id = nuevo_sector.id

            # Procesamos el Rol (si viene vacío, asignamos Operador por precaución)
            roles = str(row["Rol"]).strip()
            if not roles:
                roles = "Operador"

            # 4. Insertamos el usuario con contraseña aleatoria
            clave_usuario = generar_clave_aleatoria()
            nuevo_usuario = models.User(
                nombre=str(row["Nombre"]).strip(),
                apellido=str(row["Apellido"]).strip(),
                cuil=cuil,
                email=email,
                reparticion=str(row["Repartición"]).strip(),
                puesto=str(row["Puesto"]).strip(),
                roles=roles,
                sector_id=sector_id,
                password_hash=utils.get_password_hash(clave_usuario),
                activo=True  # Quedan aprobados por defecto al ser importados por el Admin
            )
            db.add(nuevo_usuario)
            usuarios_agregados += 1
        
        db.commit()
        
        mensaje = f"Se importaron {usuarios_agregados} usuarios. Cada uno tiene una contraseña aleatoria única."
        if errores:
            mensaje += f" Se omitieron {len(errores)} por estar duplicados."

        registrar_evento(
            db, usuario_id=admin_auth.get("id"), accion="IMPORTAR_USUARIOS_EXCEL",
            detalle=f"Importación masiva: {usuarios_agregados} usuarios creados desde archivo {file.filename}",
            ip_address=request.client.host if request else None
        )
            
        return {"mensaje": mensaje, "errores": errores}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")