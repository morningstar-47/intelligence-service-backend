import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.middleware import add_middlewares
from app.core.logging import setup_logging
from app.api.router import router

# Configurer la journalisation
setup_logging()
logger = logging.getLogger("api_gateway")

# Initialiser l'application FastAPI
app = FastAPI(
    title="Intelligence-Service API Gateway",
    description="API Gateway pour les microservices Intelligence-Service",
    version="1.0.0",
    docs_url="/api/docs" if settings.SHOW_DOCS else None,
    redoc_url="/api/redoc" if settings.SHOW_DOCS else None,
)

# Configurer CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ajouter les middlewares personnalisés
add_middlewares(app)

# Inclure le routeur principal
app.include_router(router, prefix="/api")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware pour mesurer et journaliser le temps de traitement des requêtes
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Ajouter le temps de traitement comme en-tête
    response.headers["X-Process-Time"] = str(process_time)
    
    # Journaliser la requête
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Processing time: {process_time:.4f}s"
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Gestionnaire global d'exceptions pour capturer toutes les erreurs non gérées
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne est survenue."}
    )


@app.get("/")
async def root():
    """
    Point de terminaison racine pour vérifier si l'API Gateway fonctionne
    """
    return {
        "name": "Intelligence-Service API Gateway",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Point de terminaison de vérification de l'état de santé
    """
    return {"status": "healthy"}