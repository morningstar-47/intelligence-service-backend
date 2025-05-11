from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import jwt  # PyJWT
from jwt.exceptions import PyJWTError  # Utiliser PyJWTError au lieu de InvalidTokenError
from passlib.context import CryptContext
import logging

from app.core.config import settings

# Configurer le logger
logger = logging.getLogger("auth_service.security")

# Contexte de hashage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si le mot de passe en clair correspond au hash stocké
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Génère le hash d'un mot de passe
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Génère un token JWT avec les informations d'authentification
    
    Args:
        subject: Sujet du token (matricule de l'utilisateur)
        expires_delta: Durée de validité du token
        additional_data: Données supplémentaires à inclure dans le token
    
    Returns:
        Token JWT encodé
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Données à encoder dans le token
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Ajouter des données supplémentaires
    if additional_data:
        to_encode.update(additional_data)
    
    # Encoder le token
    if settings.USE_RSA_KEYS and settings.PRIVATE_KEY:
        # Utiliser la clé privée RSA pour signer le token
        return jwt.encode(
            to_encode,
            settings.PRIVATE_KEY,
            algorithm="RS256"
        )
    else:
        # Utiliser la clé secrète pour signer le token
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Génère un token de rafraîchissement
    
    Args:
        subject: Sujet du token (matricule de l'utilisateur)
        expires_delta: Durée de validité du token
    
    Returns:
        Token JWT encodé
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Données à encoder dans le token
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh"
    }
    
    # Encoder le token
    if settings.USE_RSA_KEYS and settings.PRIVATE_KEY:
        # Utiliser la clé privée RSA pour signer le token
        return jwt.encode(
            to_encode,
            settings.PRIVATE_KEY,
            algorithm="RS256"
        )
    else:
        # Utiliser la clé secrète pour signer le token
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Décode un token JWT
    
    Args:
        token: Token JWT à décoder
    
    Returns:
        Dictionnaire des claims du token
    
    Raises:
        jwt.PyJWTError: Si le token est invalide
    """
    try:
        if settings.USE_RSA_KEYS and settings.PUBLIC_KEY:
            # Utiliser la clé publique RSA pour vérifier le token
            return jwt.decode(
                token,
                settings.PUBLIC_KEY,
                algorithms=["RS256"]
            )
        else:
            # Utiliser la clé secrète pour vérifier le token
            return jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
    except PyJWTError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise