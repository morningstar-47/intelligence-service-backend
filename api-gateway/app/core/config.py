# app/core/config.py
from typing import List, Optional, Dict, Union, Any
import os
from pathlib import Path
import json

# Remplacer l'importation qui cause l'erreur
from pydantic import field_validator

from pydantic_settings import BaseSettings  # BaseSettings est maintenant ici

class Settings(BaseSettings):
    # API Gateway configuration
    API_GATEWAY_PORT: int = 8080
    LOG_LEVEL: str = "INFO"
    SHOW_DOCS: bool = True
    ENV: str = "production"  # production, development, testing
    
    # Service URLs
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    REPORTS_SERVICE_URL: str = "http://reports-service:8001"
    ALERTS_SERVICE_URL: str = "http://alerts-service:8002"
    MAP_SERVICE_URL: str = "http://map-service:8003"
    AI_SERVICE_URL: str = "http://ai-service:8004"
    AUDIT_SERVICE_URL: str = "http://audit-service:8005"
    
    # Development URLs
    DEV_AUTH_SERVICE_URL: Optional[str] = "http://localhost:8000"
    DEV_REPORTS_SERVICE_URL: Optional[str] = "http://localhost:8001"
    DEV_ALERTS_SERVICE_URL: Optional[str] = "http://localhost:8002"
    DEV_MAP_SERVICE_URL: Optional[str] = "http://localhost:8003"
    DEV_AI_SERVICE_URL: Optional[str] = "http://localhost:8004"
    DEV_AUDIT_SERVICE_URL: Optional[str] = "http://localhost:8005"
    
    # CORS configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # @field_validator("CORS_ORIGINS", pre=True)
    # def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
    #     if isinstance(v, str) and not v.startswith("["):
    #         return [i.strip() for i in v.split(",")]
    #     elif isinstance(v, str):
    #         return json.loads(v)
    #     return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v
        
    # Rate limiting
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_REDIS_URL: Optional[str] = None
    DEFAULT_RATE_LIMIT: int = 100
    DEFAULT_RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # Security
    PROXY_SECRET_KEY: str = "dev_secret_key"  # À remplacer en production
    JWT_PUBLIC_KEY_FILE: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None
    
    # @field_validator("JWT_PUBLIC_KEY", pre=True)
    # def load_public_key(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
    #     if v:
    #         return v
    #     key_file = values.get("JWT_PUBLIC_KEY_FILE")
    #     if key_file and os.path.exists(key_file):
    #         with open(key_file, "r") as f:
    #             return f.read()
    #     return None
    
    @field_validator("JWT_PUBLIC_KEY", mode="before")
    @classmethod
    def load_public_key(cls, v: Optional[str], info) -> Optional[str]:
        if v:
            return v
        key_file = info.data.get("JWT_PUBLIC_KEY_FILE")
        if key_file:
            key_path = Path(key_file)
            if not key_path.is_absolute():
                key_path = Path(__file__).parent / key_path
            if key_path.exists():
                return key_path.read_text()
        return None

    # Telemetry
    ENABLE_TELEMETRY: bool = False
    PROMETHEUS_METRICS_PORT: int = 9090
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    
    # Service route mapping with health check endpoints
    SERVICE_ROUTES: Dict[str, Dict[str, str]] = {}
    
    # @field_validator("SERVICE_ROUTES", pre=True)
    # def create_service_routes(cls, v: Dict[str, Dict[str, str]], values: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    #     if v:
    #         return v
            
    #     is_dev = values.get("ENV") == "development"
        
    #     routes = {
    #         "/auth": {
    #             "url": values.get("DEV_AUTH_SERVICE_URL" if is_dev else "AUTH_SERVICE_URL"),
    #             "health": "/health"
    #         },
    #         "/reports": {
    #             "url": values.get("DEV_REPORTS_SERVICE_URL" if is_dev else "REPORTS_SERVICE_URL"),
    #             "health": "/health"
    #         },
    #         "/alerts": {
    #             "url": values.get("DEV_ALERTS_SERVICE_URL" if is_dev else "ALERTS_SERVICE_URL"),
    #             "health": "/health"
    #         },
    #         "/map": {
    #             "url": values.get("DEV_MAP_SERVICE_URL" if is_dev else "MAP_SERVICE_URL"),
    #             "health": "/health"
    #         },
    #         "/ai": {
    #             "url": values.get("DEV_AI_SERVICE_URL" if is_dev else "AI_SERVICE_URL"),
    #             "health": "/health"
    #         },
    #         "/audit": {
    #             "url": values.get("DEV_AUDIT_SERVICE_URL" if is_dev else "AUDIT_SERVICE_URL"),
    #             "health": "/health"
    #         }
    #     }
        
    #     return routes
    

    @field_validator("SERVICE_ROUTES", mode="before")
    @classmethod
    def create_service_routes(cls, v: Optional[Dict[str, Dict[str, str]]], info) -> Dict[str, Dict[str, str]]:
        if v:
            return v

        values = info.data
        is_dev = values.get("ENV") == "development"

        return {
            "/auth": {
                "url": values.get("DEV_AUTH_SERVICE_URL" if is_dev else "AUTH_SERVICE_URL"),
                "health": "/health"
            },
            "/reports": {
                "url": values.get("DEV_REPORTS_SERVICE_URL" if is_dev else "REPORTS_SERVICE_URL"),
                "health": "/health"
            },
            "/alerts": {
                "url": values.get("DEV_ALERTS_SERVICE_URL" if is_dev else "ALERTS_SERVICE_URL"),
                "health": "/health"
            },
            "/map": {
                "url": values.get("DEV_MAP_SERVICE_URL" if is_dev else "MAP_SERVICE_URL"),
                "health": "/health"
            },
            "/ai": {
                "url": values.get("DEV_AI_SERVICE_URL" if is_dev else "AI_SERVICE_URL"),
                "health": "/health"
            },
            "/audit": {
                "url": values.get("DEV_AUDIT_SERVICE_URL" if is_dev else "AUDIT_SERVICE_URL"),
                "health": "/health"
            }
        }

    class Config:
        env_file = ".env"
        case_sensitive = True


# Créer et exporter l'instance des paramètres
settings = Settings()