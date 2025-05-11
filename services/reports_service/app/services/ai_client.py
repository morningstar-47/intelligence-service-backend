import logging
import httpx
from typing import Dict, Any, Optional

from app.core.config import settings
from app.models.report import Report

logger = logging.getLogger("reports_service.ai_client")


async def analyze_report(report: Report) -> Optional[Dict[str, Any]]:
    """
    Envoie un rapport au service d'IA pour analyse
    
    Args:
        report: Rapport à analyser
        
    Returns:
        Résultats de l'analyse ou None en cas d'erreur
    """
    # Si le service d'IA n'est pas configuré, simuler une analyse basique
    if not settings.AI_SERVICE_URL:
        return _simulate_analysis(report)
    
    try:
        # Préparer les données pour l'analyse
        data = {
            "report_id": report.id,
            "title": report.title,
            "content": report.content,
            "source": report.source,
            "classification": report.classification,
            "location": report.location,
            "coordinates": report.coordinates
        }
        
        # Envoyer la requête au service d'IA
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AI_SERVICE_URL}{settings.AI_ANALYSIS_ENDPOINT}",
                json=data,
                timeout=30.0  # Timeout plus long pour l'analyse IA
            )
            
            if response.status_code != 200:
                logger.error(f"Erreur lors de l'analyse du rapport {report.id}: {response.text}")
                return _simulate_analysis(report)
            
            return response.json()
            
    except Exception as e:
        logger.error(f"Erreur lors de la communication avec le service d'IA: {str(e)}")
        return _simulate_analysis(report)


def _simulate_analysis(report: Report) -> Dict[str, Any]:
    """
    Simule une analyse IA basique lorsque le service d'IA n'est pas disponible
    
    Args:
        report: Rapport à analyser
        
    Returns:
        Analyse simulée
    """
    # Analyse de base des données d'entrée
    content = report.content.lower()
    
    # Simulation d'analyse de menace basique
    keywords = {
        "critical": ["explosion", "attaque", "sabotage", "infiltration", "attentat"],
        "high": ["mouvement", "troupes", "suspect", "surveillance", "intrusion"],
        "medium": ["activité", "inhabituel", "déplacement", "communication", "crypté"],
        "low": ["observation", "patrouille", "routine", "reconnaissance"]
    }
    
    # Déterminer le niveau de menace
    threat_level = "negligible"
    threat_factors = []
    
    for level, words in keywords.items():
        found_words = [word for word in words if word in content]
        if found_words:
            threat_level = level
            threat_factors.extend(found_words)
            break
    
    # Calculer un score de crédibilité (0-100)
    credibility_score = min(len(content.split()) / 5, 100)
    
    # Suggérer des tags
    keywords_to_tags = {
        "communication": "communications",
        "cyber": "cyber",
        "réseau": "réseau",
        "frontière": "terrestre",
        "véhicule": "terrestre",
        "armement": "stratégique",
        "maritime": "maritime",
        "aérien": "aérien",
        "terrorisme": "terrorisme",
        "civil": "social",
        "économie": "économique"
    }
    
    suggested_tags = []
    
    for keyword, tag in keywords_to_tags.items():
        if keyword in content:
            suggested_tags.append(tag)
    
    # Extraction d'entités (simulation)
    entities = {
        "locations": [report.location] if report.location else [],
        "persons": [],
        "organizations": [],
        "dates": []
    }
    
    # Résultats
    return {
        "summary": f"Analyse automatique du rapport '{report.title}'.",
        "threat_level": threat_level,
        "credibility_score": int(credibility_score),
        "suggested_tags": suggested_tags,
        "entities": entities,
        "related_reports": []
    }