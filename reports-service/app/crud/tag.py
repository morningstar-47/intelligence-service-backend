from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.report import Tag
from app.schemas.report import TagCreate


def get_tag(db: Session, tag_id: int) -> Optional[Tag]:
    """
    Récupère un tag par son ID
    
    Args:
        db: Session de base de données
        tag_id: ID du tag
        
    Returns:
        Tag ou None si non trouvé
    """
    return db.get(Tag, tag_id)


def get_tag_by_name(db: Session, name: str) -> Optional[Tag]:
    """
    Récupère un tag par son nom
    
    Args:
        db: Session de base de données
        name: Nom du tag
        
    Returns:
        Tag ou None si non trouvé
    """
    return db.execute(select(Tag).filter(Tag.name == name)).scalar_one_or_none()


def get_tags(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None
) -> List[Tag]:
    """
    Récupère une liste de tags
    
    Args:
        db: Session de base de données
        skip: Nombre d'éléments à sauter (pagination)
        limit: Nombre maximum d'éléments à retourner
        name: Filtrer par nom
        
    Returns:
        Liste de tags
    """
    query = select(Tag)
    
    # Appliquer les filtres
    if name:
        query = query.filter(Tag.name.ilike(f"%{name}%"))
    
    # Appliquer la pagination
    query = query.offset(skip).limit(limit)
    
    # Trier par nom
    query = query.order_by(Tag.name)
    
    # Exécuter la requête
    return list(db.execute(query).scalars().all())


def count_tags(
    db: Session,
    name: Optional[str] = None
) -> int:
    """
    Compte le nombre de tags
    
    Args:
        db: Session de base de données
        name: Filtrer par nom
        
    Returns:
        Nombre de tags
    """
    query = select(func.count()).select_from(Tag)
    
    # Appliquer les filtres
    if name:
        query = query.filter(Tag.name.ilike(f"%{name}%"))
    
    # Exécuter la requête
    return db.execute(query).scalar_one()


def create_tag(
    db: Session,
    tag_in: Union[TagCreate, str]
) -> Tag:
    """
    Crée un nouveau tag
    
    Args:
        db: Session de base de données
        tag_in: Données du tag à créer ou nom du tag
        
    Returns:
        Tag créé
    """
    # Vérifier si le tag existe déjà
    tag_name = tag_in.name if isinstance(tag_in, TagCreate) else tag_in
    existing_tag = get_tag_by_name(db, tag_name)
    if existing_tag:
        return existing_tag
    
    # Créer le tag
    db_tag = Tag(
        name=tag_name
    )
    
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    
    return db_tag


def update_tag(
    db: Session,
    tag_id: int,
    tag_in: TagCreate
) -> Optional[Tag]:
    """
    Met à jour un tag existant
    
    Args:
        db: Session de base de données
        tag_id: ID du tag à mettre à jour
        tag_in: Données à mettre à jour
        
    Returns:
        Tag mis à jour ou None si non trouvé
    """
    db_tag = get_tag(db, tag_id)
    if not db_tag:
        return None
    
    # Vérifier si un tag avec le nouveau nom existe déjà
    if db_tag.name != tag_in.name:
        existing_tag = get_tag_by_name(db, tag_in.name)
        if existing_tag:
            return None
    
    # Mettre à jour le nom
    db_tag.name = tag_in.name
    
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    
    return db_tag


def delete_tag(db: Session, tag_id: int) -> Optional[Tag]:
    """
    Supprime un tag
    
    Args:
        db: Session de base de données
        tag_id: ID du tag à supprimer
        
    Returns:
        Tag supprimé ou None si non trouvé
    """
    db_tag = get_tag(db, tag_id)
    if not db_tag:
        return None
    
    db.delete(db_tag)
    db.commit()
    
    return db_tag