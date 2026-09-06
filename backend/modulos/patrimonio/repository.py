from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from .models import Patrimonio, PatrimonioHistorial, PatrimonioConcepto

class PatrimonioRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Patrimonio]:
        stmt = select(Patrimonio).where(Patrimonio.activo == True).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def get_by_numero_inventario(self, numero_inventario: str) -> Optional[Patrimonio]:
        stmt = select(Patrimonio).where(Patrimonio.numero_inventario == numero_inventario)
        return self.db.execute(stmt).scalars().first()

    def create(self, patrimonio: Patrimonio) -> Patrimonio:
        self.db.add(patrimonio)
        self.db.commit()
        self.db.refresh(patrimonio)
        return patrimonio

    def update(self, patrimonio: Patrimonio) -> Patrimonio:
        self.db.commit()
        self.db.refresh(patrimonio)
        return patrimonio

    def delete_logico(self, patrimonio: Patrimonio) -> Patrimonio:
        patrimonio.activo = False
        self.db.commit()
        self.db.refresh(patrimonio)
        return patrimonio


class PatrimonioHistorialRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, historial: PatrimonioHistorial) -> PatrimonioHistorial:
        self.db.add(historial)
        self.db.commit()
        self.db.refresh(historial)
        return historial

    def get_by_inventario(self, numero_inventario: str) -> List[PatrimonioHistorial]:
        stmt = select(PatrimonioHistorial).where(
            PatrimonioHistorial.numero_inventario == numero_inventario
        ).order_by(PatrimonioHistorial.fecha.desc())
        return self.db.execute(stmt).scalars().all()


class PatrimonioConceptoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_activos(self) -> List[PatrimonioConcepto]:
        stmt = select(PatrimonioConcepto).where(PatrimonioConcepto.activo == True)
        return self.db.execute(stmt).scalars().all()