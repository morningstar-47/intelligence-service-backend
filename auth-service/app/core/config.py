# app/core/config.py
from typing import List, Union, Optional, Dict, Any
import os
import secrets
from pathlib import Path
import json

from pydantic import AnyHttpUrl, field_validator, EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Nom du service
    SERVICE_NAME: str = "auth-service"
    
    # Configuration API
    API_STR: str = "/api"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    
    # Niveau de log
    LOG_LEVEL: str = "INFO"
    
    # Clé secrète pour la signature des tokens JWT
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # Configuration JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Utiliser des clés RSA pour les JWT (production)
    USE_RSA_KEYS: bool = False
    PRIVATE_KEY_FILE: Optional[str] = None
    PUBLIC_KEY_FILE: Optional[str] = None
    PRIVATE_KEY: Optional[str] = None
    PUBLIC_KEY: Optional[str] = None
    
    # Configuration CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v
    
    # Configuration de la base de données
    POSTGRES_HOST: str = "localhost"  # Valeur par défaut
    POSTGRES_PORT: str = "5432"       # Valeur par défaut
    POSTGRES_USER: str = "postgres"   # Valeur par défaut
    POSTGRES_PASSWORD: str = ""  # Valeur par défaut
    POSTGRES_DB: str = "auth_service"    # Valeur par défaut
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        
        # Utiliser les valeurs de l'objet info.data qui contient toutes les valeurs
        # validées jusqu'à présent
        data = info.data
        return f"postgresql://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_HOST')}:{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"
    
    # Utilisateur administrateur par défaut
    DEFAULT_ADMIN_MATRICULE: str = "AD-1234A"
    DEFAULT_ADMIN_PASSWORD: str = "admin_password"  # Valeur par défaut, à changer en production
    DEFAULT_ADMIN_EMAIL: EmailStr = "admin@intelligence-service.com"  # Valeur par défaut
    DEFAULT_ADMIN_FULL_NAME: str = "Administrator"
    
    # Métriques
    ENABLE_METRICS: bool = False
    METRICS_PORT: int = 9100
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    # Méthode pour charger les clés post-initialisation
    def model_post_init(self, __context):
        """
        Charge les clés RSA après l'initialisation du modèle,
        quand toutes les valeurs sont disponibles
        """
        if self.USE_RSA_KEYS:
            # Charger la clé privée si le fichier est spécifié
            if self.PRIVATE_KEY_FILE and os.path.exists(self.PRIVATE_KEY_FILE):
                with open(self.PRIVATE_KEY_FILE, "r") as f:
                    self.PRIVATE_KEY = f.read()
            
            # Charger la clé publique si le fichier est spécifié
            if self.PUBLIC_KEY_FILE and os.path.exists(self.PUBLIC_KEY_FILE):
                with open(self.PUBLIC_KEY_FILE, "r") as f:
                    self.PUBLIC_KEY = f.read()


# Créer l'instance des paramètres
settings = Settings()