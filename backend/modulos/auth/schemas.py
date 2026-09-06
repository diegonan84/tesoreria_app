from pydantic import BaseModel, EmailStr, field_validator
import re

class UserCreate(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    cuil: str
    reparticion: str
    password: str
    confirm_password: str

    @field_validator('cuil')
    def validar_cuil(cls, v):
        if not re.match(r"^\d{2}-\d{8}-\d{1}$", v):
            raise ValueError('El CUIL debe tener el formato XX-XXXXXXXX-X')
        return v

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Las contraseñas no coinciden')
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    nueva_password: str
    confirmar_password: str

    @field_validator('confirmar_password')
    def passwords_match(cls, v, info):
        if 'nueva_password' in info.data and v != info.data['nueva_password']:
            raise ValueError('Las contraseñas no coinciden')
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v