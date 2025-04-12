# Guide Administrateur - Système OCR Technicia

**Version :** 1.0  
**Date :** 2 avril 2025  
**Public cible :** Administrateurs système et DevOps responsables du déploiement et de la maintenance

## Table des matières

1. [Introduction](#1-introduction)
2. [Architecture du système](#2-architecture-du-système)
3. [Prérequis techniques](#3-prérequis-techniques)
4. [Installation et déploiement](#4-installation-et-déploiement)
5. [Configuration](#5-configuration)
6. [Monitoring et maintenance](#6-monitoring-et-maintenance)
7. [Sécurité](#7-sécurité)
8. [Sauvegarde et reprise](#8-sauvegarde-et-reprise)
9. [Résolution des problèmes](#9-résolution-des-problèmes)
10. [Références](#10-références)

## 1. Introduction

Ce guide est destiné aux administrateurs système et personnel DevOps responsables du déploiement, de la configuration et de la maintenance du système OCR Technicia. Il fournit des instructions détaillées sur l'installation, la configuration, le monitoring et la résolution de problèmes.

## 2. Architecture du système

### 2.1 Vue d'ensemble des composants

Le système OCR Technicia est composé des éléments suivants :

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Interface Web   │────▶│ API Backend     │────▶│ File Queue      │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Base de données │◀───▶│ Workers OCR     │◀────│ Orchestrateur   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │ Services cloud  │◀───▶│ Processeurs     │
                        │ (Vision AI,     │     │ spécialisés     │
                        │  Document AI)   │     └─────────────────┘
                        └─────────────────┘
```

### 2.2 Description des composants

- **Interface Web** : Application frontend pour les utilisateurs finaux, développée en React
- **API Backend** : API REST développée en Flask, gère les requêtes de l'interface utilisateur
- **File Queue** : Système de file d'attente basé sur Celery et Redis
- **Orchestrateur** : Coordonne les différents processeurs OCR selon le type de document
- **Workers OCR** : Services de traitement qui exécutent les tâches OCR
- **Processeurs spécialisés** : Modules dédiés à l'extraction de contenu technique (formules, schémas)
- **Services cloud** : Intégration avec Google Cloud Vision AI et Document AI
- **Base de données** : PostgreSQL pour le stockage des métadonnées et des résultats de traitement

## 3. Prérequis techniques

### 3.1 Matériel recommandé

#### Configuration minimale (jusqu'à 100 documents/jour)
- CPU : 4 cœurs, 2.5 GHz ou supérieur
- RAM : 16 Go
- Stockage : 100 Go SSD
- Bande passante réseau : 100 Mbps

#### Configuration recommandée (jusqu'à 1000 documents/jour)
- CPU : 8 cœurs, 3.0 GHz ou supérieur
- RAM : 32 Go
- Stockage : 500 Go SSD
- Bande passante réseau : 1 Gbps

### 3.2 Logiciels requis

- **Système d'exploitation** : Ubuntu 22.04 LTS ou CentOS 8.x
- **Docker** : version 24.0 ou supérieure
- **Docker Compose** : version 2.20 ou supérieure
- **Python** : version 3.10 ou supérieure
- **PostgreSQL** : version 14 ou supérieure
- **Redis** : version 7.0 ou supérieure
- **Nginx** : version 1.20 ou supérieure (pour le serveur de production)

### 3.3 Comptes et licences

- Compte Google Cloud Platform avec API Vision AI et Document AI activées
- Clés d'API pour les services tiers
- Licences pour les composants propriétaires (le cas échéant)

## 4. Installation et déploiement

### 4.1 Installation avec Docker (recommandée)

1. Clonez le dépôt Git :
   ```bash
   git clone https://github.com/technicia/ocr-system.git
   cd ocr-system
   ```

2. Configurez les variables d'environnement :
   ```bash
   cp .env.example .env
   # Éditez le fichier .env avec vos paramètres
   ```

3. Construisez et lancez les conteneurs :
   ```bash
   docker-compose up -d
   ```

4. Vérifiez l'état des services :
   ```bash
   docker-compose ps
   ```

### 4.2 Installation manuelle

Suivez cette procédure si vous ne pouvez pas utiliser Docker :

1. Installez les dépendances système :
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install -y python3-pip python3-venv postgresql redis-server nginx tesseract-ocr
   
   # CentOS/RHEL
   sudo dnf update
   sudo dnf install -y python3-pip postgresql-server redis nginx tesseract
   ```

2. Configurez la base de données PostgreSQL :
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   sudo -u postgres createuser -P technicia
   sudo -u postgres createdb -O technicia ocr_db
   ```

3. Configurez l'environnement Python :
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Initialisez l'application :
   ```bash
   python manage.py init_db
   python manage.py create_admin
   ```

5. Configurez et démarrez les services :
   ```bash
   # Configurez Celery, Redis, etc.
   # (voir les instructions détaillées dans docs/INSTALLATION_MANUELLE.md)
   ```

### 4.3 Déploiement en production

Pour un environnement de production, suivez ces étapes supplémentaires :

1. Configurez Nginx comme proxy inverse :
   ```bash
   # Exemple de configuration dans /etc/nginx/sites-available/technicia
   server {
       listen 80;
       server_name your-domain.com;
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

2. Configurez SSL/TLS avec Let's Encrypt :
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

3. Activez la configuration et redémarrez Nginx :
   ```bash
   sudo ln -s /etc/nginx/sites-available/technicia /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

## 5. Configuration

### 5.1 Fichier de configuration principal

Le fichier `.env` contient les principales variables de configuration. Voici les paramètres essentiels à définir :

```
# Configuration de base
APP_NAME=Technicia OCR
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=your-secure-secret-key

# Base de données
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ocr_db
DB_USER=technicia
DB_PASSWORD=your-secure-password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
VISION_AI_ENABLED=True
DOCUMENT_AI_ENABLED=True
DOCUMENT_AI_PROCESSOR_ID=your-processor-id

# OCR
DEFAULT_OCR_ENGINE=hybrid
MAX_PARALLEL_TASKS=4
OCR_QUALITY_THRESHOLD=0.75
```

### 5.2 Configuration des processeurs OCR

Vous pouvez configurer le comportement des différents processeurs OCR dans le fichier `config/processors.json` :

```json
{
  "tesseract": {
    "enabled": true,
    "language": "fra+eng",
    "oem": 3,
    "psm": 6
  },
  "ocrmypdf": {
    "enabled": true,
    "options": {
      "deskew": true,
      "clean": true,
      "optimize": 2
    }
  },
  "document_ai": {
    "enabled": true,
    "fallback_to_local": true,
    "confidence_threshold": 0.7
  }
}
```

### 5.3 Configuration du système de file d'attente

Modifiez le fichier `config/celery.py` pour ajuster les paramètres de la file d'attente :

```python
# Paramètres Celery
broker_url = f'redis://{os.getenv("REDIS_HOST")}:{os.getenv("REDIS_PORT")}/0'
result_backend = f'redis://{os.getenv("REDIS_HOST")}:{os.getenv("REDIS_PORT")}/0'
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Paris'
worker_prefetch_multiplier = 1
task_acks_late = True
```

## 6. Monitoring et maintenance

### 6.1 Monitoring du système

#### Outils de monitoring intégrés

Le système OCR Technicia dispose d'un tableau de bord de monitoring accessible à l'adresse `/admin/monitoring` :

- État des workers
- Utilisation des ressources (CPU, mémoire, disque)
- File d'attente des documents
- Taux de succès/échec des traitements
- Temps de traitement moyen

#### Intégration avec des systèmes externes

Le système expose des métriques Prometheus à l'endpoint `/metrics`, permettant l'intégration avec :

- Prometheus
- Grafana
- Datadog
- New Relic

Configuration recommandée pour Prometheus :
```yaml
scrape_configs:
  - job_name: 'technicia-ocr'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:5000']
```

### 6.2 Logs du système

Les logs sont générés dans le répertoire `/var/log/technicia/` et comprennent :

- `api.log` : Logs de l'API
- `worker.log` : Logs des workers OCR
- `scheduler.log` : Logs du planificateur
- `error.log` : Logs d'erreurs uniquement

Configuration de rotation des logs dans `/etc/logrotate.d/technicia` :
```
/var/log/technicia/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 technicia technicia
    sharedscripts
    postrotate
        systemctl reload technicia-service
    endscript
}
```

### 6.3 Maintenance régulière

#### Tâches quotidiennes
- Vérification des logs d'erreurs
- Surveillance de l'espace disque
- Vérification de l'état des workers

#### Tâches hebdomadaires
- Sauvegarde de la base de données
- Nettoyage des fichiers temporaires
- Vérification des mises à jour

#### Tâches mensuelles
- Analyse des performances et optimisation
- Revue des statistiques d'utilisation
- Mise à jour des modèles OCR si nécessaire

## 7. Sécurité

### 7.1 Authentification et autorisation

Le système utilise un modèle d'authentification basé sur JWT (JSON Web Tokens) avec les fonctionnalités suivantes :

- Authentification multi-facteurs (optionnelle)
- Intégration LDAP/Active Directory (optionnelle)
- Gestion fine des autorisations basée sur les rôles
- Historique des connexions et activités

### 7.2 Sécurisation des communications

- Toutes les communications doivent être chiffrées via HTTPS
- Configuration recommandée de TLS dans Nginx :
  ```
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_prefer_server_ciphers on;
  ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
  ssl_session_timeout 1d;
  ssl_session_cache shared:SSL:50m;
  ssl_stapling on;
  ssl_stapling_verify on;
  ```

### 7.3 Protection des données

- Chiffrement des données sensibles en base de données
- Suppression automatique des fichiers temporaires
- Anonymisation des données de test
- Conformité RGPD avec export et suppression des données sur demande

## 8. Sauvegarde et reprise

### 8.1 Stratégie de sauvegarde

#### Éléments à sauvegarder
- Base de données PostgreSQL
- Configuration du système
- Documents traités (si nécessaire)
- Logs (pour audit)

#### Planification des sauvegardes
- Sauvegarde complète : hebdomadaire
- Sauvegarde incrémentielle : quotidienne
- Sauvegarde des logs : quotidienne

#### Script de sauvegarde automatique
```bash
#!/bin/bash
# Sauvegarde de la base de données
BACKUP_DATE=$(date +"%Y%m%d")
BACKUP_DIR="/var/backups/technicia"

# Base de données
pg_dump -U technicia ocr_db | gzip > "$BACKUP_DIR/db_$BACKUP_DATE.sql.gz"

# Configuration
tar -czf "$BACKUP_DIR/config_$BACKUP_DATE.tar.gz" /etc/technicia /app/config

# Rotation des sauvegardes (conserver 30 jours)
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete
```

### 8.2 Procédure de reprise après incident

#### Reprise de la base de données
```bash
# Restauration de la base de données
gunzip -c /var/backups/technicia/db_20250401.sql.gz | psql -U technicia ocr_db
```

#### Restauration de la configuration
```bash
# Restauration des fichiers de configuration
tar -xzf /var/backups/technicia/config_20250401.tar.gz -C /
```

#### Reprise complète du système
Consultez le document détaillé `docs/DISASTER_RECOVERY.md` pour les procédures complètes de reprise après différents types d'incidents.

## 9. Résolution des problèmes

### 9.1 Problèmes courants et solutions

#### Problème : Les workers ne traitent pas les documents
- Vérifiez l'état des services Celery : `systemctl status technicia-celery`
- Vérifiez la connexion à Redis : `redis-cli ping`
- Vérifiez les logs pour les erreurs : `tail -f /var/log/technicia/worker.log`

#### Problème : Erreurs de connexion à la base de données
- Vérifiez l'état de PostgreSQL : `systemctl status postgresql`
- Vérifiez les logs PostgreSQL : `tail -f /var/log/postgresql/postgresql-14-main.log`
- Testez la connexion manuellement : `psql -U technicia -h localhost ocr_db`

#### Problème : API Google Cloud inaccessible
- Vérifiez les identifiants : `echo $GOOGLE_APPLICATION_CREDENTIALS`
- Vérifiez la validité des clés : `gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS`
- Vérifiez le statut des services Google Cloud : https://status.cloud.google.com/

### 9.2 Outils de diagnostic

Le système dispose d'outils de diagnostic accessibles via l'interface d'administration ou en ligne de commande :

```bash
# Vérification complète du système
python manage.py system_check

# Test de la connexion aux services externes
python manage.py test_services

# Simulation de traitement OCR
python manage.py test_ocr --file=/path/to/test.pdf
```

### 9.3 Support et escalade

Consultez notre portail de support pour l'escalade des problèmes :
- Portail : https://support.technicia.com
- Email : support@technicia.com
- Téléphone (urgence) : +33 1 23 45 67 89

## 10. Références

### 10.1 Documentation complémentaire
- [Architecture détaillée](../architecture/ARCHITECTURE_GLOBALE.md)
- [Spécifications API](../api/API_DOCUMENT_PROCESSING.md)
- [Guide de déploiement Docker](../INSTALLATION_OCR.md)
- [Guide de troubleshooting](../TROUBLESHOOTING/Enhanced_Reply.md)

### 10.2 Ressources externes
- [Documentation Docker](https://docs.docker.com/)
- [Documentation Celery](https://docs.celeryproject.org/)
- [Documentation Google Cloud Vision AI](https://cloud.google.com/vision)
- [Documentation Tesseract OCR](https://tesseract-ocr.github.io/)

### 10.3 Glossaire
- **OCR** : Optical Character Recognition (Reconnaissance Optique de Caractères)
- **API** : Application Programming Interface
- **JWT** : JSON Web Token
- **RAG** : Retrieval Augmented Generation
- **Worker** : Processus de traitement des tâches asynchrones
