from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Créer le moteur de base de données
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    echo=settings.LOG_LEVEL == "DEBUG"
)

# Créer la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dépendance pour obtenir une session de base de données
def get_db():
    """
    Fournit une session de base de données pour les opérations de la requête
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()