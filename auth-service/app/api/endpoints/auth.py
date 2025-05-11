from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.services.auth_service import AuthenticationService
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest, VerifyTokenRequest, VerifyTokenResponse
from app.models.user import User
from app.core.logging import log_auth_activity

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Authentifie un utilisateur avec son matricule et son mot de passe
    et retourne un token JWT
    """
    # Récupérer l'adresse IP
    client_ip = request.client.host if request.client else None
    
    # Authentifier l'utilisateur
    user, token_data = AuthenticationService.login(
        db,
        login_data.matricule,
        login_data.password,
        ip_address=client_ip
    )
    
    if not user or not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Matricule ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Construire la réponse
    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"],
        "role": user.role.value,
        "matricule": user.matricule,
        "full_name": user.full_name
    }


@router.post("/login/form", response_model=Token)
def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Point d'entrée de connexion compatible avec le schéma OAuth2
    Le matricule est attendu dans le champ username du formulaire
    """
    # Récupérer l'adresse IP
    client_ip = request.client.host if request.client else None
    
    # Authentifier l'utilisateur (le username contient le matricule)
    user, token_data = AuthenticationService.login(
        db,
        form_data.username,
        form_data.password,
        ip_address=client_ip
    )
    
    if not user or not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Matricule ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Construire la réponse
    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"],
        "role": user.role.value,
        "matricule": user.matricule,
        "full_name": user.full_name
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Rafraîchit un token JWT expiré en utilisant un token de rafraîchissement
    """
    # Récupérer l'adresse IP
    client_ip = request.client.host if request.client else None
    
    # Rafraîchir le token
    user, token_data = AuthenticationService.refresh_token(
        db,
        refresh_data.refresh_token,
        ip_address=client_ip
    )
    
    if not user or not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de rafraîchissement invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Construire la réponse
    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"],
        "role": user.role.value,
        "matricule": user.matricule,
        "full_name": user.full_name
    }


@router.post("/verify-token", response_model=VerifyTokenResponse)
def verify_token(
    request: Request,
    token_data: VerifyTokenRequest = None,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Vérifie la validité d'un token JWT et retourne les informations de l'utilisateur
    Cette route est utilisée par les autres services pour vérifier l'authentification
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "matricule": current_user.matricule,
        "role": current_user.role.value,
        "clearance_level": current_user.clearance_level.value
    }


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Déconnecte l'utilisateur
    
    Note: Avec JWT, la déconnexion est gérée côté client en supprimant le token.
    Cet endpoint est principalement utilisé pour la journalisation.
    Dans une implémentation plus complète, on pourrait ajouter le token à une liste noire.
    """
    # Récupérer l'adresse IP
    client_ip = request.client.host if request.client else None
    
    # Journaliser la déconnexion
    log_auth_activity(
        matricule=current_user.matricule,
        action="logout",
        details="Déconnexion utilisateur",
        ip_address=client_ip,
        metadata={"user_id": current_user.id}
    )
    
    return {"detail": "Déconnexion réussie"}