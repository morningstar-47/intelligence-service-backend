from fastapi import APIRouter

from app.api.endpoints import auth, users

api_router = APIRouter()

# Inclure les routeurs des différents modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentification"])
api_router.include_router(users.router, prefix="/users", tags=["Utilisateurs"])