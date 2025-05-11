from typing import Any, List, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, File, UploadFile, Form
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db, get_current_user_info, 
    get_admin_user, get_commander_user,
    check_clearance_level
)
from app.core.logging import log_activity
from app.schemas.report import (
    Report as ReportSchema, ReportCreate, ReportUpdate, ReportList,
    ReportApproval, ReportAIAnalysis
)
from app.services.ai_client import analyze_report
from app.crud.report import (
    get_report, get_reports, count_reports, create_report, update_report,
    delete_report, approve_report, reject_report
)
from app.crud.tag import create_tag, get_tag_by_name

router = APIRouter()


@router.get("/", response_model=ReportList)
async def read_reports(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: str = Query(None),
    classification: str = Query(None),
    submitted_by: int = Query(None),
    approved_by: int = Query(None),
    from_date: datetime = Query(None),
    to_date: datetime = Query(None),
    search: str = Query(None),
    tags: List[str] = Query(None)
) -> Any:
    """
    Récupère la liste des rapports avec filtrage
    """
    # Déterminer les classifications autorisées en fonction du niveau d'habilitation
    clearance_level = user_info.get("clearance_level", "")
    allowed_classifications = []
    
    if clearance_level == "top_secret":
        allowed_classifications = ["top_secret", "secret", "confidential", "unclassified"]
    elif clearance_level == "secret":
        allowed_classifications = ["secret", "confidential", "unclassified"]
    elif clearance_level == "confidential":
        allowed_classifications = ["confidential", "unclassified"]
    
    # Restreindre aux rapports soumis par l'utilisateur courant pour les Field Agents
    user_role = user_info.get("role", "")
    user_id = user_info.get("user_id")
    
    if user_role == "field" and not submitted_by:
        submitted_by = user_id
    
    # Récupérer les rapports
    reports = get_reports(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        classification=classification,
        submitted_by=submitted_by,
        approved_by=approved_by,
        from_date=from_date,
        to_date=to_date,
        search=search,
        tags=tags,
        allowed_classifications=allowed_classifications
    )
    
    # Compter le nombre total de rapports pour la pagination
    total = count_reports(
        db=db,
        status=status,
        classification=classification,
        submitted_by=submitted_by,
        approved_by=approved_by,
        from_date=from_date,
        to_date=to_date,
        search=search,
        tags=tags,
        allowed_classifications=allowed_classifications
    )
    
    return {
        "items": reports,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 0,
        "page_size": limit,
        "pages": (total + limit - 1) // limit if limit > 0 else 0
    }


@router.get("/{report_id}", response_model=ReportSchema)
async def read_report(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    report_id: int = Path(..., gt=0)
) -> Any:
    """
    Récupère un rapport spécifique
    """
    # Récupérer le rapport
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    # Vérifier l'accès en fonction du niveau d'habilitation
    clearance_level = user_info.get("clearance_level", "")
    allowed_classifications = []
    
    if clearance_level == "top_secret":
        allowed_classifications = ["top_secret", "secret", "confidential", "unclassified"]
    elif clearance_level == "secret":
        allowed_classifications = ["secret", "confidential", "unclassified"]
    elif clearance_level == "confidential":
        allowed_classifications = ["confidential", "unclassified"]
    
    if report.classification not in allowed_classifications:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Niveau d'habilitation insuffisant pour accéder à ce rapport ({report.classification})"
        )
    
    # Vérifier l'accès pour les agents de terrain (uniquement leurs propres rapports)
    user_role = user_info.get("role", "")
    user_id = user_info.get("user_id")
    
    if user_role == "field" and report.submitted_by_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez consulter que vos propres rapports"
        )
    
    return report


@router.post("/", response_model=ReportSchema, status_code=status.HTTP_201_CREATED)
async def create_new_report(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    report_in: ReportCreate
) -> Any:
    """
    Crée un nouveau rapport
    """
    # Vérifier que l'utilisateur a le niveau d'habilitation nécessaire pour la classification du rapport
    clearance_level = user_info.get("clearance_level", "")
    allowed_classifications = []
    
    if clearance_level == "top_secret":
        allowed_classifications = ["top_secret", "secret", "confidential", "unclassified"]
    elif clearance_level == "secret":
        allowed_classifications = ["secret", "confidential", "unclassified"]
    elif clearance_level == "confidential":
        allowed_classifications = ["confidential", "unclassified"]
    
    if report_in.classification not in allowed_classifications:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Niveau d'habilitation insuffisant pour créer un rapport avec cette classification ({report_in.classification})"
        )
    
    # Créer le rapport
    user_id = user_info.get("user_id")
    report = create_report(db, report_in, user_id)
    
    # Analyser le rapport avec l'IA
    if report and report.id:
        try:
            # Lancer l'analyse en arrière-plan
            # Dans une application réelle, cela serait fait de manière asynchrone avec une tâche de fond
            analysis_result = await analyze_report(report)
            
            # Mettre à jour le rapport avec les résultats de l'analyse
            if analysis_result:
                update_data = {
                    "ai_analysis": analysis_result.get("summary", ""),
                    "threat_level": analysis_result.get("threat_level", ""),
                    "credibility_score": analysis_result.get("credibility_score", 0)
                }
                
                update_report(db, report.id, update_data)
                
                # Ajouter les tags suggérés
                suggested_tags = analysis_result.get("suggested_tags", [])
                for tag_name in suggested_tags:
                    # Créer le tag s'il n'existe pas
                    tag = get_tag_by_name(db, tag_name)
                    if not tag:
                        tag = create_tag(db, tag_name)
                    
                    # Ajouter le tag au rapport
                    add_tag_to_report(db, report.id, tag.id)
        
        except Exception as e:
            # Ne pas bloquer la création du rapport en cas d'erreur d'analyse
            log_activity(
                action="report_analysis_error",
                details=f"Erreur lors de l'analyse du rapport {report.id}: {str(e)}",
                user_id=user_id,
                report_id=report.id
            )
    
    log_activity(
        action="report_created",
        details=f"Rapport créé: {report.title}",
        user_id=user_id,
        report_id=report.id,
        metadata={"classification": report.classification}
    )
    
    return report


@router.put("/{report_id}", response_model=ReportSchema)
async def update_report_info(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    report_id: int = Path(..., gt=0),
    report_in: ReportUpdate
) -> Any:
    """
    Met à jour un rapport existant
    """
    # Récupérer le rapport
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    # Obtenir le rôle et l'ID de l'utilisateur
    user_role = user_info.get("role", "")
    user_id = user_info.get("user_id")
    
    # Vérifier les permissions (seul l'auteur peut modifier son rapport, ou un admin/commander)
    if (user_role == "field" and report.submitted_by_id != user_id) or \
       (user_role not in ["admin", "commander"] and report.submitted_by_id != user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à modifier ce rapport"
        )
    
    # Vérifier que le rapport n'est pas déjà approuvé/rejeté/archivé (sauf pour les admins)
    if user_role != "admin" and report.status in ["approved", "rejected", "archived"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de modifier un rapport avec le statut {report.status}"
        )
    
    # Vérifier la classification si elle est modifiée
    if report_in.classification and report_in.classification != report.classification:
        clearance_level = user_info.get("clearance_level", "")
        allowed_classifications = []
        
        if clearance_level == "top_secret":
            allowed_classifications = ["top_secret", "secret", "confidential", "unclassified"]
        elif clearance_level == "secret":
            allowed_classifications = ["secret", "confidential", "unclassified"]
        elif clearance_level == "confidential":
            allowed_classifications = ["confidential", "unclassified"]
        
        if report_in.classification not in allowed_classifications:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Niveau d'habilitation insuffisant pour attribuer cette classification ({report_in.classification})"
            )
    
    # Mettre à jour le rapport
    updated_report = update_report(db, report_id, report_in)
    
    log_activity(
        action="report_updated",
        details=f"Rapport mis à jour: {report.title} (ID: {report_id})",
        user_id=user_id,
        report_id=report_id
    )
    
    return updated_report


@router.delete("/{report_id}", response_model=ReportSchema)
async def delete_report_endpoint(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_admin_user),  # Seul un admin peut supprimer un rapport
    report_id: int = Path(..., gt=0)
) -> Any:
    """
    Supprime un rapport (admin seulement)
    """
    # Récupérer le rapport
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    # Supprimer le rapport
    deleted_report = delete_report(db, report_id)
    
    user_id = user_info.get("user_id")
    log_activity(
        action="report_deleted",
        details=f"Rapport supprimé: {report.title} (ID: {report_id})",
        user_id=user_id,
        report_id=report_id
    )
    
    return deleted_report


@router.post("/{report_id}/approve", response_model=ReportSchema)
async def approve_report_endpoint(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_commander_user),  # Seul un commander ou admin peut approuver
    report_id: int = Path(..., gt=0),
    approval: ReportApproval
) -> Any:
    """
    Approuve ou rejette un rapport
    """
    # Récupérer le rapport
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    # Vérifier que le rapport est en attente d'approbation
    if report.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le rapport n'est pas en attente d'approbation (statut actuel: {report.status})"
        )
    
    # Vérifier le niveau d'habilitation
    clearance_level = user_info.get("clearance_level", "")
    allowed_classifications = []
    
    if clearance_level == "top_secret":
        allowed_classifications = ["top_secret", "secret", "confidential", "unclassified"]
    elif clearance_level == "secret":
        allowed_classifications = ["secret", "confidential", "unclassified"]
    elif clearance_level == "confidential":
        allowed_classifications = ["confidential", "unclassified"]
    
    if report.classification not in allowed_classifications:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Niveau d'habilitation insuffisant pour approuver ce rapport ({report.classification})"
        )
    
    user_id = user_info.get("user_id")
    
    # Approuver ou rejeter le rapport
    if approval.approved:
        updated_report = approve_report(db, report_id, user_id)
        action = "approved"
    else:
        updated_report = reject_report(db, report_id, user_id, approval.rejection_reason)
        action = "rejected"
    
    log_activity(
        action=f"report_{action}",
        details=f"Rapport {action}: {report.title} (ID: {report_id})",
        user_id=user_id,
        report_id=report_id,
        metadata={"reason": approval.rejection_reason if not approval.approved else None}
    )
    
    return updated_report


@router.post("/{report_id}/submit", response_model=ReportSchema)
async def submit_report_for_approval(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    report_id: int = Path(..., gt=0)
) -> Any:
    """
    Soumet un rapport pour approbation
    """
    # Récupérer le rapport
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )
    
    # Vérifier que l'utilisateur est l'auteur du rapport ou un admin
    user_role = user_info.get("role", "")
    user_id = user_info.get("user_id")
    
    if user_role != "admin" and report.submitted_by_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à soumettre ce rapport"
        )
    
    # Vérifier que le rapport est en état de brouillon
    if report.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de soumettre un rapport avec le statut {report.status}"
        )
    
    # Mettre à jour le statut du rapport
    updated_report = update_report(db, report_id, {"status": "pending"})
    
    log_activity(
        action="report_submitted",
        details=f"Rapport soumis pour approbation: {report.title} (ID: {report_id})",
        user_id=user_id,
        report_id=report_id
    )
    
    return updated_report


@router.post("/{report_id}/analyze", response_model=ReportAIAnalysis)
async def analyze_report_with_ai(
    *,
    db: Session = Depends(get_db),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    report_id: int = Path(..., gt=0)
) -> Any:
    """
    Analyse un rapport avec l'IA
    """
    # Récupérer le rapport
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport non trouvé"
        )

    # Vérifier l'accès au rapport
    clearance_level = user_info.get("clearance_level", "")
    allowed_classifications = []
    
    if clearance_level == "top_secret":
        allowed_classifications = ["top_secret", "secret", "confidential", "unclassified"]
    elif clearance_level == "secret":
        allowed_classifications = ["secret", "confidential", "unclassified"]
    elif clearance_level == "confidential":
        allowed_classifications = ["confidential", "unclassified"]
    
    if report.classification not in allowed_classifications:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Niveau d'habilitation insuffisant pour accéder à l'analyse de ce rapport ({report.classification})"
        )
    
    # Vérifier l'accès pour les agents de terrain (uniquement leurs propres rapports)
    user_role = user_info.get("role", "")
    user_id = user_info.get("user_id")
    
    if user_role == "field" and report.submitted_by_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez accéder qu'à l'analyse de vos propres rapports"
        )
    
    # Analyser le rapport
    try:
        analysis_result = await analyze_report(report)
        
        if not analysis_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de l'analyse du rapport par l'IA"
            )
        
        # Mettre à jour le rapport avec les résultats de l'analyse
        update_data = {
            "ai_analysis": analysis_result.get("summary", ""),
            "threat_level": analysis_result.get("threat_level", ""),
            "credibility_score": analysis_result.get("credibility_score", 0)
        }
        
        update_report(db, report_id, update_data)
        
        # Ajouter les tags suggérés
        suggested_tags = analysis_result.get("suggested_tags", [])
        for tag_name in suggested_tags:
            # Créer le tag s'il n'existe pas
            tag = get_tag_by_name(db, tag_name)
            if not tag:
                tag = create_tag(db, tag_name)
            
            # Ajouter le tag au rapport
            add_tag_to_report(db, report_id, tag.id)
        
        return analysis_result
    
    except Exception as e:
        log_activity(
            action="report_analysis_error",
            details=f"Erreur lors de l'analyse du rapport {report_id}: {str(e)}",
            user_id=user_id,
            report_id=report_id
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'analyse du rapport: {str(e)}"
        )