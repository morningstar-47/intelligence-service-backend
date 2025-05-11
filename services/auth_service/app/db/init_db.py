import logging
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole, ClearanceLevel
from app.crud.user import get_user_by_matricule

logger = logging.getLogger("auth_service.db")


def init_db(db: Session) -> None:
    """
    Initialise la base de données avec les données par défaut
    """
    # Créer l'utilisateur admin par défaut s'il n'existe pas
    create_default_admin(db)


def create_default_admin(db: Session) -> None:
    """
    Crée l'utilisateur administrateur par défaut s'il n'existe pas
    """
    admin_matricule = settings.DEFAULT_ADMIN_MATRICULE
    
    # Vérifier si l'administrateur existe déjà
    user = get_user_by_matricule(db, admin_matricule)
    if user:
        logger.info(f"Default admin user {admin_matricule} already exists")
        return
    
    # Créer l'administrateur
    admin_user = User(
        matricule=admin_matricule,
        full_name=settings.DEFAULT_ADMIN_FULL_NAME,
        email=settings.DEFAULT_ADMIN_EMAIL,
        hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
        role=UserRole.ADMIN.value,
        clearance_level=ClearanceLevel.TOP_SECRET.value,
        is_active=True
    )
    
    try:
        db.add(admin_user)
        db.commit()
        logger.info(f"Created default admin user: {admin_matricule}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create default admin: {e}")
    raise

    # db.add(admin_user)
    # db.commit()
    # logger.info(f"Created default admin user: {admin_matricule}")