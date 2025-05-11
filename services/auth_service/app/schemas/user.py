import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Schéma de base pour les utilisateurs"""
    matricule: str = Field(..., description="Matricule de l'utilisateur (format: XX-9999X)")
    full_name: str = Field(..., description="Nom complet de l'utilisateur")
    email: EmailStr = Field(..., description="Adresse email de l'utilisateur")
    role: str = Field(..., description="Rôle de l'utilisateur (admin, commander, field)")
    clearance_level: str = Field(..., description="Niveau d'habilitation (top_secret, secret, confidential)")
    is_active: bool = Field(True, description="Indique si l'utilisateur est actif")
    
    @field_validator("matricule")
    def validate_matricule(cls, v):
        """Valide le format du matricule (format: XX-9999X)"""
        pattern = r'^[A-Z]{2}-\d{4}[A-Z]$'
        if not re.match(pattern, v):
            raise ValueError("Le matricule doit avoir le format XX-9999X (ex: AF-1234P)")
        return v
    
    @field_validator("role")
    def validate_role(cls, v):
        """Valide le rôle de l'utilisateur"""
        valid_roles = ["admin", "commander", "field"]
        if v not in valid_roles:
            raise ValueError(f"Le rôle doit être l'un des suivants: {', '.join(valid_roles)}")
        return v
    
    @field_validator("clearance_level")
    def validate_clearance_level(cls, v):
        """Valide le niveau d'habilitation de l'utilisateur"""
        valid_levels = ["top_secret", "secret", "confidential"]
        if v not in valid_levels:
            raise ValueError(f"Le niveau d'habilitation doit être l'un des suivants: {', '.join(valid_levels)}")
        return v


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur"""
    password: str = Field(..., min_length=8, description="Mot de passe de l'utilisateur")


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[str] = None
    clearance_level: Optional[str] = None
    is_active: Optional[bool] = None
    
    @field_validator("role")
    def validate_role(cls, v):
        if v is not None:
            valid_roles = ["admin", "commander", "field"]
            if v not in valid_roles:
                raise ValueError(f"Le rôle doit être l'un des suivants: {', '.join(valid_roles)}")
        return v
    
    @field_validator("clearance_level")
    def validate_clearance_level(cls, v):
        if v is not None:
            valid_levels = ["top_secret", "secret", "confidential"]
            if v not in valid_levels:
                raise ValueError(f"Le niveau d'habilitation doit être l'un des suivants: {', '.join(valid_levels)}")
        return v


class UserInDB(UserBase):
    """Schéma pour un utilisateur en base de données"""
    id: int
    hashed_password: str
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(UserBase):
    """Schéma pour la réponse d'un utilisateur"""
    id: int
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserList(BaseModel):
    """Schéma pour la réponse d'une liste d'utilisateurs"""
    items: List[User]
    total: int
    page: int
    page_size: int
    pages: int


class ChangePassword(BaseModel):
    """Schéma pour le changement de mot de passe"""
    current_password: str = Field(..., description="Mot de passe actuel")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe")
    
    @field_validator("new_password")
    def validate_new_password(cls, v, values):
        if "current_password" in values and v == values["current_password"]:
            raise ValueError("Le nouveau mot de passe doit être différent de l'ancien")
        return v