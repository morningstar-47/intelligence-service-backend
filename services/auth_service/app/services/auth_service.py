from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import logging
from sqlalchemy.orm import Session
# from jwt.exceptions import InvalidTokenError
from jwt.exceptions import PyJWTError  # Remplacer InvalidTokenError par PyJWTError


from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.crud.user import authenticate_user, get_user_by_matricule, update_user_last_login
from app.models.user import User
from app.core.logging import log_auth_activity

logger = logging.getLogger("auth_service.services")


class AuthenticationService:
    """
    Service pour gérer l'authentification et les tokens
    """
    @staticmethod
    def login(
        db: Session,
        matricule: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[Dict[str, Any]]]:
        """
        Authentifie un utilisateur et génère un token JWT
        
        Args:
            db: Session de base de données
            matricule: Matricule de l'utilisateur
            password: Mot de passe
            ip_address: Adresse IP du client
            
        Returns:
            Tuple contenant l'utilisateur authentifié et les informations du token
        """
        # Authentifier l'utilisateur
        user = authenticate_user(db, matricule, password)
        if not user:
            log_auth_activity(
                matricule=matricule,
                action="login_failed",
                details="Identifiants invalides",
                ip_address=ip_address
            )
            return None, None
        
        # Vérifier que l'utilisateur est actif
        if not user.is_active:
            log_auth_activity(
                matricule=user.matricule,
                action="login_failed",
                details="Compte inactif",
                ip_address=ip_address,
                metadata={"user_id": user.id}
            )
            return None, None
        
        # Mettre à jour la date de dernière connexion
        now = datetime.utcnow()
        update_user_last_login(db, user.id, now)
        
        # Créer les tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Données supplémentaires pour le token
        additional_data = {
            "role": user.role.value,
            "clearance_level": user.clearance_level.value,
            "user_id": user.id,
            "type": "access"
        }
        
        access_token = create_access_token(
            subject=user.matricule,
            expires_delta=access_token_expires,
            additional_data=additional_data
        )
        
        refresh_token = create_refresh_token(
            subject=user.matricule,
            expires_delta=refresh_token_expires
        )
        
        # Journaliser la connexion réussie
        log_auth_activity(
            matricule=user.matricule,
            action="login_success",
            details=f"Connexion réussie (rôle: {user.role.value}, niveau: {user.clearance_level.value})",
            ip_address=ip_address,
            metadata={"user_id": user.id}
        )
        
        # Retourner l'utilisateur et les informations du token
        return user, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    def refresh_token(
        db: Session,
        refresh_token: str,
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[Dict[str, Any]]]:
        """
        Rafraîchit un token JWT expiré
        
        Args:
            db: Session de base de données
            refresh_token: Token de rafraîchissement
            ip_address: Adresse IP du client
            
        Returns:
            Tuple contenant l'utilisateur et les informations du nouveau token
        """
        try:
            # Décoder le token de rafraîchissement
            payload = decode_token(refresh_token)
            
            # Vérifier que c'est bien un token de rafraîchissement
            if payload.get("type") != "refresh":
                log_auth_activity(
                    matricule="unknown",
                    action="refresh_token_failed",
                    details="Type de token invalide",
                    ip_address=ip_address
                )
                return None, None
            
            # Récupérer l'utilisateur à partir du matricule dans le token
            matricule = payload.get("sub")
            if not matricule:
                return None, None
            
            user = get_user_by_matricule(db, matricule)
            if not user or not user.is_active:
                log_auth_activity(
                    matricule=matricule,
                    action="refresh_token_failed",
                    details="Utilisateur introuvable ou inactif",
                    ip_address=ip_address
                )
                return None, None
            
            # Créer un nouveau token d'accès
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            additional_data = {
                "role": user.role.value,
                "clearance_level": user.clearance_level.value,
                "user_id": user.id,
                "type": "access"
            }
            
            access_token = create_access_token(
                subject=user.matricule,
                expires_delta=access_token_expires,
                additional_data=additional_data
            )
            
            # Journaliser le rafraîchissement réussi
            log_auth_activity(
                matricule=user.matricule,
                action="refresh_token_success",
                details="Token rafraîchi avec succès",
                ip_address=ip_address,
                metadata={"user_id": user.id}
            )
            
            # Retourner l'utilisateur et les informations du token
            return user, {
                "access_token": access_token,
                "refresh_token": refresh_token,  # Réutiliser le même token de rafraîchissement
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
            
        # except InvalidTokenError as e:
        #     logger.warning(f"Invalid refresh token: {str(e)}")

        except PyJWTError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            log_auth_activity(
                matricule="unknown",
                action="refresh_token_failed",
                details=f"Token invalide: {str(e)}",
                ip_address=ip_address
            )
            return None, None
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Vérifie un token JWT
        
        Args:
            token: Token JWT à vérifier
            
        Returns:
            Dictionnaire des informations du token
        """
        try:
            # Décoder le token
            payload = decode_token(token)
            
            # Préparer la réponse
            response = {
                "valid": True,
                "matricule": payload.get("sub"),
                "role": payload.get("role"),
                "clearance_level": payload.get("clearance_level"),
                "user_id": payload.get("user_id")
            }
            
            return response
            
        # except InvalidTokenError as e:
        #     logger.warning(f"Token verification failed: {str(e)}")
        
        except PyJWTError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            
            # Token invalide
            return {
                "valid": False,
                "error": str(e)
            }