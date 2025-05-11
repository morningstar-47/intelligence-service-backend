import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ReportStatus(str, enum.Enum):
    """Statuts possibles pour un rapport de renseignement"""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# Table d'association pour les tags de rapport
report_tag = Table(
    "report_tag",
    Base.metadata,
    Column("report_id", Integer, ForeignKey("report.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.id"), primary_key=True)
)


class Report(Base):
    """
    Modèle pour les rapports de renseignement
    """
    __tablename__ = "report"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)
    classification = Column(String(50), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    coordinates = Column(String(100), nullable=True)
    report_date = Column(DateTime, default=func.now(), nullable=False)
    
    # Relations avec les utilisateurs
    submitted_by_id = Column(Integer, nullable=False)
    approved_by_id = Column(Integer, nullable=True)
    
    # Statut du rapport
    status = Column(Enum(ReportStatus), default=ReportStatus.DRAFT, nullable=False, index=True)
    
    # Métadonnées
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Données d'IA
    ai_analysis = Column(Text, nullable=True)
    threat_level = Column(String(50), nullable=True)
    credibility_score = Column(Integer, nullable=True)
    
    # Relations
    attachments = relationship("Attachment", back_populates="report", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="report", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=report_tag, back_populates="reports")
    
    def __repr__(self):
        return f"<Report {self.id}: {self.title}>"


class Tag(Base):
    """
    Modèle pour les tags associés aux rapports
    """
    __tablename__ = "tag"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    
    # Relations
    reports = relationship("Report", secondary=report_tag, back_populates="tags")
    
    def __repr__(self):
        return f"<Tag {self.id}: {self.name}>"