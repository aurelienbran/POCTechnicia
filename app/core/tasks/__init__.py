"""
Package pour les tâches asynchrones Celery.
"""

from .celery_app import celery_app
from .embedding_tasks import process_document_embeddings

__all__ = [
    'celery_app',
    'process_document_embeddings',
]
