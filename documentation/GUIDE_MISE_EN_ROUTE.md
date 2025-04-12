# Guide de mise en route du système Technicia

Ce guide détaille les étapes pour installer, configurer et utiliser le système Technicia, un chatbot conçu pour fournir un support technique aux techniciens de maintenance en interprétant efficacement les documents techniques, schémas et images.

## Table des matières

1. [Prérequis système](#1-prérequis-système)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Utilisation de l'API](#4-utilisation-de-lapi)
5. [Système OCR](#5-système-ocr)
6. [Interprétation des schémas techniques](#6-interprétation-des-schémas-techniques)
7. [Dépannage](#7-dépannage)
8. [FAQ](#8-faq)

## 1. Prérequis système

### Matériel recommandé
- Processeur: 4 cœurs minimum, 8 cœurs recommandés
- RAM: 8 Go minimum, 16 Go recommandés
- Stockage: 20 Go d'espace disque libre minimum
- Connexion Internet: Requise pour les services cloud (Document AI, Vision AI)

### Logiciels requis
- Python 3.8 ou supérieur
- Node.js 14 ou supérieur (pour l'interface utilisateur)
- Docker (optionnel, pour le déploiement conteneurisé)

### Dépendances externes
- **OCR**: 
  - Tesseract OCR 5.0+
  - Poppler
  - Ghostscript
- **Base de données**: 
  - PostgreSQL 13+ ou SQLite (pour développement)
- **Recherche vectorielle**: 
  - Qdrant (déployé localement ou cloud)

## 2. Installation

### Clonage du dépôt

```bash
git clone https://github.com/votre-organisation/technicia.git
cd technicia
```

### Création de l'environnement virtuel

```bash
python -m venv venv
```

#### Activation de l'environnement virtuel

Windows:
```bash
venv\Scripts\activate
```

Linux/MacOS:
```bash
source venv/bin/activate
```

### Installation des dépendances Python

```bash
pip install -r requirements.txt
```

### Installation des dépendances Node.js (pour l'interface)

```bash
cd frontend
npm install
cd ..
```

### Installation des outils OCR

#### Windows

1. **Tesseract OCR**:
   ```
   winget install UB-Mannheim.TesseractOCR
   ```
   ou télécharger depuis https://github.com/UB-Mannheim/tesseract/wiki

2. **Poppler**:
   ```
   choco install poppler
   ```

3. **Ghostscript**:
   ```
   choco install ghostscript
   ```

#### Linux

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils ghostscript
sudo apt-get install -y tesseract-ocr-fra  # Pour le français
```

#### MacOS

```bash
brew install tesseract poppler ghostscript
brew install tesseract-lang  # Pour les langues additionnelles
```

## 3. Configuration

### Configuration de l'environnement

Copiez le fichier d'exemple `.env.example` en `.env` et modifiez les variables selon votre environnement:

```bash
cp .env.example .env
```

Principales variables à configurer:

```
# Configuration de la base de données
DATABASE_URL=postgresql://username:password@localhost/technicia

# Configuration OCR
TESSERACT_PATH=/chemin/vers/tesseract
POPPLER_PATH=/chemin/vers/poppler
GHOSTSCRIPT_PATH=/chemin/vers/ghostscript

# Configuration Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=technicia

# Configuration LLM
LLM_API_KEY=votre_clé_api
LLM_MODEL=voyage-2
LLM_EMBEDDINGS_MODEL=voyage-large-2

# Configuration Document AI et Vision AI (Phase 3)
GOOGLE_APPLICATION_CREDENTIALS=/chemin/vers/credentials.json
DOCUMENT_AI_PROJECT_ID=votre-projet-gcp
DOCUMENT_AI_LOCATION=eu
DOCUMENT_AI_PROCESSOR_ID=votre-processor-id
```

### Configuration initiale de la base de données

```bash
python scripts/setup_database.py
```

### Configuration initiale de Qdrant

```bash
python scripts/setup_qdrant.py
```

## 4. Utilisation de l'API

### Démarrage du serveur

```bash
# Démarrer le serveur backend
python -m app.main

# Dans un autre terminal, démarrer le serveur frontend (optionnel)
cd frontend
npm run dev
```

Le serveur API sera accessible à l'adresse `http://localhost:8000/api/docs` (documentation Swagger).

### Endpoints principaux

#### Traitement de documents

- `POST /api/documents/process`: Traite un document unique
- `POST /api/documents/batch-process`: Traite un lot de documents
- `POST /api/documents/process-and-index`: Traite et indexe un document
- `GET /api/documents/task/{task_id}`: Vérifie le statut d'une tâche de traitement
- `GET /api/documents/supported-formats`: Liste les formats supportés

Exemple de requête pour traiter un document:

```bash
curl -X POST "http://localhost:8000/api/documents/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@chemin/vers/document.pdf" \
  -F "enable_ocr=true" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=100"
```

#### Recherche et questions

- `POST /api/search`: Recherche dans les documents indexés
- `POST /api/ask`: Pose une question sur les documents

Exemple de requête de recherche:

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "procédure de maintenance pompe hydraulique", "top_k": 5}'
```

## 5. Système OCR

Le système OCR de Technicia est conçu pour être flexible et robuste, avec différentes options de traitement adaptées aux types de documents.

> **ℹ️ Note ℹ️**  
> Pour une documentation complète et détaillée du système OCR et de son tableau de bord, consultez le document consolidé : [OCR_DASHBOARD_COMPLET.md](./OCR_DASHBOARD_COMPLET.md)

### Tableau de bord OCR

Technicia intègre un tableau de bord OCR en cours de développement accessible à l'adresse :
```
http://localhost:8000/dashboard
```

> ⚠️ **Note importante** ⚠️  
> Le tableau de bord OCR est actuellement en cours de développement.  
> Certaines fonctionnalités mentionnées ci-dessous peuvent être partiellement implémentées.  
> Consultez [SUIVI_IMPLEMENTATION.md](./MVP/SUIVI_IMPLEMENTATION.md) pour connaître l'état d'avancement précis.

Ce tableau de bord offrira les fonctionnalités suivantes :
- Surveillance en temps réel des tâches OCR via WebSockets
- Gestion des tâches (création, pause, reprise, annulation)
- Métriques de performance par fournisseur OCR
- Exportation des données et génération de rapports (CSV, PDF, JSON)
- Interface utilisateur intuitive avec visualisations

Pour y accéder :
1. Assurez-vous que le serveur est démarré
2. Naviguez vers l'URL du tableau de bord dans votre navigateur
3. Authentifiez-vous avec vos identifiants si nécessaire

### Vérification de l'installation OCR

```bash
python scripts/diagnose_ocr.py
```

Ce script vérifie que tous les composants OCR sont correctement installés et accessibles.

### Options de traitement OCR

Lors du traitement des documents, vous pouvez spécifier différentes options:

- `enable_ocr`: Active le traitement OCR si nécessaire (détection automatique)
- `force_ocr`: Force le traitement OCR même si le document contient déjà du texte
- `language`: Code de langue pour l'OCR (défaut: "fra" pour français)
- `ocr_provider`: Provider OCR à utiliser (options: "ocrmypdf", "tesseract_direct", "document_ai")

### Traitement de documents volumineux

Pour les documents volumineux (>28 Mo), le système utilise une approche par batches pour éviter les timeouts:

```bash
curl -X POST "http://localhost:8000/api/documents/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@chemin/vers/document_large.pdf" \
  -F "enable_ocr=true" \
  -F "batch_size=10" \
  -F "chunk_size=500"
```

### Intégration avec Document AI (Phase 3)

Pour utiliser Google Cloud Document AI, vous devez d'abord configurer un compte GCP et créer un processeur Document AI:

1. Créez un projet GCP: https://console.cloud.google.com/
2. Activez l'API Document AI
3. Créez un processeur Document AI adapté à vos besoins
4. Générez une clé de compte de service et configurez `GOOGLE_APPLICATION_CREDENTIALS`

Une fois configuré, vous pouvez utiliser Document AI comme provider OCR:

```bash
curl -X POST "http://localhost:8000/api/documents/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@chemin/vers/document.pdf" \
  -F "ocr_provider=document_ai"
```

## 6. Interprétation des schémas techniques

### Extraction de schémas depuis les documents

Pour extraire des schémas techniques à partir de documents PDF:

```bash
python scripts/extract_schemas.py --input chemin/vers/document.pdf --output chemin/vers/dossier_sortie
```

### Analyse des schémas avec Vision AI (Phase 3)

Pour analyser des schémas techniques avec Vision AI:

1. Configurez un compte GCP et activez l'API Vision AI
2. Configurez la variable `GOOGLE_APPLICATION_CREDENTIALS`

```bash
python scripts/analyze_schema.py --input chemin/vers/schema.png
```

### Requêtes multimodales

Pour poser des questions impliquant des schémas techniques:

```bash
curl -X POST "http://localhost:8000/api/multimodal/ask" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@chemin/vers/schema.png" \
  -F "question=Que représente ce symbole dans le schéma?"
```

## 7. Dépannage

### Problèmes d'OCR

#### OCR lent ou qui échoue

1. Vérifiez que les chemins vers Tesseract, Poppler et Ghostscript sont correctement configurés
2. Assurez-vous que les versions sont compatibles
3. Pour les documents volumineux, augmentez les paramètres de timeout
4. Utilisez l'approche par batches pour les fichiers de grande taille

```bash
python scripts/diagnose_ocr.py --verbose
```

#### Qualité OCR insuffisante

1. Essayez d'augmenter la résolution des images (`--dpi 600`)
2. Vérifiez que vous utilisez le bon modèle de langue
3. Pour des documents spécifiques, essayez différents providers OCR

### Problèmes de base de données

```bash
python scripts/diagnose_database.py
```

### Problèmes de stockage vectoriel

```bash
python scripts/diagnose_qdrant.py
```

## 8. FAQ

**Q: Comment puis-je optimiser le système pour des documents techniques spécifiques?**  
R: Vous pouvez créer des profils OCR personnalisés dans `app/core/file_processing/ocr/profiles/` pour différents types de documents.

**Q: Est-il possible d'utiliser le système sans connexion Internet?**  
R: Oui, le système de base fonctionne entièrement en local. Seules les fonctionnalités de la Phase 3 (Document AI, Vision AI) nécessitent une connexion Internet.

**Q: Comment puis-je contribuer au projet?**  
R: Consultez notre guide de contribution dans `CONTRIBUTING.md` et notre code de conduite dans `CODE_OF_CONDUCT.md`.

**Q: Où puis-je trouver des exemples d'utilisation?**  
R: Des exemples sont disponibles dans le dossier `examples/`, notamment `document_processing_client.html` pour le traitement de documents.

**Q: Comment puis-je surveiller les performances du système?**  
R: Utilisez notre tableau de bord de monitoring à l'adresse `http://localhost:8000/monitoring` (nécessite de démarrer le serveur avec `--enable-monitoring`).

---

## Support et contact

Pour toute question ou problème, veuillez:
1. Consulter notre [documentation complète](./README.md)
2. Vérifier les [issues GitHub](https://github.com/votre-organisation/technicia/issues)
3. Contacter notre équipe support à support@technicia.com

---

*Ce guide est mis à jour régulièrement pour refléter les dernières fonctionnalités et améliorations du système Technicia.*

Dernière mise à jour: 31 mars 2025
