import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    """
    Formateur de logs au format JSON pour une meilleure intégration
    avec les outils d'agrégation de logs
    """
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.SERVICE_NAME,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Ajouter des informations d'exception si présentes
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "value": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Ajouter des données supplémentaires si présentes
        if hasattr(record, "data"):
            log_data["data"] = record.data
        
        return json.dumps(log_data)


def setup_logging():
    """
    Configure la journalisation globale de l'application
    """
    # Obtenir le niveau de journalisation à partir des paramètres
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Supprimer tous les handlers existants
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configurer le logger racine
    root_logger.setLevel(log_level)
    
    # Créer un handler pour la sortie standard
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Utiliser le formateur JSON pour la production, et un formateur lisible pour le développement
    if settings.LOG_LEVEL == "INFO" or settings.LOG_LEVEL == "WARNING" or settings.LOG_LEVEL == "ERROR":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configurer des loggers spécifiques
    for logger_name in ["auth_service", "auth_service.api", "auth_service.security", "auth_service.db"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.propagate = True
    
    # Réduire le niveau de log pour les bibliothèques tierces
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def log_auth_activity(
    matricule: str,
    action: str,
    details: str,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Journalise une activité d'authentification
    
    Args:
        matricule: Matricule de l'utilisateur concerné
        action: Type d'action (login, logout, etc.)
        details: Description détaillée de l'activité
        ip_address: Adresse IP de l'utilisateur
        metadata: Données supplémentaires
    """
    logger = logging.getLogger("auth_service.activity")
    
    # Préparer les données du log
    log_data = {
        "matricule": matricule,
        "action": action,
        "details": details,
        "ip_address": ip_address or "unknown"
    }
    
    if metadata:
        log_data["metadata"] = metadata
    
    # Créer un record avec les données
    record = logging.LogRecord(
        name="auth_service.activity",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=f"Auth activity: {action} by {matricule}: {details}",
        args=(),
        exc_info=None
    )
    record.data = log_data
    
    # Journaliser l'activité
    logger.handle(record)

    # Note: Dans une implémentation complète, on enverrait également ces données
    # au service d'audit via une requête HTTP asynchrone