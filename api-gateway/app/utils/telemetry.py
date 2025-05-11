import logging
from fastapi import FastAPI, Request
from typing import Callable, Dict, List, Any
import time
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import threading
from app.core.config import settings

# Configurer le logger
logger = logging.getLogger("api_gateway.telemetry")

# Métriques Prometheus
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Active HTTP requests',
    ['method']
)

ERROR_COUNT = Counter(
    'http_request_errors_total',
    'Total HTTP request errors',
    ['method', 'endpoint', 'error_type']
)

SERVICE_HEALTH = Gauge(
    'service_health',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service']
)

# Variable pour suivre si le serveur de métriques a été démarré
metrics_server_started = False

def start_metrics_server():
    """
    Démarrer le serveur HTTP pour exposer les métriques Prometheus
    """
    global metrics_server_started
    
    if metrics_server_started:
        return
    
    try:
        start_http_server(settings.PROMETHEUS_METRICS_PORT)
        metrics_server_started = True
        logger.info(f"Prometheus metrics available on port {settings.PROMETHEUS_METRICS_PORT}")
    except Exception as e:
        logger.error(f"Failed to start Prometheus metrics server: {str(e)}")


def setup_opentelemetry():
    """
    Configurer OpenTelemetry pour les traces distribuées
    """
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.warning("OpenTelemetry not configured: missing OTEL_EXPORTER_OTLP_ENDPOINT")
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        
        # Configurer le fournisseur de traceur
        trace.set_tracer_provider(TracerProvider())
        
        # Créer un exportateur OTLP
        otlp_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        
        # Ajouter l'exportateur au fournisseur de traceur
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
        
        logger.info(f"OpenTelemetry configured with exporter at {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
        return FastAPIInstrumentor
        
    except ImportError:
        logger.warning("OpenTelemetry packages not installed. Skipping setup.")
        return None
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {str(e)}")
        return None


def setup_telemetry(app: FastAPI):
    """
    Configurer la télémétrie pour l'application
    """
    # Démarrer le serveur de métriques Prometheus
    threading.Thread(target=start_metrics_server, daemon=True).start()
    
    # Configurer OpenTelemetry si activé
    otel_instrumentor = setup_opentelemetry()
    if otel_instrumentor:
        otel_instrumentor.instrument_app(app)
    
    # Ajouter le middleware de télémétrie
    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next: Callable):
        # Incrémenter le compteur de requêtes actives
        method = request.method
        ACTIVE_REQUESTS.labels(method=method).inc()
        
        # Enregistrer le temps de début
        start_time = time.time()
        
        try:
            # Appeler le prochain middleware/handler
            response = await call_next(request)
            
            # Calculer le temps de latence
            latency = time.time() - start_time
            
            # Extraire l'endpoint (normaliser pour éviter l'explosion de cardinalité)
            endpoint = _normalize_endpoint(request.url.path)
            
            # Enregistrer les métriques de requête
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(latency)
            
            return response
            
        except Exception as e:
            # Enregistrer les erreurs
            endpoint = _normalize_endpoint(request.url.path)
            error_type = type(e).__name__
            
            ERROR_COUNT.labels(
                method=method,
                endpoint=endpoint,
                error_type=error_type
            ).inc()
            
            # Relancer l'exception
            raise
            
        finally:
            # Décrémenter le compteur de requêtes actives
            ACTIVE_REQUESTS.labels(method=method).dec()


def _normalize_endpoint(path: str) -> str:
    """
    Normaliser l'endpoint pour éviter l'explosion de cardinalité dans les métriques
    """
    path_parts = path.split('/')
    normalized_parts = []
    
    for part in path_parts:
        # Si la partie ressemble à un identifiant (nombre, UUID, etc.), la remplacer par :id
        if part.isdigit() or (len(part) > 20 and '-' in part):
            normalized_parts.append(':id')
        else:
            normalized_parts.append(part)
    
    # Reconstruire le chemin
    normalized_path = '/'.join(normalized_parts)
    
    # Si la route est trop longue, la tronquer
    if len(normalized_path) > 100:
        normalized_path = normalized_path[:100] + '...'
    
    return normalized_path


def update_service_health(service_name: str, is_healthy: bool):
    """
    Mettre à jour l'état de santé d'un service dans les métriques
    """
    SERVICE_HEALTH.labels(service=service_name).set(1 if is_healthy else 0)