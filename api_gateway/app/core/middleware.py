from fastapi import FastAPI, Request, Response
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.utils.rate_limiting import RateLimiter
from app.utils.telemetry import setup_telemetry

logger = logging.getLogger("api_gateway.middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour journaliser les requêtes HTTP
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Récupérer l'adresse IP du client
        client_ip = request.client.host if request.client else "unknown"
        
        # Journaliser la requête entrante
        logger.info(
            f"Request started: {request.method} {request.url.path} - "
            f"Client: {client_ip}"
        )
        
        # Appel à la prochaine middleware/handler
        try:
            response = await call_next(request)
            
            # Calculer le temps de traitement
            process_time = time.time() - start_time
            
            # Journaliser la réponse
            logger.info(
                f"Request completed: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.4f}s"
            )
            
            return response
            
        except Exception as e:
            # Journaliser l'erreur
            logger.error(
                f"Request failed: {request.method} {request.url.path} - "
                f"Error: {str(e)}"
            )
            
            # Relancer l'exception pour qu'elle soit gérée par le gestionnaire global
            raise


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour limiter le taux de requêtes
    """
    def __init__(self, app):
        super().__init__(app)
        self.limiter = RateLimiter(
            redis_url=settings.RATE_LIMIT_REDIS_URL,
            default_limit=settings.DEFAULT_RATE_LIMIT,
            default_period=settings.DEFAULT_RATE_LIMIT_PERIOD
        )
    
    async def dispatch(self, request: Request, call_next):
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)
        
        # Identifier le client (IP ou utilisateur si authentifié)
        client_id = self._get_client_id(request)
        
        # Vérifier si le client a dépassé la limite
        allowed, remaining, reset_time = await self.limiter.check(client_id)
        
        if not allowed:
            # Si la limite est dépassée, renvoyer 429 Too Many Requests
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time)
                }
            )
        
        # Ajouter les en-têtes de limite de taux à la réponse
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Extraire un identifiant unique pour le client
        """
        # Si l'utilisateur est authentifié, utiliser son ID
        # Sinon, utiliser l'adresse IP
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Dans une implémentation complète, on extrairait l'identifiant de l'utilisateur du JWT
            # Pour simplifier, on utilise le token complet
            return auth_header
        
        return request.client.host if request.client else "unknown"


def add_middlewares(app: FastAPI):
    """
    Ajouter tous les middlewares à l'application
    """
    # Ajouter le middleware de journalisation
    app.add_middleware(RequestLoggingMiddleware)
    
    # Ajouter le middleware de limitation de taux si activé
    if settings.ENABLE_RATE_LIMITING:
        app.add_middleware(RateLimitingMiddleware)
    
    # Configurer la télémétrie si activée
    if settings.ENABLE_TELEMETRY:
        setup_telemetry(app)