from sqlalchemy import Boolean, Column, Integer, String, Date, DateTime, ForeignKey, Text, Time, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


class Marcacion(Base):
    """Fichada cruda tal como llega del origen (reloj, archivo exportado o carga manual).
    Es la base de todo el módulo: horas trabajadas, llegadas tarde y ausencias se calculan
    a partir de estas filas cruzadas con el horario de cada empleado."""
    __tablename__ = "rrhh_marcaciones"
    __table_args__ = (
        # Evita duplicar fichadas si se importa dos veces el mismo archivo / período
        UniqueConstraint("identificador", "fecha_hora", name="uq_rrhh_marcacion_ident_fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # Cómo identifica el origen a la persona (legajo, DNI o ID del reloj)
    identificador = Column(String(40), nullable=False, index=True)
    # Usuario del sistema al que corresponde, si se pudo vincular
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    fecha_hora = Column(DateTime, nullable=False, index=True)  # hora local del reloj
    tipo = Column(String(10), nullable=True)                    # ENTRADA | SALIDA | null si el origen no lo indica
    origen = Column(String(20), nullable=False, default="MANUAL")  # RELOJ | ARCHIVO | MANUAL
    dispositivo = Column(String(80), nullable=True)
    cargado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_carga = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("User", foreign_keys=[usuario_id])


# Días de la semana del tablero (0 = lunes ... 4 = viernes)
DIAS_SEMANA = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")
# Cómo se marca cada día en el tablero. Por defecto todos están convocados:
# un día sin fila cuenta como CONVOCADO y RRHH solo asigna los días de Home.
TIPOS_DIA = {"HOME": "Home", "CONVOCADO": "Convocado", "SIN_HORARIO": "Sin horario"}
TIPO_POR_DEFECTO = "CONVOCADO"


class HomeOfficeDia(Base):
    """Marca de un día de la semana para un usuario: HOME (trabaja desde su casa) o
    CONVOCADO (tiene que ir a la oficina). Una fila por usuario y día; sin fila = CONVOCADO."""
    __tablename__ = "rrhh_home_office"
    __table_args__ = (UniqueConstraint("usuario_id", "dia_semana", name="uq_rrhh_home_office_usuario_dia"),)

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    dia_semana = Column(Integer, nullable=False)  # 0 = lunes ... 4 = viernes
    tipo = Column(String(12), nullable=False, default="HOME")  # HOME | CONVOCADO | SIN_HORARIO
    # Franja horaria del día, tal como viene de la planilla de RRHH
    franja = Column(String(80), nullable=True)
    hora_desde = Column(Time, nullable=True)
    hora_hasta = Column(Time, nullable=True)
    lugar = Column(String(60), nullable=True)  # "DGAI", "ENTE HU", "Registro Civil"...
    modificado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_modificacion = Column(DateTime, default=datetime.utcnow)



class PeriodoSinControl(Base):
    """Período en que no se controla Home / Convocado (licencias, comisiones, receso, etc.).
    usuario_id null = aplica a todo el personal."""
    __tablename__ = "rrhh_periodos_sin_control"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=True, index=True)
    desde = Column(Date, nullable=False, index=True)
    hasta = Column(Date, nullable=False, index=True)
    motivo = Column(String(150), nullable=True)
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)



class PersonalHorario(Base):
    """Datos de la planilla de horarios por persona: hoja (área), subsector, observaciones y color."""
    __tablename__ = "rrhh_personal_horario"

    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    area = Column(String(80), nullable=True)
    subsector = Column(String(150), nullable=True)
    observacion = Column(Text, nullable=True)
    color = Column(String(6), nullable=True)          # color de la celda del nombre (para el Cód Reg)
    nombre_planilla = Column(String(150), nullable=True)
    orden = Column(Integer, nullable=True)            # orden en la planilla (hoja y fila)
    fecha_importacion = Column(DateTime, default=datetime.utcnow)



class HorarioHistorial(Base):
    """Historial por fechas del horario de cada persona y día de la semana.
    Cada cambio cierra la vigencia anterior (vigente_hasta) y abre una nueva desde ese día,
    así se puede saber qué horario tenía alguien en cualquier fecha (para compararlo con las fichadas)."""
    __tablename__ = "rrhh_horario_historial"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    dia_semana = Column(Integer, nullable=False)  # 0 = lunes ... 4 = viernes
    tipo = Column(String(12), nullable=False)      # HOME | CONVOCADO | SIN_HORARIO
    franja = Column(String(80), nullable=True)
    hora_desde = Column(Time, nullable=True)
    hora_hasta = Column(Time, nullable=True)
    lugar = Column(String(60), nullable=True)
    vigente_desde = Column(Date, nullable=False, index=True)
    vigente_hasta = Column(Date, nullable=True, index=True)  # null = vigente hoy
    modificado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)



class FichadaArchivo(Base):
    """Cada Excel de asistencia importado. El hash del contenido evita subir dos veces el mismo archivo."""
    __tablename__ = "rrhh_fichadas_archivos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    hash_sha256 = Column(String(64), nullable=False, unique=True, index=True)
    desde = Column(Date, nullable=True)
    hasta = Column(Date, nullable=True)
    filas = Column(Integer, nullable=False, default=0)
    subido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_subida = Column(DateTime, default=datetime.utcnow)


class FichadaDiaria(Base):
    """Asistencia de una persona en un día, tal como la informa el reporte biométrico, con sus alertas.
    Una sola fila por CUIL y fecha: si se importa otro archivo con el mismo día, se actualiza."""
    __tablename__ = "rrhh_fichadas_diarias"
    __table_args__ = (UniqueConstraint("cuil", "fecha", name="uq_rrhh_fichada_cuil_fecha"),)

    id = Column(Integer, primary_key=True)
    archivo_id = Column(Integer, ForeignKey("rrhh_fichadas_archivos.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    cuil = Column(String(20), nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    reparticion = Column(String(150), nullable=True)
    cod_reg = Column(String(100), nullable=True)
    fecha = Column(Date, nullable=False, index=True)
    feriado = Column(Boolean, default=False)
    tipo_horario = Column(String(80), nullable=True)
    convocado = Column(Boolean, nullable=False, default=False)
    teorico_ingreso = Column(Time, nullable=True)
    teorico_salida = Column(Time, nullable=True)
    real_ingreso = Column(Time, nullable=True)
    real_salida = Column(Time, nullable=True)
    horas_min = Column(Integer, nullable=True)      # Cant Horas (R) en minutos
    eximido = Column(Boolean, default=False)
    incidencia = Column(String(40), nullable=True)
    estado_incidencia = Column(String(150), nullable=True)
    estado = Column(String(120), nullable=True)
    alertas = Column(Text, nullable=True)           # JSON: [{codigo, texto}]
    fecha_carga = Column(DateTime, default=datetime.utcnow)



class BancoHorasMovimiento(Base):
    """Banco de horas: cada movimiento suma o resta minutos al saldo de una persona (por CUIL).
    minutos < 0 = horas que debe. Tipos:
      SALDO_INICIAL  → lo que traía (Excel de saldo inicial; uno por persona, se reemplaza al reimportar)
      FICHADA        → lo que debe de un día según el Excel de asistencia (uno por persona y fecha)
      AJUSTE         → corrección o compensación cargada a mano"""
    __tablename__ = "rrhh_banco_horas"

    id = Column(Integer, primary_key=True)
    cuil = Column(String(20), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    nombre = Column(String(150), nullable=True)
    tipo = Column(String(20), nullable=False, index=True)
    fecha = Column(Date, nullable=True, index=True)       # día de la fichada (FICHADA) o de la carga
    minutos = Column(Integer, nullable=False)
    detalle = Column(String(255), nullable=True)
    archivo = Column(String(200), nullable=True)
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
