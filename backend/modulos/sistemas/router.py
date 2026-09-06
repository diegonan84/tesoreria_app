from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

# Importamos las dependencias desde tu módulo patrimonio (o global) que ya funciona
from backend.modulos.patrimonio.dependencies import get_db, get_current_user
JWT_DEPENDENCY = get_current_user

from . import schemas
from .service import SistemasService
from backend.modulos.auditoria.service import registrar_evento

router = APIRouter(
    prefix="/sistemas",
    tags=["Sistemas"]
)

# 2. El endpoint debe usar @router.post, NO @app.post
@router.post("/nota-salida/generar")
def generar_nota_salida_pdf(
    req: schemas.NotaSalidaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario_actual: str = Depends(JWT_DEPENDENCY)
):
    service = SistemasService(db)
    pdf_buffer = service.generar_pdf_salida(req)

    nombre_limpio = req.nombre_apellido.replace(' ', '_')

    from backend.modulos.usuarios.models import User
    user = db.query(User).filter(User.email == usuario_actual).first()
    if user:
        registrar_evento(
            db, usuario_id=user.id, accion="GENERAR_NOTA_SALIDA",
            detalle=f"PDF nota de salida generado para: {req.nombre_apellido} ({req.cuil_cuit})",
            ip_address=request.client.host
        )

    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=Nota_Salida_{nombre_limpio}.pdf"}
    )