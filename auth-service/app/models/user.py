import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, enum.Enum):
    """Rôles possibles pour un utilisateur"""
    ADMIN = "admin"
    COMMANDER = "commander"
    FIELD = "field"


class ClearanceLevel(str, enum.Enum):
    """Niveaux d'habilitation de sécurité"""
    TOP_SECRET = "top_secret"
    SECRET = "secret"
    CONFIDENTIAL = "confidential"


class User(Base):
    """
    Modèle pour les utilisateurs du système
    """
    id = Column(Integer, primary_key=True, index=True)
    matricule = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    clearance_level = Column(Enum(ClearanceLevel), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<User {self.id}: {self.matricule} ({self.role})>"