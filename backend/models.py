# Este archivo es solo un ÍNDICE de modelos.
# De esta forma los routers importan con "from backend import models"
# sin tener que cambiar "import models" en cada módulo.

from backend.modulos.usuarios.models import User, Sector, MapaGrid, MapaCelda, Equipo
from backend.modulos.auth.models import PasswordResetToken
from backend.modulos.auditoria.models import RegistroAuditoria
from backend.modulos.chat.models import MensajeChat, ContactoChat
from backend.modulos.notificaciones.models import NotificacionGlobal, LecturaNotificacion