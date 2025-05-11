import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.api.router import api_router

# Configurer la journalisation
setup_logging()
logger = logging.getLogger("reports_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexte de vie de l'application.
    Initialise la base de données au démarrage.
    """
    # Initialiser la base de données avec les données par défaut
    try:
        db = SessionLocal()
        init_db(db)
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    finally:
        db.close()
    
    logger.info("Reports service started successfully")
    yield
    logger.info("Reports service shutting down")


# Initialiser l'application FastAPI
app = FastAPI(
    title=f"{settings.SERVICE_NAME} API",
    description="Service de rapports pour le système Intelligence-Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Configurer CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware pour mesurer le temps de traitement des requêtes
    """
    start_time = time.time()
    
    # Obtenir l'adresse IP du client
    client_ip = request.client.host if request.client else "unknown"
    
    # Ajouter le temps de traitement dans les en-têtes de réponse
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Journaliser la requête
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Client: {client_ip} - "
        f"Processing time: {process_time:.4f}s"
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Gestionnaire global d'exceptions
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne est survenue"}
    )


# Inclure les routes API
app.include_router(api_router, prefix=settings.API_STR)


@app.get("/")
async def root():
    """
    Point de terminaison racine
    """
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Point de terminaison de santé
    """
    try:
        # Vérifier la connexion à la base de données
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )