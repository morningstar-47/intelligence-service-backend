from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_info, get_admin_user
from app.crud.tag import get_tag, get_tags, count_tags, create_tag, update_tag, delete_tag
from app.schemas.report import Tag, TagCreate

router = APIRouter()


@router.get("/", response_model=List[Tag])
async def read_tags(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    name: str = Query(None)
) -> Any:
    """
    Récupère la liste des tags
    """
    tags = get_tags(db, skip=skip, limit=limit, name=name)
    return tags


@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_new_tag(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_admin_user),  # Seul un admin peut créer des tags
    tag_in: TagCreate
) -> Any:
    """
    Crée un nouveau tag (admin seulement)
    """
    # Vérifier si le tag existe déjà
    existing_tag = get_tag_by_name(db, tag_in.name)
    if existing_tag:
        return existing_tag
    
    # Créer le tag
    tag = create_tag(db, tag_in)
    
    return tag


@router.get("/{tag_id}", response_model=Tag)
async def read_tag(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    tag_id: int = Path(..., gt=0)
) -> Any:
    """
    Récupère un tag spécifique
    """
    tag = get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag non trouvé"
        )
    
    return tag


@router.put("/{tag_id}", response_model=Tag)
async def update_tag_info(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_admin_user),  # Seul un admin peut modifier des tags
    tag_id: int = Path(..., gt=0),
    tag_in: TagCreate
) -> Any:
    """
    Met à jour un tag existant (admin seulement)
    """
    tag = update_tag(db, tag_id, tag_in)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag non trouvé ou nom de tag déjà utilisé"
        )
    
    return tag


@router.delete("/{tag_id}", response_model=Tag)
async def delete_tag_endpoint(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_admin_user),  # Seul un admin peut supprimer des tags
    tag_id: int = Path(..., gt=0)
) -> Any:
    """
    Supprime un tag (admin seulement)
    """
    tag = delete_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag non trouvé"
        )
    
    return tag