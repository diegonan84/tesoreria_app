"""
Limpia los datos de prueba del control de fichadas en la base LOCAL, para volver a probar el banco de horas.

Sin opciones borra:
  - las fichadas guardadas con el sistema anterior (rrhh_fichadas_diarias y rrhh_fichadas_archivos)
  - lo que se sumó o compensó al banco de horas desde los Excel de fichadas (movimientos tipo FICHADA)
  y deja el saldo inicial y los ajustes manuales.
Con --todo borra además TODO el banco de horas (saldos iniciales y ajustes manuales incluidos).

Uso (desde C:/Proyectos/tesoreria_app):
    venv/Scripts/python.exe scripts/limpiar_fichadas_local.py           (deja saldos iniciales y ajustes)
    venv/Scripts/python.exe scripts/limpiar_fichadas_local.py --todo    (deja el banco vacío)
Pide confirmación antes de borrar. Hacé un backup antes si querés poder volver atrás.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func  # noqa: E402

from backend.database import SessionLocal  # noqa: E402
import backend.main  # noqa: E402,F401  (registra todos los modelos)
from backend.modulos.recursos_humanos.models import BancoHorasMovimiento, FichadaArchivo, FichadaDiaria  # noqa: E402


def main():
    todo = "--todo" in sys.argv
    db = SessionLocal()
    banco = db.query(BancoHorasMovimiento)
    if not todo:
        banco = banco.filter(BancoHorasMovimiento.tipo == "FICHADA")
    print(f"Base: {db.bind.url.host}/{db.bind.url.database}")
    print(f"  Fichadas guardadas: {db.query(FichadaDiaria).count()} (de {db.query(FichadaArchivo).count()} archivo/s)")
    if todo:
        print(f"  TODO el banco de horas: {banco.count()} movimientos (saldos iniciales, fichadas y ajustes)")
    else:
        print(f"  Movimientos del banco sumados desde fichadas: {banco.count()}")
        print("  (El saldo inicial y los ajustes manuales NO se tocan. Usá --todo para borrarlos también.)")
    if db.bind.url.host not in ("localhost", "127.0.0.1"):
        print("La base no es local: no se borra nada.")
        return
    if input("¿Borrar? Escribí SI para confirmar: ").strip().upper() != "SI":
        print("No se borró nada.")
        return
    a = banco.delete()
    b = db.query(FichadaDiaria).delete()
    c = db.query(FichadaArchivo).delete()
    db.commit()
    print(f"Listo: {a} movimientos del banco, {b} fichadas y {c} archivo/s borrados.")
    print("Queda en el banco:", db.query(BancoHorasMovimiento.tipo, func.count()).group_by(BancoHorasMovimiento.tipo).all())


if __name__ == "__main__":
    main()
