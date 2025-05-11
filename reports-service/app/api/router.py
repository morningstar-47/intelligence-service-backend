from fastapi import APIRouter

from app.api.endpoints import reports, comments, attachments, tags

api_router = APIRouter()

# Inclure les routeurs des différents modules
api_router.include_router(reports.router, prefix="/reports", tags=["Rapports"])
api_router.include_router(comments.router, prefix="/comments", tags=["Commentaires"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["Pièces jointes"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])