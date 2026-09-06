from fastapi import WebSocket
from typing import Dict, Set

class ChatManager:
    def __init__(self):
        # Guarda las conexiones activas: {usuario_id: websocket}
        self.conexiones_activas: Dict[int, WebSocket] = {}
        # Guarda los usuarios que decidieron ponerse en modo "Invisible"
        self.usuarios_invisibles: Set[int] = set()

    async def conectar(self, usuario_id: int, websocket: WebSocket):
        await websocket.accept()
        self.conexiones_activas[usuario_id] = websocket

    def desconectar(self, usuario_id: int):
        if usuario_id in self.conexiones_activas:
            del self.conexiones_activas[usuario_id]
        if usuario_id in self.usuarios_invisibles:
            self.usuarios_invisibles.remove(usuario_id)

    def cambiar_visibilidad(self, usuario_id: int, invisible: bool):
        if invisible:
            self.usuarios_invisibles.add(usuario_id)
        elif usuario_id in self.usuarios_invisibles:
            self.usuarios_invisibles.remove(usuario_id)

    def obtener_usuarios_en_linea(self) -> Set[int]:
        # Retorna solo los usuarios conectados que NO están invisibles
        return {uid for uid in self.conexiones_activas.keys() if uid not in self.usuarios_invisibles}

manager_chat = ChatManager()