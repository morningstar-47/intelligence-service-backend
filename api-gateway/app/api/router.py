# api-gateway/app/api/router.py
import httpx
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, List, Any
import time
import asyncio

from app.core.config import settings
from app.utils.errors import ServiceUnavailableError, ProxyError

router = APIRouter()
logger = logging.getLogger("api_gateway.router")

# Timeout par défaut pour les requêtes HTTP (en secondes)
DEFAULT_TIMEOUT = 30.0

# Créer un client HTTP asynchrone réutilisable
http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)

# État des services
service_health = {}

# Routes internes gérées par l'API Gateway lui-même
INTERNAL_ROUTES = {
    "/health": "health_check",
    "/routes": "list_routes",
    "/services/health": "service_health_check"
}


async def check_service_health(service_path: str) -> bool:
    """
    Vérifier si un service est disponible en appelant son endpoint de santé
    """
    service_info = settings.SERVICE_ROUTES.get(service_path)
    
    if not service_info:
        return False
    
    service_url = service_info.get("url")
    health_endpoint = service_info.get("health", "/health")
    
    if not service_url:
        return False
    
    try:
        url = f"{service_url}{health_endpoint}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            is_healthy = response.status_code == 200
            
            # Mettre à jour l'état du service
            service_health[service_path] = {
                "is_healthy": is_healthy,
                "last_checked": time.time()
            }
            
            return is_healthy
    except Exception as e:
        logger.error(f"Health check failed for {service_path}: {str(e)}")
        
        # Marquer le service comme indisponible
        service_health[service_path] = {
            "is_healthy": False,
            "last_checked": time.time(),
            "error": str(e)
        }
        
        return False


async def get_service_url(path: str) -> str:
    """
    Obtenir l'URL du service approprié pour un chemin donné
    """
    # Normaliser le chemin pour la correspondance
    normalized_path = path
    if not normalized_path.startswith('/'):
        normalized_path = '/' + normalized_path
        
    # Vérifier s'il s'agit d'une route API dirigée vers un service
    for route_prefix, service_info in settings.SERVICE_ROUTES.items():
        # Vérifier si le chemin commence par le préfixe de route
        if normalized_path.startswith(route_prefix):
            service_url = service_info.get("url")
            if not service_url:
                raise ServiceUnavailableError(f"Service configuration for {route_prefix} is missing")
                
            # Vérifier l'état du service si la dernière vérification date de plus de 60 secondes
            service_status = service_health.get(route_prefix, {})
            last_checked = service_status.get("last_checked", 0)
            is_healthy = service_status.get("is_healthy", True)  # Présumer que le service est en bonne santé
            
            current_time = time.time()
            if current_time - last_checked > 60 or not is_healthy:
                # Vérifier l'état du service de manière asynchrone (ne pas attendre le résultat)
                asyncio.create_task(check_service_health(route_prefix))
            
            return service_url
    
    # Si aucun service n'est trouvé pour cette route
    raise HTTPException(status_code=404, detail=f"No service configured for path: {path}")


async def preserve_headers(request: Request) -> Dict[str, str]:
    """
    Préserver les en-têtes HTTP pertinents lors du transfert de la requête
    """
    headers = dict(request.headers)
    
    # Supprimer les en-têtes qui ne doivent pas être transmis
    headers.pop("host", None)
    headers.pop("connection", None)
    headers.pop("content-length", None)
    
    # Ajouter l'en-tête X-Forwarded-For
    if "x-forwarded-for" in headers:
        client_ip = request.client.host if request.client else "unknown"
        headers["x-forwarded-for"] = f"{headers['x-forwarded-for']}, {client_ip}"
    else:
        client_ip = request.client.host if request.client else "unknown"
        headers["x-forwarded-for"] = client_ip
    
    # Ajouter un en-tête secret pour que les services sachent que la requête vient du gateway
    headers["x-gateway-secret"] = settings.PROXY_SECRET_KEY
    
    return headers


@router.get("/health")
async def health_check():
    """
    Point de terminaison de santé
    """
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0"
    }


@router.get("/routes")
async def list_routes():
    """
    Liste les routes disponibles
    """
    return {
        "routes": [
            {
                "prefix": prefix,
                "service_url": info.get("url"),
                "health_endpoint": info.get("health", "/health")
            }
            for prefix, info in settings.SERVICE_ROUTES.items()
        ],
        "internal_routes": list(INTERNAL_ROUTES.keys())
    }


@router.get("/services/health")
async def service_health_check():
    """
    Vérifier l'état de santé de tous les services
    """
    health_results = {}
    
    # Vérifier l'état de santé de chaque service en parallèle
    tasks = []
    for service_path in settings.SERVICE_ROUTES:
        tasks.append(check_service_health(service_path))
    
    results = await asyncio.gather(*tasks)
    
    # Construire la réponse
    for i, service_path in enumerate(settings.SERVICE_ROUTES):
        service_info = settings.SERVICE_ROUTES[service_path]
        service_status = service_health.get(service_path, {})
        
        health_results[service_path] = {
            "url": service_info.get("url"),
            "is_healthy": results[i],
            "last_checked": service_status.get("last_checked", time.time()),
            "error": service_status.get("error")
        }
    
    return {
        "gateway_status": "healthy",
        "services": health_results
    }


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_request(request: Request, path: str):
    """
    Proxy toutes les requêtes vers le service approprié, sauf les routes internes
    """
    # Créer le chemin complet (en ajoutant un slash au début si nécessaire)
    full_path = path if path.startswith('/') else '/' + path
    
    # Vérifier si c'est une route interne
    if full_path in INTERNAL_ROUTES:
        handler_name = INTERNAL_ROUTES[full_path]
        handler = globals().get(handler_name)
        if handler and callable(handler):
            return await handler()
        else:
            logger.error(f"Internal route handler '{handler_name}' not found")
            return Response(
                content="Internal server error",
                status_code=500
            )
    
    try:
        # Obtenir l'URL du service cible
        service_url = await get_service_url(path)
        
        # Construire l'URL complète
        target_url = f"{service_url}/{path}"
        
        # Préserver les en-têtes pertinents
        headers = await preserve_headers(request)
        
        # Obtenir le corps de la requête si applicable
        content = await request.body()
        
        # Envoyer la requête au service cible avec la méthode HTTP d'origine
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=content,
                params=request.query_params,
                follow_redirects=True
            )
            
            # Journaliser la requête proxy
            logger.info(
                f"Proxied {request.method} {path} to {target_url} - "
                f"Status: {response.status_code}"
            )
            
            # Créer la réponse avec les en-têtes et le contenu du service cible
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except ServiceUnavailableError as e:
        logger.error(f"Service unavailable: {str(e)}")
        return Response(
            content=str(e),
            status_code=503,
            headers={"Content-Type": "text/plain"}
        )
    
    except httpx.TimeoutException:
        logger.error(f"Request timeout for path: {path}")
        return Response(
            content="Service timeout. Please try again later.",
            status_code=504,
            headers={"Content-Type": "text/plain"}
        )
    
    except httpx.RequestError as e:
        logger.error(f"Request error for path {path}: {str(e)}")
        return Response(
            content=f"Unable to reach the service: {str(e)}",
            status_code=502,
            headers={"Content-Type": "text/plain"}
        )
    
    except Exception as e:
        logger.error(f"Proxy error for path {path}: {str(e)}", exc_info=True)
        return Response(
            content="An internal error occurred while processing your request.",
            status_code=500,
            headers={"Content-Type": "text/plain"}
        )