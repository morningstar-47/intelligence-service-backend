from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Attachment(Base):
    """
    Modèle pour les pièces jointes aux rapports
    """
    __tablename__ = "attachment"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # Taille en octets
    file_path = Column(String(512), nullable=False)  # Chemin de stockage interne
    
    # Relation avec le rapport
    report_id = Column(Integer, ForeignKey("report.id"), nullable=False)
    report = relationship("Report", back_populates="attachments")
    
    # Métadonnées
    uploaded_by_id = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Attachment {self.id}: {self.filename}>"