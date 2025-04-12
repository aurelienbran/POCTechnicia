"""
Module d'utilitaires de formatage.

Ce module fournit des fonctions utilitaires pour formater différents types de données
(dates, durées, tailles de fichiers, etc.) de manière cohérente dans l'application.

Auteur: Équipe de Développement Technicia
Date: 1 avril, 2025
"""

from datetime import datetime
from typing import Union, Optional


def format_datetime(dt: Union[datetime, str, None]) -> str:
    """
    Formate un objet datetime ou une chaîne ISO en format lisible.
    
    Args:
        dt: Datetime ou chaîne ISO à formater
        
    Returns:
        Chaîne formatée ou chaîne vide si None
    """
    if not dt:
        return ""
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y %H:%M")
    
    return str(dt)


def format_duration(seconds: Union[float, int, None]) -> str:
    """
    Formate une durée en secondes en chaîne lisible.
    
    Args:
        seconds: Durée en secondes
        
    Returns:
        Durée formatée (ex: "1h 30m", "45s")
    """
    if seconds is None:
        return ""
    
    seconds = float(seconds)
    
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {int(seconds)}s"
    
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m"


def format_file_size(size_bytes: Union[int, float, None]) -> str:
    """
    Formate une taille de fichier en bytes en format lisible.
    
    Args:
        size_bytes: Taille en bytes
        
    Returns:
        Taille formatée (ex: "1.5 MB", "45 KB")
    """
    if size_bytes is None:
        return ""
    
    size_bytes = float(size_bytes)
    
    # Définition des unités
    units = ["B", "KB", "MB", "GB", "TB"]
    size = size_bytes
    unit_index = 0
    
    # Conversion aux unités appropriées
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    # Formatage avec le nombre approprié de décimales
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def format_percentage(value: Union[float, int, None], decimal_places: int = 1) -> str:
    """
    Formate une valeur en pourcentage.
    
    Args:
        value: Valeur à formater (0-100 ou 0-1)
        decimal_places: Nombre de décimales à afficher
        
    Returns:
        Pourcentage formaté (ex: "75.5%")
    """
    if value is None:
        return ""
    
    # Normalisation à l'échelle 0-100
    if 0 <= value <= 1:
        value *= 100
    
    return f"{value:.{decimal_places}f}%"


def format_confidence_level(confidence: Union[float, int, None]) -> str:
    """
    Formate un niveau de confiance OCR avec une indication textuelle.
    
    Args:
        confidence: Valeur de confiance (0-100 ou 0-1)
        
    Returns:
        Niveau de confiance formaté avec indication
    """
    if confidence is None:
        return ""
    
    # Normalisation à l'échelle 0-100
    if 0 <= confidence <= 1:
        confidence *= 100
    
    # Détermination du niveau
    if confidence >= 95:
        level = "Excellent"
        color_class = "text-success"
    elif confidence >= 85:
        level = "Très bon"
        color_class = "text-success"
    elif confidence >= 75:
        level = "Bon"
        color_class = "text-primary"
    elif confidence >= 60:
        level = "Moyen"
        color_class = "text-warning"
    else:
        level = "Faible"
        color_class = "text-danger"
    
    # Formatage avec pourcentage et niveau
    return f"{confidence:.1f}% <span class='{color_class}'>({level})</span>"
