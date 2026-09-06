from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha_expiracion = Column(DateTime, nullable=False)
    usado = Column(Boolean, default=False)
    user = relationship("User", back_populates="tokens")