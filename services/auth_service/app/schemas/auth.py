from typing import Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """Schéma pour le token d'authentification"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    role: str
    matricule: str
    full_name: str


class TokenPayload(BaseModel):
    """Schéma pour le contenu d'un token JWT"""
    sub: Optional[str] = None  # matricule
    exp: Optional[int] = None  # timestamp d'expiration
    role: Optional[str] = None
    clearance_level: Optional[str] = None
    user_id: Optional[int] = None
    type: Optional[str] = None  # "access" ou "refresh"


class LoginRequest(BaseModel):
    """Schéma pour la requête d'authentification"""
    matricule: str = Field(..., description="Matricule de l'utilisateur")
    password: str = Field(..., description="Mot de passe de l'utilisateur")


class RefreshTokenRequest(BaseModel):
    """Schéma pour la requête de rafraîchissement de token"""
    refresh_token: str = Field(..., description="Token de rafraîchissement")


class VerifyTokenRequest(BaseModel):
    """Schéma pour la requête de vérification de token"""
    token: str = Field(..., description="Token à vérifier")


class VerifyTokenResponse(BaseModel):
    """Schéma pour la réponse de vérification de token"""
    valid: bool
    user_id: Optional[int] = None
    matricule: Optional[str] = None
    role: Optional[str] = None
    clearance_level: Optional[str] = None