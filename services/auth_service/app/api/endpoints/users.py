from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin, get_current_active_user
from app.core.logging import log_auth_activity
from app.crud.user import (
    get_user, get_users, create_user, update_user, 
    delete_user, deactivate_user, change_user_password
)
from app.models.user import User
from app.schemas.user import (
    User as UserSchema, UserCreate, UserUpdate, UserList,
    ChangePassword
)

router = APIRouter()


@router.get("/", response_model=UserList)
def read_users(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    role: str = Query(None),
    clearance_level: str = Query(None),
    is_active: bool = Query(None),
    search: str = Query(None)
) -> Any:
    """
    Récupère la liste des utilisateurs (admin seulement)
    """
    # Récupérer les utilisateurs
    users, total = get_users(
        db=db,
        skip=skip,
        limit=limit,
        role=role,
        clearance_level=clearance_level,
        is_active=is_active,
        search=search
    )
    
    return {
        "items": users,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 0
    }


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_new_user(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    user_in: UserCreate
) -> Any:
    """
    Crée un nouvel utilisateur (admin seulement)
    """
    # Créer l'utilisateur
    user = create_user(db, user_in)
    
    # Journaliser l'action
    log_auth_activity(
        matricule=current_user.matricule,
        action="user_create",
        details=f"Création d'un nouvel utilisateur: {user_in.matricule} (rôle: {user_in.role})",
        metadata={"created_user_id": user.id}
    )
    
    return user


@router.get("/me", response_model=UserSchema)
def read_user_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Récupère les informations de l'utilisateur connecté
    """
    return current_user


@router.put("/me", response_model=UserSchema)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    user_in: UserUpdate
) -> Any:
    """
    Met à jour les informations de l'utilisateur connecté
    """
    # Empêcher les utilisateurs de changer leur propre rôle ou niveau d'habilitation
    if user_in.role is not None or user_in.clearance_level is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas modifier votre propre rôle ou niveau d'habilitation"
        )
    
    # Mettre à jour l'utilisateur
    updated_user = update_user(db, current_user.id, user_in)
    
    # Journaliser l'action
    log_auth_activity(
        matricule=current_user.matricule,
        action="user_self_update",
        details="Mise à jour des informations personnelles"
    )
    
    return updated_user


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
def change_my_password(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    password_data: ChangePassword
) -> Any:
    """
    Change le mot de passe de l'utilisateur connecté
    """
    # Changer le mot de passe
    user = change_user_password(
        db,
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )
    
    # Journaliser l'action
    log_auth_activity(
        matricule=current_user.matricule,
        action="password_change",
        details="Changement de mot de passe réussi"
    )
    
    return {"detail": "Mot de passe modifié avec succès"}


@router.get("/{user_id}", response_model=UserSchema)
def read_user(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    user_id: int = Path(..., gt=0)
) -> Any:
    """
    Récupère les détails d'un utilisateur spécifique (admin seulement)
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return user


@router.put("/{user_id}", response_model=UserSchema)
def update_user_info(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    user_id: int = Path(..., gt=0),
    user_in: UserUpdate
) -> Any:
    """
    Met à jour les informations d'un utilisateur (admin seulement)
    """
    # Récupérer l'utilisateur
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Mettre à jour l'utilisateur
    updated_user = update_user(db, user_id, user_in)
    
    # Journaliser l'action
    log_auth_activity(
        matricule=current_user.matricule,
        action="user_update",
        details=f"Mise à jour de l'utilisateur: {user.matricule} (ID: {user_id})"
    )
    
    return updated_user


@router.delete("/{user_id}", response_model=UserSchema)
def delete_user_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    user_id: int = Path(..., gt=0)
) -> Any:
    """
    Supprime un utilisateur (admin seulement)
    """
    # Récupérer l'utilisateur
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Empêcher la suppression de son propre compte
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer votre propre compte"
        )
    
    # Journaliser l'action
    log_auth_activity(
        matricule=current_user.matricule,
        action="user_delete",
        details=f"Suppression de l'utilisateur: {user.matricule} (ID: {user_id})"
    )
    
    # Supprimer l'utilisateur
    deleted_user = delete_user(db, user_id)
    
    return deleted_user


@router.post("/{user_id}/deactivate", response_model=UserSchema)
def deactivate_user_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    user_id: int = Path(..., gt=0)
) -> Any:
    """
    Désactive un compte utilisateur (admin seulement)
    """
    # Récupérer l'utilisateur
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Empêcher la désactivation de son propre compte
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de désactiver votre propre compte"
        )
    
    # Journaliser l'action
    log_auth_activity(
        matricule=current_user.matricule,
        action="user_deactivate",
        details=f"Désactivation de l'utilisateur: {user.matricule} (ID: {user_id})"
    )
    
    # Désactiver l'utilisateur
    deactivated_user = deactivate_user(db, user_id)
    
    return deactivated_user