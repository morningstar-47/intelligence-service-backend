from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Comment(Base):
    """
    Modèle pour les commentaires sur les rapports
    """
    __tablename__ = "comment"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    
    # Relations
    report_id = Column(Integer, ForeignKey("report.id"), nullable=False)
    report = relationship("Report", back_populates="comments")
    
    # Informations sur l'utilisateur (stockées uniquement par ID car 
    # les données utilisateur complètes sont gérées par le service d'authentification)
    user_id = Column(Integer, nullable=False)
    
    # Métadonnées
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Comment {self.id} by User {self.user_id} on Report {self.report_id}>"