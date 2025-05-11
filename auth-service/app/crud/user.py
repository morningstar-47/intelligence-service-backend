from typing import Any, Dict, Optional, Union, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole, ClearanceLevel
from app.schemas.user import UserCreate, UserUpdate


def get_user(db: Session, user_id: int) -> Optional[User]:
    """
    Récupère un utilisateur par son ID
    
    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        
    Returns:
        User ou None si non trouvé
    """
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Récupère un utilisateur par son email
    
    Args:
        db: Session de base de données
        email: Email de l'utilisateur
        
    Returns:
        User ou None si non trouvé
    """
    return db.execute(select(User).filter(User.email == email)).scalar_one_or_none()


def get_user_by_matricule(db: Session, matricule: str) -> Optional[User]:
    """
    Récupère un utilisateur par son matricule
    
    Args:
        db: Session de base de données
        matricule: Matricule de l'utilisateur (ex: AF-1234P)
        
    Returns:
        User ou None si non trouvé
    """
    return db.execute(select(User).filter(User.matricule == matricule)).scalar_one_or_none()


def get_users(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    role: Optional[str] = None,
    clearance_level: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> Tuple[List[User], int]:
    """
    Récupère une liste d'utilisateurs avec filtrage optionnel
    
    Args:
        db: Session de base de données
        skip: Nombre d'éléments à sauter (pagination)
        limit: Nombre maximum d'éléments à retourner
        role: Filtrer par rôle
        clearance_level: Filtrer par niveau d'habilitation
        is_active: Filtrer par statut (actif/inactif)
        search: Recherche textuelle (matricule, nom, email)
        
    Returns:
        Tuple contenant la liste des utilisateurs et le nombre total
    """
    # Construire la requête
    query = select(User)
    
    # Appliquer les filtres
    if role:
        query = query.filter(User.role == UserRole(role))
    
    if clearance_level:
        query = query.filter(User.clearance_level == ClearanceLevel(clearance_level))
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.matricule.ilike(search_term)) |
            (User.full_name.ilike(search_term)) |
            (User.email.ilike(search_term))
        )
    
    # Compter le nombre total d'utilisateurs
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()
    
    # Appliquer la pagination
    query = query.offset(skip).limit(limit)
    
    # Exécuter la requête
    users = db.execute(query).scalars().all()
    
    return users, total


def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Crée un nouvel utilisateur
    
    Args:
        db: Session de base de données
        user_in: Données de l'utilisateur à créer
        
    Returns:
        Utilisateur créé
    """
    # Convertir le rôle et le niveau d'habilitation en énumérations
    role = UserRole(user_in.role)
    clearance_level = ClearanceLevel(user_in.clearance_level)
    
    # Créer l'utilisateur
    db_user = User(
        matricule=user_in.matricule,
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=role,
        clearance_level=clearance_level,
        is_active=user_in.is_active
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def update_user(
    db: Session, 
    user_id: int, 
    user_in: Union[UserUpdate, Dict[str, Any]]
) -> Optional[User]:
    """
    Met à jour un utilisateur existant
    
    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur à mettre à jour
        user_in: Données à mettre à jour
        
    Returns:
        Utilisateur mis à jour ou None si non trouvé
    """
    # Récupérer l'utilisateur
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    # Convertir les données d'entrée en dictionnaire si nécessaire
    update_data = user_in.model_dump(exclude_unset=True) if not isinstance(user_in, dict) else user_in
    
    # Traiter le mot de passe séparément
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        update_data["hashed_password"] = hashed_password
        del update_data["password"]
    
    # Convertir le rôle et le niveau d'habilitation en énumérations si présents
    if "role" in update_data and update_data["role"]:
        update_data["role"] = UserRole(update_data["role"])
    
    if "clearance_level" in update_data and update_data["clearance_level"]:
        update_data["clearance_level"] = ClearanceLevel(update_data["clearance_level"])
    
    # Mettre à jour les attributs
    for field, value in update_data.items():
        if hasattr(db_user, field) and value is not None:
            setattr(db_user, field, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def update_user_last_login(db: Session, user_id: int, last_login: datetime) -> Optional[User]:
    """
    Met à jour la date de dernière connexion d'un utilisateur
    
    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        last_login: Date de dernière connexion
        
    Returns:
        Utilisateur mis à jour ou None si non trouvé
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db_user.last_login = last_login
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def delete_user(db: Session, user_id: int) -> Optional[User]:
    """
    Supprime un utilisateur
    
    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur à supprimer
        
    Returns:
        Utilisateur supprimé ou None si non trouvé
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db.delete(db_user)
    db.commit()
    
    return db_user


def deactivate_user(db: Session, user_id: int) -> Optional[User]:
    """
    Désactive un utilisateur (alternative à la suppression)
    
    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur à désactiver
        
    Returns:
        Utilisateur désactivé ou None si non trouvé
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db_user.is_active = False
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def authenticate_user(db: Session, matricule: str, password: str) -> Optional[User]:
    """
    Authentifie un utilisateur par matricule et mot de passe
    
    Args:
        db: Session de base de données
        matricule: Matricule de l'utilisateur
        password: Mot de passe en clair
        
    Returns:
        Utilisateur authentifié ou None si échec
    """
    user = get_user_by_matricule(db, matricule)
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def change_user_password(
    db: Session, 
    user_id: int, 
    current_password: str, 
    new_password: str
) -> Optional[User]:
    """
    Change le mot de passe d'un utilisateur
    
    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        current_password: Mot de passe actuel
        new_password: Nouveau mot de passe
        
    Returns:
        Utilisateur mis à jour ou None si échec
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    # Vérifier le mot de passe actuel
    if not verify_password(current_password, db_user.hashed_password):
        return None
    
    # Mettre à jour le mot de passe
    db_user.hashed_password = get_password_hash(new_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def count_users(
    db: Session,
    role: Optional[str] = None,
    clearance_level: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """
    Compte le nombre d'utilisateurs avec filtrage optionnel
    
    Args:
        db: Session de base de données
        role: Filtrer par rôle
        clearance_level: Filtrer par niveau d'habilitation
        is_active: Filtrer par statut (actif/inactif)
        search: Recherche textuelle (matricule, nom, email)
        
    Returns:
        Nombre d'utilisateurs
    """
    # Construire la requête
    query = select(func.count()).select_from(User)
    
    # Appliquer les filtres
    if role:
        query = query.filter(User.role == UserRole(role))
    
    if clearance_level:
        query = query.filter(User.clearance_level == ClearanceLevel(clearance_level))
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.matricule.ilike(search_term)) |
            (User.full_name.ilike(search_term)) |
            (User.email.ilike(search_term))
        )
    
    # Exécuter la requête
    return db.execute(query).scalar_one()