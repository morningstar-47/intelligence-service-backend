from typing import Generator, Dict, Any, Optional
import logging
import httpx
from fastapi import Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings

logger = logging.getLogger("reports_service.api.deps")


async def get_current_user_info(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Dépendance pour obtenir les informations de l'utilisateur actuel
    en validant le token JWT auprès du service d'authentification
    
    Args:
        authorization: En-tête d'autorisation (Bearer token)
        
    Returns:
        Informations sur l'utilisateur actuel
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Vérifier que c'est bien un token Bearer
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Vérifier le token auprès du service d'authentification
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AUTH_SERVICE_URL}{settings.AUTH_TOKEN_VALIDATE_PATH}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token or token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_info = response.json()
            
            if not user_info.get("valid", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user_info
            
    except httpx.RequestError as e:
        logger.error(f"Error connecting to auth service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot connect to authentication service",
        )


def check_clearance_level(required_level: str):
    """
    Crée une dépendance pour vérifier le niveau d'habilitation de l'utilisateur
    
    Args:
        required_level: Niveau d'habilitation minimum requis
        
    Returns:
        Fonction de dépendance
    """
    clearance_levels = {
        "confidential": 1,
        "secret": 2,
        "top_secret": 3
    }
    
    required_level_value = clearance_levels.get(required_level, 0)
    
    async def _check_clearance_level(user_info: Dict[str, Any] = Depends(get_current_user_info)):
        user_clearance = user_info.get("clearance_level", "")
        user_level_value = clearance_levels.get(user_clearance, 0)
        
        if user_level_value < required_level_value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Niveau d'habilitation insuffisant. Niveau requis: {required_level}",
            )
        
        return user_info
    
    return _check_clearance_level


def check_role(required_roles: list):
    """
    Crée une dépendance pour vérifier le rôle de l'utilisateur
    
    Args:
        required_roles: Liste des rôles autorisés
        
    Returns:
        Fonction de dépendance
    """
    async def _check_role(user_info: Dict[str, Any] = Depends(get_current_user_info)):
        user_role = user_info.get("role", "")
        
        if user_role not in required_roles and "admin" not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle insuffisant. Rôles requis: {', '.join(required_roles)}",
            )
        
        return user_info
    
    return _check_role


# Dépendances communes
get_current_user = get_current_user_info

# Dépendances spécifiques aux rôles
get_admin_user = check_role(["admin"])
get_commander_user = check_role(["admin", "commander"])
get_field_agent_user = check_role(["admin", "commander", "field"])

# Dépendances spécifiques aux niveaux d'habilitation
get_top_secret_user = check_clearance_level("top_secret")
get_secret_user = check_clearance_level("secret")
get_confidential_user = check_clearance_level("confidential")