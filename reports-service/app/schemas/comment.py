from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# Schéma de base pour un commentaire
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1)


# Schéma pour la création d'un commentaire
class CommentCreate(CommentBase):
    report_id: int


# Schéma pour la mise à jour d'un commentaire
class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1)


# Schéma pour un commentaire (sortie)
class Comment(CommentBase):
    id: int
    report_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Schéma pour la liste des commentaires (sortie)
class CommentList(BaseModel):
    items: List[Comment]
    total: int
    
    class Config:
        from_attributes = True