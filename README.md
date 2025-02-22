# POC RAG - Assistant Documentation Technique

## Description
POC de Retrieval Augmented Generation (RAG) pour le traitement de documents techniques PDF volumineux. Le système utilise Claude 3 Sonnet pour la génération de réponses et VoyageAI pour les embeddings, avec une interface utilisateur moderne et intuitive.

## Fonctionnalités
- Upload et traitement de PDF jusqu'à 150 Mo
- Traitement asynchrone des documents avec suivi de progression
- Extraction et indexation intelligente du contenu avec PyMuPDF
- Recherche sémantique optimisée via Qdrant
- Génération de réponses contextuelles avec Claude 3 Sonnet
- Interface utilisateur moderne et réactive avec :
  - Sidebar compacte pour l'upload
  - Modal de progression interactif
  - Chat avec historique scrollable
  - Affichage des sources avec scores
  - Design responsive avec Tailwind CSS
  - Gestion des erreurs côté client

## Prérequis
- Python 3.11+
- Environnement virtuel Python (venv)
- Qdrant (version binaire)
- Clés API :
  - VoyageAI pour les embeddings (v0.3.2)
  - Claude 3 Sonnet (Anthropic v0.18.0)

## Installation

1. Cloner le dépôt :
```bash
git clone <repository_url>
cd POC-TECHNICIA
```

2. Créer et activer l'environnement virtuel :
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Copier le fichier `.env.example` vers `.env` et configurer les variables :
```bash
cp .env.example .env
```

Variables importantes :
```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-...  # Clé API Claude 3 Sonnet
VOYAGE_API_KEY=pa-...         # Clé API VoyageAI

# Configuration
MAX_UPLOAD_SIZE=157286400     # Taille maximale des fichiers (150 Mo)
QDRANT_HOST=localhost         # Hôte Qdrant
QDRANT_PORT=6333             # Port Qdrant
QDRANT_PATH=./qdrant_storage # Stockage local Qdrant
COLLECTION_NAME=documents     # Nom de la collection
```

## Architecture

Le projet utilise :
- FastAPI pour l'API REST
- PyMuPDF pour le traitement des PDFs
- VoyageAI pour les embeddings
- Qdrant (mode local) pour le stockage vectoriel
- Claude 3 Sonnet pour la génération de réponses
- Tailwind CSS pour l'interface utilisateur

### Stockage Vectoriel

Nous utilisons Qdrant en mode local (fichier) plutôt qu'en mode serveur pour :
- Simplifier le déploiement
- Éviter les dépendances externes
- Faciliter les tests et le développement
- Permettre une portabilité maximale

Les vecteurs et métadonnées sont stockés dans le dossier `qdrant_storage/`.

## Structure du Projet

```
POC-TECHNICIA/
├── app/
│   ├── api/            # Endpoints FastAPI
│   ├── core/           # Logique métier
│   │   ├── pdf_processor.py    # Traitement PDF
│   │   ├── vector_store.py     # Interface Qdrant
│   │   ├── llm_interface.py    # Interface Claude
│   │   └── rag_engine.py       # Orchestration RAG
│   ├── static/         # Assets frontend
│   │   ├── css/
│   │   └── js/
│   ├── templates/      # Templates HTML
│   └── config.py       # Configuration
├── tests/              # Tests
│   ├── unit/
│   └── performance/
├── qdrant_storage/     # Stockage vectoriel local
├── uploads/            # Fichiers PDF temporaires
├── logs/              # Logs applicatifs
└── storage/           # Autres données persistantes
```

## Utilisation

1. Démarrer Qdrant :
```bash
./qdrant.exe  # Le binaire doit être téléchargé depuis le site officiel
```

2. Démarrer l'API :
```bash
python -m uvicorn app.main:app --reload
```

3. Accéder à l'interface :
```
http://localhost:8000
```

4. Documentation API (Swagger) :
```
http://localhost:8000/docs
```

## Problèmes Connus

1. **Erreur 503 au Démarrage**
   - Normal pendant l'initialisation du système
   - Attendre quelques secondes
   - Vérifier les logs dans `logs/app.log`

2. **Problèmes d'Upload**
   - Vérifier que le fichier est un PDF
   - Taille maximale : 150 MB
   - Rafraîchir si le système vient de démarrer

## Limitations Actuelles

- Taille maximale des fichiers : 150 MB
- Format supporté : PDF uniquement
- Base de données vectorielle locale (pas de clustering)
- Traitement séquentiel des documents

## État Actuel du Projet

### Composants Principaux
- ✅ Upload et traitement de PDF avec PyMuPDF
- ✅ Extraction de texte et chunking optimisé
- ✅ Génération d'embeddings avec VoyageAI
- ✅ Stockage vectoriel optimisé avec Qdrant
- ✅ Interface LLM avec Claude
- 🔄 Interface utilisateur (en développement)

### Optimisations Réalisées
1. **Migration vers PyMuPDF** :
   - Meilleure performance pour les gros PDFs
   - Extraction de texte plus précise
   - Gestion optimisée de la mémoire

2. **Configuration Qdrant Optimisée** :
   - Collection configurée pour RAG
   - Stockage sur disque pour les gros volumes
   - Paramètres optimisés pour la recherche sémantique
   - Gestion mémoire contrôlée (max 1GB)

## Tests

Exécuter les tests :
```bash
pytest
```

Tests avec couverture :
```bash
pytest --cov=app tests/
```

Tests de performance :
```bash
python tests/performance/test_performance.py
```

## Logs

Les logs sont stockés dans :
- `logs/app.log` : Logs principaux
- `logs/uvicorn.log` : Logs du serveur

## Documentation Complémentaire

- [PROJECT.md](PROJECT.md) : État détaillé du projet
- [PIPELINE.md](PIPELINE.md) : Description des pipelines de traitement
- [NEXT.md](NEXT.md) : Prochaines étapes et instructions

## Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## Licence

Distribué sous la licence MIT. Voir `LICENSE` pour plus d'informations.

## Qdrant

Ce projet utilise Qdrant comme base de données vectorielle pour le stockage et la recherche de documents.

### Prérequis

- Python 3.8+
- Qdrant

### Installation

1. Clonez le repository :
```bash
git clone https://github.com/aurelienbran/POCTechnicia.git
cd POCTechnicia
```

2. Installez les dépendances Python :
```bash
pip install -r requirements.txt
```

3. Téléchargez Qdrant :
   - Rendez-vous sur [la page de releases de Qdrant](https://github.com/qdrant/qdrant/releases)
   - Téléchargez la dernière version de `qdrant-windows-x86_64.exe`
   - Renommez le fichier en `qdrant.exe`
   - Placez-le dans le dossier `qdrant/` de votre projet

### Structure du projet

- `app/` : Contient le code principal de l'application
- `tests/` : Tests unitaires et de performance
- `qdrant/` : Configuration et données Qdrant
- `scripts/` : Scripts utilitaires

### Utilisation

1. Démarrez Qdrant :
```bash
./scripts/start_qdrant.ps1
```

2. Initialisez la base de données (première utilisation uniquement) :
```bash
python scripts/initialize_qdrant.py
```

3. Pour plus d'informations sur l'utilisation de l'API et les fonctionnalités disponibles, consultez la documentation dans le dossier `docs/`.
