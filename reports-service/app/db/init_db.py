import logging
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.report import Tag

logger = logging.getLogger("reports_service.db")


def init_db(db: Session) -> None:
    """
    Initialise la base de données avec les données par défaut
    """
    # Créer les tags par défaut
    create_default_tags(db)


def create_default_tags(db: Session) -> None:
    """
    Crée les tags par défaut s'ils n'existent pas déjà
    """
    default_tags = [
        "urgent", "stratégique", "tactique", "cyber", "maritime", 
        "aérien", "terrestre", "économique", "politique", "social", 
        "terrorisme", "crime organisé", "renseignement humain", 
        "signal", "imagerie", "source ouverte"
    ]
    
    # Vérifier quels tags existent déjà
    existing_tags = db.query(Tag.name).all()
    existing_tag_names = {tag[0] for tag in existing_tags}
    
    # Créer les tags manquants
    for tag_name in default_tags:
        if tag_name not in existing_tag_names:
            tag = Tag(name=tag_name)
            db.add(tag)
    
    if len(default_tags) > len(existing_tag_names):
        db.commit()
        logger.info(f"Created {len(default_tags) - len(existing_tag_names)} default tags")
    else:
        logger.info("Default tags already exist")