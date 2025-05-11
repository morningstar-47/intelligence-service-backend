from typing import Generator, Optional
import logging
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from jwt.exceptions import PyJWTError  # Remplacer InvalidTokenError par PyJWTError

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.models.user import User, UserRole, ClearanceLevel
from app.crud.user import get_user_by_matricule

logger = logging.getLogger("auth_service.api.deps")

# Schéma OAuth2 pour l'authentification
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_STR}/auth/login"
)


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    request: Request = None
) -> User:
    """
    Dépendance pour obtenir l'utilisateur actuellement authentifié
    
    Args:
        db: Session de base de données
        token: Token JWT
        request: Requête HTTP
        
    Returns:
        Utilisateur authentifié
    """
    try:
        # Décoder le token
        payload = decode_token(token)
        
        # Vérifier que c'est un token d'accès
        token_type = payload.get("type")
        if token_type is not None and token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide (type incorrect)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Récupérer le matricule
        matricule: Optional[str] = payload.get("sub")
        if matricule is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide (pas de matricule)",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    # except InvalidTokenError as e:
    #     logger.warning(f"Invalid token: {str(e)}")
    except PyJWTError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalide: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Récupérer l'utilisateur
    user = get_user_by_matricule(db, matricule=matricule)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dépendance pour obtenir l'utilisateur actif
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        Utilisateur actif
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte utilisateur inactif",
        )
    return current_user


def get_current_user_by_role(required_role: UserRole):
    """
    Crée une dépendance pour vérifier le rôle de l'utilisateur
    
    Args:
        required_role: Rôle requis
        
    Returns:
        Fonction de dépendance
    """
    def _get_user_by_role(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès réservé aux utilisateurs avec le rôle {required_role.value}"
            )
        return current_user
    
    return _get_user_by_role


def get_current_user_by_clearance(minimum_clearance: ClearanceLevel):
    """
    Crée une dépendance pour vérifier le niveau d'habilitation de l'utilisateur
    
    Args:
        minimum_clearance: Niveau d'habilitation minimum requis
        
    Returns:
        Fonction de dépendance
    """
    clearance_levels = {
        ClearanceLevel.CONFIDENTIAL: 1,
        ClearanceLevel.SECRET: 2,
        ClearanceLevel.TOP_SECRET: 3
    }
    
    def _get_user_by_clearance(current_user: User = Depends(get_current_active_user)) -> User:
        user_clearance = clearance_levels[current_user.clearance_level]
        required_clearance = clearance_levels[minimum_clearance]
        
        if user_clearance < required_clearance:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès réservé aux utilisateurs avec le niveau d'habilitation {minimum_clearance.value} ou supérieur"
            )
        return current_user
    
    return _get_user_by_clearance


# Dépendances spécifiques aux rôles
get_current_admin = get_current_user_by_role(UserRole.ADMIN)
get_current_commander = get_current_user_by_role(UserRole.COMMANDER)
get_current_field_agent = get_current_user_by_role(UserRole.FIELD)

# Dépendances spécifiques aux niveaux d'habilitation
get_current_top_secret_user = get_current_user_by_clearance(ClearanceLevel.TOP_SECRET)
get_current_secret_user = get_current_user_by_clearance(ClearanceLevel.SECRET)
get_current_confidential_user = get_current_user_by_clearance(ClearanceLevel.CONFIDENTIAL)