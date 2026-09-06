from pydantic import BaseModel

class NotificacionCreate(BaseModel):
    titulo: str
    mensaje: str