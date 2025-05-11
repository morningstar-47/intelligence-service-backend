from typing import Any
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Classe de base pour tous les modèles SQLAlchemy
    """
    id: Any
    
    # Générer le nom de la table automatiquement à partir du nom de la classe
    @declared_attr
    def __tablename__(cls) -> str:
        # Conversion du nom de classe CamelCase en snake_case
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return name