from typing import List, Union, Optional, Dict, Any
import os
import json
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Nom du service
    SERVICE_NAME: str = "reports-service"
    
    # Configuration API
    API_STR: str = "/api"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8001
    
    # Niveau de log
    LOG_LEVEL: str = "INFO"
    
    # Configuration de la base de données
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "reports_service"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        
        # Utiliser les valeurs de l'objet info.data
        data = info.data
        return f"postgresql://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_HOST')}:{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"
    
    # Configuration d'authentification
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    AUTH_TOKEN_VALIDATE_PATH: str = "/api/auth/verify-token"
    
    # Configuration de l'IA
    AI_SERVICE_URL: str = "http://ai-service:8004"
    AI_ANALYSIS_ENDPOINT: str = "/api/ai/analyze-report"
    
    # Configuration du stockage
    UPLOADS_PATH: str = "/app/uploads"
    
    @field_validator("UPLOADS_PATH", mode="before")
    def create_uploads_dir(cls, v: str) -> str:
        """Crée le répertoire des uploads s'il n'existe pas"""
        os.makedirs(v, exist_ok=True)
        return v
    
    # Configuration CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # C'est probablement une chaîne JSON
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    # En cas d'erreur, essayer de le traiter comme une liste séparée par des virgules
                    v = v.strip("[]")
            
            # Traiter comme une liste séparée par des virgules
            return [i.strip() for i in v.split(",")]
        return v
    
    # Métriques
    ENABLE_METRICS: bool = False
    METRICS_PORT: int = 9101
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Créer l'instance des paramètres
settings = Settings()

# Créer le répertoire des uploads s'il n'existe pas
os.makedirs(settings.UPLOADS_PATH, exist_ok=True)