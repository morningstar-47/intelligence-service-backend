from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# Schéma de base pour une pièce jointe
class AttachmentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int


# Schéma pour une pièce jointe (sortie)
class Attachment(AttachmentBase):
    id: int
    report_id: int
    uploaded_by_id: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


# Schéma pour la liste des pièces jointes (sortie)
class AttachmentList(BaseModel):
    items: List[Attachment]
    total: int
    
    class Config:
        from_attributes = True