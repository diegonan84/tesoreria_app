# backend/modulos/recursos_humanos/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend import database
from backend.modulos.auth.dependencies import verificar_usuario_autenticado

router = APIRouter()

@router.get("/api/fichadas")
def listar_fichadas(db: Session = Depends(database.get_db), usuario = Depends(verificar_usuario_autenticado)):
    # Acá después podés conectar la lógica para traer las fichadas de la base de datos
    return [{"id": 1, "empleado": usuario.get("nombre"), "estado": "Presente", "hora": "08:00"}]