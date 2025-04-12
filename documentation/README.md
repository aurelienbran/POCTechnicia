# POC Technicia - Plateforme OCR et RAG avancée

## Description

Solution complète de traitement intelligent de documents combinant OCR (Reconnaissance Optique de Caractères) avancé et RAG (Retrieval Augmented Generation). Cette plateforme permet l'analyse, l'extraction et la recherche sémantique dans les documents PDF ainsi qu'un tableau de bord OCR en cours de développement pour la gestion et le suivi des tâches.

## Fonctionnalités principales

### Module RAG (Retrieval Augmented Generation)
- Traitement de documents techniques (PDF, texte)
- Extraction intelligente de texte avec support OCR pour documents scannés
- Chunking adaptatif selon la structure du document
- Recherche sémantique avancée dans la base de connaissances
- Génération de réponses contextuelles avec Claude 3 Sonnet
- Interface utilisateur interactive et intuitive

### Système OCR Hybride et Tableau de Bord (En développement)
- Sélection automatique du meilleur moteur OCR selon le type de document &#10004;
- Support pour différents fournisseurs OCR (OCRmyPDF, Tesseract direct, Document AI) &#10004;
- Métriques de qualité pour évaluation des résultats OCR &#10004; 
- Tableau de bord de surveillance et gestion des tâches OCR (en cours de développement &#10226;)
- Interface d'exportation des données et génération de rapports (en cours de développement &#10226;)
- Système WebSocket pour mises à jour en temps réel (en cours de développement &#10226;)

> **Note :** Les fonctionnalités marquées &#10004; sont entièrement implémentées. Celles marquées &#10226; sont en cours de développement. Pour plus de détails sur l'état actuel du développement, consultez [SUIVI_IMPLEMENTATION.md](./MVP/SUIVI_IMPLEMENTATION.md).

## Architecture technique

L'application est construite selon une architecture moderne et modulaire :

- **Backend** : FastAPI (Python 3.11+)
- **Frontend RAG** : React + TypeScript + Tailwind CSS
- **Frontend Dashboard** : HTML/CSS/JS avec WebSockets
- **Base de données vectorielle** : Qdrant
- **Base de données relationnelle** : PostgreSQL
- **Traitement asynchrone** : Celery avec RabbitMQ
- **API LLM** : Claude 3 Sonnet (Anthropic)
- **API Embeddings** : VoyageAI (v0.3.2)

## Prérequis

- Python 3.11+
- Environnement virtuel Python (.venv)
- Node.js et npm (pour le frontend React)
- Qdrant (version binaire)
- PostgreSQL
- Pour la fonctionnalité OCR :
  - Tesseract OCR
  - Poppler
  - Ghostscript
  - OCRmyPDF (installé via pip)

## Installation

1. Cloner le dépôt :
```bash
git clone <repository_url>
cd POC-TECHNICIA
```

2. Créer et activer l'environnement virtuel :
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate 
# Linux/Mac
source .venv/bin/activate 
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Installer les dépendances OCR (optionnel) :
Voir [INSTALLATION_OCR.md](./INSTALLATION_OCR.md) pour les instructions détaillées.

5. Configurer la base de données PostgreSQL :
```bash
python scripts/setup_database.py
```

6. Copier le fichier `.env.example` vers `.env` et configurer les variables.

7. Démarrer tous les composants :
```bash
# Windows
cd scripts/startup
start-all-components.bat

# Linux/Mac
cd scripts/startup
./start-all-components.sh
```

## Documentation détaillée

Consultez les documents suivants pour plus d'informations :

- [Guide de mise en route](./GUIDE_MISE_EN_ROUTE.md) - Guide complet de démarrage
- [Documentation du Dashboard OCR](./OCR_DASHBOARD_COMPLET.md) - Fonctionnalités et utilisation du tableau de bord OCR
- [Installation OCR](./INSTALLATION_OCR.md) - Guide d'installation des dépendances OCR
- [Diagnostics](./DIAGNOSTICS.md) - Outils et procédures de dépannage

## Roadmap d'évolution

La plateforme continue d'évoluer selon les phases suivantes :

1. **Phase actuelle (Avril 2025)** :
   - Fonctionnalités complètes du tableau de bord OCR
   - Intégration des WebSockets pour les mises à jour en temps réel
   - API complète pour les données et l'exportation

2. **Prochaine phase (Mai 2025)** :
   - Amélioration des outils de diagnostic
   - Support de formats de documents additionnels
   - Interface mobile responsive

Pour un suivi détaillé de l'implémentation, voir [SUIVI_IMPLEMENTATION.md](./MVP/SUIVI_IMPLEMENTATION.md).

## Équipe et contributions

Développé par l'équipe de développement Technicia, ce projet est maintenu activement et amélioré régulièrement. Pour contribuer, veuillez consulter le document [CONTRIBUTING.md](./CONTRIBUTING.md).

## Licence

Copyright 2025 Technicia Corp. Tous droits réservés.
