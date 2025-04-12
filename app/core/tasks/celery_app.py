"""
Configuration de l'application Celery pour les tâches asynchrones.
"""

import os
from celery import Celery
from app.config import settings

# Configuration de base de Celery
celery_app = Celery(
    'technicia',
    broker=settings.CELERY_BROKER_URL or 'redis://localhost:6379/0',
    backend=settings.CELERY_RESULT_BACKEND or 'redis://localhost:6379/0',
    include=['app.core.tasks.embedding_tasks']
)

# Configuration générale
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Paris',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 heure max par tâche (pour éviter les tâches zombies)
    worker_max_tasks_per_child=200,  # Redémarrer les workers après 200 tâches (éviter les fuites mémoire)
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
)

# Configuration spécifique pour les tâches d'embedding
celery_app.conf.task_routes = {
    'app.core.tasks.embedding_tasks.*': {'queue': 'embeddings'},
}

# Configuration des tâches périodiques
celery_app.conf.beat_schedule = {
    'cleanup-temp-files': {
        'task': 'app.core.tasks.maintenance_tasks.cleanup_temp_files',
        'schedule': 3600.0,  # Toutes les heures
    },
}

# Configuration du logging
celery_app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
celery_app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s] %(message)s'

if __name__ == '__main__':
    celery_app.start()
