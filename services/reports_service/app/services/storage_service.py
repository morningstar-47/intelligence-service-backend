import os
import shutil
import logging
import aiofiles
from typing import Tuple, Optional
from fastapi import UploadFile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("reports_service.storage")


async def save_upload_file(upload_file: UploadFile, report_id: int) -> Tuple[str, int]:
    """
    Sauvegarde un fichier téléchargé
    
    Args:
        upload_file: Fichier téléchargé
        report_id: ID du rapport
        
    Returns:
        Tuple contenant le chemin du fichier sauvegardé et sa taille
    """
    # Créer le répertoire pour les rapports s'il n'existe pas
    report_dir = os.path.join(settings.UPLOADS_PATH, f"report_{report_id}")
    os.makedirs(report_dir, exist_ok=True)
    
    # Nettoyer le nom du fichier
    filename = Path(upload_file.filename).name
    safe_filename = _sanitize_filename(filename)
    
    # Générer le chemin complet du fichier
    file_path = os.path.join(report_dir, safe_filename)
    
    # Écrire le fichier
    size = 0
    try:
        # Copierdata = await upload_file.read()
        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await upload_file.read(1024):
                await out_file.write(content)
                size += len(content)
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du fichier {file_path}: {e}")
        raise

    return file_path, size
def _sanitize_filename(filename: str) -> str:
    """
    Nettoie le nom d'un fichier pour éviter les problèmes de sécurité

    Args:
        filename: Nom du fichier
    Returns:
        Nom du fichier nettoyé
    """
    return "".join(c for c in filename if c.isalnum() or c in (" ", ".", "_"))  