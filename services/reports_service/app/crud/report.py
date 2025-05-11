from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from app.models.report import Report, ReportStatus, Tag, report_tag
from app.schemas.report import ReportCreate, ReportUpdate


def get_report(db: Session, report_id: int) -> Optional[Report]:
    """
    Récupère un rapport par son ID
    
    Args:
        db: Session de base de données
        report_id: ID du rapport
        
    Returns:
        Report ou None si non trouvé
    """
    return db.get(Report, report_id)


def get_reports(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    classification: Optional[str] = None,
    submitted_by: Optional[int] = None,
    approved_by: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = None,
    allowed_classifications: Optional[List[str]] = None
) -> List[Report]:
    """
    Récupère une liste de rapports avec filtrage
    
    Args:
        db: Session de base de données
        skip: Nombre d'éléments à sauter (pagination)
        limit: Nombre maximum d'éléments à retourner
        status: Filtrer par statut
        classification: Filtrer par classification
        submitted_by: Filtrer par auteur
        approved_by: Filtrer par approbateur
        from_date: Date de début
        to_date: Date de fin
        search: Recherche textuelle
        tags: Filtrer par tags
        allowed_classifications: Classifications autorisées pour l'utilisateur
        
    Returns:
        Liste de rapports
    """
    query = select(Report)
    
    # Appliquer les filtres
    if status:
        query = query.filter(Report.status == ReportStatus(status))
    
    if classification:
        query = query.filter(Report.classification == classification)
    
    if submitted_by:
        query = query.filter(Report.submitted_by_id == submitted_by)
    
    if approved_by:
        query = query.filter(Report.approved_by_id == approved_by)
    
    if from_date:
        query = query.filter(Report.report_date >= from_date)
    
    if to_date:
        query = query.filter(Report.report_date <= to_date)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Report.title.ilike(search_term),
                Report.content.ilike(search_term),
                Report.source.ilike(search_term),
                Report.location.ilike(search_term)
            )
        )
    
    if tags:
        # Filtrer par tags
        for tag_name in tags:
            tag_subquery = select(Tag.id).filter(Tag.name == tag_name).scalar_subquery()
            query = query.filter(
                Report.id.in_(
                    select(report_tag.c.report_id)
                    .filter(report_tag.c.tag_id == tag_subquery)
                    .scalar_subquery()
                )
            )
    
    if allowed_classifications:
        # Filtrer par classifications autorisées
        query = query.filter(Report.classification.in_(allowed_classifications))
    
    # Appliquer la pagination
    query = query.offset(skip).limit(limit)
    
    # Trier par date de rapport (du plus récent au plus ancien)
    query = query.order_by(Report.report_date.desc())
    
    # Exécuter la requête
    return list(db.execute(query).scalars().all())


def count_reports(
    db: Session,
    status: Optional[str] = None,
    classification: Optional[str] = None,
    submitted_by: Optional[int] = None,
    approved_by: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = None,
    allowed_classifications: Optional[List[str]] = None
) -> int:
    """
    Compte le nombre de rapports avec filtrage
    
    Args:
        db: Session de base de données
        status: Filtrer par statut
        classification: Filtrer par classification
        submitted_by: Filtrer par auteur
        approved_by: Filtrer par approbateur
        from_date: Date de début
        to_date: Date de fin
        search: Recherche textuelle
        tags: Filtrer par tags
        allowed_classifications: Classifications autorisées pour l'utilisateur
        
    Returns:
        Nombre de rapports
    """
    query = select(func.count()).select_from(Report)
    
    # Appliquer les filtres
    if status:
        query = query.filter(Report.status == ReportStatus(status))
    
    if classification:
        query = query.filter(Report.classification == classification)
    
    if submitted_by:
        query = query.filter(Report.submitted_by_id == submitted_by)
    
    if approved_by:
        query = query.filter(Report.approved_by_id == approved_by)
    
    if from_date:
        query = query.filter(Report.report_date >= from_date)
    
    if to_date:
        query = query.filter(Report.report_date <= to_date)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Report.title.ilike(search_term),
                Report.content.ilike(search_term),
                Report.source.ilike(search_term),
                Report.location.ilike(search_term)
            )
        )
    
    if tags:
        # Filtrer par tags
        for tag_name in tags:
            tag_subquery = select(Tag.id).filter(Tag.name == tag_name).scalar_subquery()
            query = query.filter(
                Report.id.in_(
                    select(report_tag.c.report_id)
                    .filter(report_tag.c.tag_id == tag_subquery)
                    .scalar_subquery()
                )
            )
    
    if allowed_classifications:
        # Filtrer par classifications autorisées
        query = query.filter(Report.classification.in_(allowed_classifications))
    
    # Exécuter la requête
    return db.execute(query).scalar_one()


def create_report(
    db: Session,
    report_in: ReportCreate,
    user_id: int
) -> Report:
    """
    Crée un nouveau rapport
    
    Args:
        db: Session de base de données
        report_in: Données du rapport à créer
        user_id: ID de l'utilisateur qui crée le rapport
        
    Returns:
        Rapport créé
    """
    db_report = Report(
        title=report_in.title,
        content=report_in.content,
        source=report_in.source,
        classification=report_in.classification,
        location=report_in.location,
        coordinates=report_in.coordinates,
        submitted_by_id=user_id,
        status=ReportStatus.DRAFT
    )
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return db_report


def update_report(
    db: Session,
    report_id: int,
    report_in: Union[ReportUpdate, Dict[str, Any]]
) -> Optional[Report]:
    """
    Met à jour un rapport existant
    
    Args:
        db: Session de base de données
        report_id: ID du rapport à mettre à jour
        report_in: Données à mettre à jour
        
    Returns:
        Rapport mis à jour ou None si non trouvé
    """
    db_report = get_report(db, report_id)
    if not db_report:
        return None
    
    # Convertir les données d'entrée en dictionnaire si nécessaire
    update_data = report_in.model_dump(exclude_unset=True) if not isinstance(report_in, dict) else report_in
    
    # Convertir le statut en énumération si présent
    if "status" in update_data and update_data["status"]:
        update_data["status"] = ReportStatus(update_data["status"])
    
    # Mettre à jour les attributs
    for field, value in update_data.items():
        if hasattr(db_report, field) and value is not None:
            setattr(db_report, field, value)
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return db_report


def delete_report(db: Session, report_id: int) -> Optional[Report]:
    """
    Supprime un rapport
    
    Args:
        db: Session de base de données
        report_id: ID du rapport à supprimer
        
    Returns:
        Rapport supprimé ou None si non trouvé
    """
    db_report = get_report(db, report_id)
    if not db_report:
        return None
    
    db.delete(db_report)
    db.commit()
    
    return db_report


def approve_report(
    db: Session,
    report_id: int,
    approver_id: int
) -> Optional[Report]:
    """
    Approuve un rapport
    
    Args:
        db: Session de base de données
        report_id: ID du rapport à approuver
        approver_id: ID de l'utilisateur qui approuve le rapport
        
    Returns:
        Rapport approuvé ou None si non trouvé
    """
    db_report = get_report(db, report_id)
    if not db_report:
        return None
    
    db_report.status = ReportStatus.APPROVED
    db_report.approved_by_id = approver_id
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return db_report


def reject_report(
    db: Session,
    report_id: int,
    approver_id: int,
    rejection_reason: str
) -> Optional[Report]:
    """
    Rejette un rapport
    
    Args:
        db: Session de base de données
        report_id: ID du rapport à rejeter
        approver_id: ID de l'utilisateur qui rejette le rapport
        rejection_reason: Raison du rejet
        
    Returns:
        Rapport rejeté ou None si non trouvé
    """
    db_report = get_report(db, report_id)
    if not db_report:
        return None
    
    db_report.status = ReportStatus.REJECTED
    db_report.approved_by_id = approver_id
    
    # En production, on pourrait stocker la raison du rejet dans une table séparée
    # ou dans un champ dédié
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return db_report


def add_tag_to_report(
    db: Session,
    report_id: int,
    tag_id: int
) -> Optional[Report]:
    """
    Ajoute un tag à un rapport
    
    Args:
        db: Session de base de données
        report_id: ID du rapport
        tag_id: ID du tag
        
    Returns:
        Rapport mis à jour ou None si le rapport ou le tag n'existent pas
    """
    db_report = get_report(db, report_id)
    if not db_report:
        return None
    
    db_tag = db.get(Tag, tag_id)
    if not db_tag:
        return None
    
    # Vérifier si le tag est déjà associé au rapport
    if db_tag not in db_report.tags:
        db_report.tags.append(db_tag)
        db.commit()
        db.refresh(db_report)
    
    return db_report


def remove_tag_from_report(
    db: Session,
    report_id: int,
    tag_id: int
) -> Optional[Report]:
    """
    Supprime un tag d'un rapport
    
    Args:
        db: Session de base de données
        report_id: ID du rapport
        tag_id: ID du tag
        
    Returns:
        Rapport mis à jour ou None si le rapport ou le tag n'existent pas
    """
    db_report = get_report(db, report_id)
    if not db_report:
        return None
    
    db_tag = db.get(Tag, tag_id)
    if not db_tag:
        return None
    
    # Vérifier si le tag est associé au rapport
    if db_tag in db_report.tags:
        db_report.tags.remove(db_tag)
        db.commit()
        db.refresh(db_report)
    
    return db_report


def get_reports_for_summary(
    db: Session,
    start_date: datetime,
    tags: Optional[List[str]] = None,
    classification: Optional[str] = None,
    location: Optional[str] = None,
    clearance_level: Optional[str] = None
) -> List[Report]:
    """
    Récupère les rapports pour générer un résumé
    
    Args:
        db: Session de base de données
        start_date: Date de début
        tags: Filtrer par tags
        classification: Filtrer par classification
        location: Filtrer par location
        clearance_level: Niveau d'habilitation de l'utilisateur
        
    Returns:
        Liste de rapports
    """
    # Déterminer les classifications autorisées en fonction du niveau d'habilitation
    allowed_classifications = None
    if clearance_level:
        if clearance_level == "top_secret":
            allowed_classifications = ["top_secret", "secret", "confidential", "unclassified"]
        elif clearance_level == "secret":
            allowed_classifications = ["secret", "confidential", "unclassified"]
        elif clearance_level == "confidential":
            allowed_classifications = ["confidential", "unclassified"]
    
    # Récupérer les rapports
    reports = get_reports(
        db=db,
        skip=0,
        limit=100,
        status="approved",
        classification=classification,
        from_date=start_date,
        tags=tags,
        allowed_classifications=allowed_classifications
    )
    
    # Filtrer par location si nécessaire
    if location and reports:
        reports = [r for r in reports if r.location and location.lower() in r.location.lower()]
    
    return reports