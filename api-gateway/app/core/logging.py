import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    """
    Formateur de log au format JSON pour une meilleure intégration avec les outils d'agrégation de logs
    """
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
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
    Configurer la journalisation globale de l'application
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
    
    # Utiliser le formateur JSON en production, et un formateur lisible en développement
    if settings.ENV == "production":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configurer des loggers spécifiques
    for logger_name, logger_level in [
        ("api_gateway", log_level),
        ("api_gateway.router", log_level),
        ("api_gateway.middleware", log_level),
        ("uvicorn", logging.WARNING),
        ("uvicorn.access", logging.WARNING),
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        logger.propagate = True


def log_to_audit(
    action: str,
    details: str,
    user_id: str = None,
    ip_address: str = None,
    metadata: Dict[str, Any] = None
):
    """
    Envoyer un log à destination du service d'audit
    """
    logger = logging.getLogger("api_gateway.audit")
    
    # Créer un objet de données pour le log
    data = {
        "action": action,
        "details": details,
        "service": "api_gateway",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user_id:
        data["user_id"] = user_id
    
    if ip_address:
        data["ip_address"] = ip_address
    
    if metadata:
        data["metadata"] = metadata
    
    # Créer un log avec les données d'audit
    record = logging.LogRecord(
        name="api_gateway.audit",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=f"Audit log: {action} - {details}",
        args=(),
        exc_info=None
    )
    
    # Ajouter les données d'audit au record
    record.data = data
    
    # Journaliser le record
    logger.handle(record)
    
    # Dans une implémentation complète, on enverrait également ces données au service d'audit
    # via une requête HTTP asynchrone