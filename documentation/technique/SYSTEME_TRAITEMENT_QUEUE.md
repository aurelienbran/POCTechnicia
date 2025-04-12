# Système de traitement et pipelines

> **ℹ️ Note importante ℹ️**  
> Ce document technique unifié décrit les pipelines de traitement et le système de file d'attente OCR dans le projet Technicia.
>
> Dernière mise à jour : 1 avril 2025

## 1. Vue d'ensemble des pipelines

Le système Technicia est bâti autour de trois pipelines principaux :
1. **Pipeline de traitement des documents** : transformation de documents en base de connaissances
2. **Pipeline OCR et file d'attente** : traitement et reconnaissance de documents
3. **Pipeline de dialogue** : interactions avec le chatbot

Ce document se concentre principalement sur les deux premiers pipelines, qui forment le cœur du système de traitement des documents.

## 2. Pipeline de traitement des documents

### 2.1 Schéma général

Ce pipeline transforme un document (PDF, image, etc.) en une base de connaissances interrogeable.

```
Document → Extraction → Découpage → Embeddings → Indexation
   ↓            ↓           ↓           ↓            ↓
[Fichier] → [Processeurs → [Chunks] → [VoyageAI] → [Qdrant]
   150Mo     OCR+NLP     500-1000    Vecteurs     Point = {
   max                    tokens      1024dim      - id: uuid
                                                   - vector: [1024]
                                                   - payload: {
                                                       content: "...",
                                                       metadata: {...}
                                                    }
                                                  }
```

### 2.2 Étapes détaillées

1. **Upload de document**
   - Réception du fichier via l'API
   - Validation format et taille
   - Stockage temporaire
   - Génération d'un ID de tâche

2. **Extraction de texte**
   - Pour les PDF textuels : extraction directe
   - Pour les images ou scans : traitement OCR
     - OCRmyPDF pour PDF scannés
     - Tesseract pour images
     - Document AI pour documents complexes
     - Vision AI pour schémas et images

3. **Découpage (Chunking)**
   - Découpage en fragments de 500-1000 tokens
   - Préservation du contexte aux frontières
   - Métadonnées sur la structure du document
   - Stratégies adaptatives selon le contenu

4. **Génération d'embeddings**
   - Modèle : VoyageAI voyage-2 (1024 dimensions)
   - Représentation vectorielle de chaque chunk
   - Traitement par lots pour les documents volumineux
   - Mise en cache pour optimisation

5. **Indexation vectorielle**
   - Stockage dans Qdrant (base vectorielle)
   - Association du texte source et métadonnées
   - Création d'une collection par projet
   - Configuration des paramètres de similarité

### 2.3 Paramètres et optimisation

- **Configuration chunking**
  - `chunk_size` : Taille des chunks (500-1000 tokens recommandés)
  - `chunk_overlap` : Chevauchement entre chunks (10-20% recommandé)
  - `split_strategy` : Méthode de découpage (paragraphe, section, etc.)

- **Configuration embeddings**
  - `embedding_model` : Modèle à utiliser (voyage-2 par défaut)
  - `batch_size` : Nombre de chunks traités simultanément
  - `timeout` : Délai maximum pour la génération

- **Configuration indexation**
  - `collection_name` : Nom de la collection Qdrant
  - `distance_metric` : Métrique de distance (cosine par défaut)
  - `index_params` : Paramètres d'optimisation de l'index

## 3. Système de file d'attente OCR

### 3.1 Vue d'ensemble

Le système de file d'attente OCR est une solution complète pour gérer efficacement les tâches OCR longues et complexes, en particulier pour les documents volumineux. Il résout les problèmes de timeout et de ressources limitées en introduisant un mécanisme robuste de mise en file d'attente avec priorité, de traitement par lots, et de reprise sur erreur.

**Fonctionnalités principales:**
- File d'attente avec gestion des priorités
- Traitement de documents par chunks
- Interface de gestion des tâches (pause, reprise, annulation)
- Système de notification en temps réel via WebSockets
- Métriques détaillées et tableau de bord
- API RESTful pour l'intégration avec d'autres systèmes

### 3.2 Architecture

Le système est composé de plusieurs modules interdépendants:

```
┌───────────────────┐      ┌────────────────────┐     ┌────────────────────┐
│ Interface Web     │      │ API RESTful        │     │ WebSockets         │
│ (Dashboard OCR)   │<────>│ (Endpoints OCR)    │<───>│ (Notifications)    │
└───────────────────┘      └────────────────────┘     └────────────────────┘
          ^                          ^                          ^
          │                          │                          │
          v                          v                          v
┌───────────────────────────────────────────────────────────────────────────┐
│                         OCRQueueManager                                   │
│                                                                           │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────────┐     │
│  │ Task Queue    │    │ Task Scheduler │    │ Task State Manager    │     │
│  └───────────────┘    └───────────────┘    └───────────────────────┘     │
└───────────────────────────────────────────────────────────────────────────┘
          ^                          ^                          ^
          │                          │                          │
          v                          v                          v
┌───────────────────┐      ┌────────────────────┐     ┌────────────────────┐
│ OCR Processors    │      │ Document Analyzer  │     │ Result Processor   │
│ (OCRmyPDF,        │<────>│ (Type, Qualité,    │<───>│ (Validation,       │
│  Tesseract, etc.) │      │  Complexité)       │     │  Indexation)       │
└───────────────────┘      └────────────────────┘     └────────────────────┘
```

### 3.3 Composants principaux

#### 3.3.1 OCRQueueManager

Le `OCRQueueManager` est le composant central qui orchestre l'ensemble du processus OCR:

```python
from app.core.file_processing.ocr.ocr_queue_manager import OCRQueueManager

# Singleton pattern
queue_manager = OCRQueueManager()

# Ajouter une tâche
task_id = await queue_manager.add_task(
    file_path="/path/to/document.pdf",
    priority=5,
    ocr_options={
        "engine": "auto",
        "languages": ["fra", "eng"],
        "enable_tables": True
    }
)

# Obtenir l'état d'une tâche
task_info = await queue_manager.get_task_info(task_id)
print(f"Status: {task_info.status}, Progress: {task_info.progress}%")

# Contrôler une tâche
await queue_manager.pause_task(task_id)
await queue_manager.resume_task(task_id)
await queue_manager.cancel_task(task_id)
```

Caractéristiques:
- Gestion des priorités (1-10)
- Persistance des tâches
- Reprise après redémarrage
- Limitation des tâches simultanées
- Statistiques et métriques

#### 3.3.2 Task Scheduler

Le planificateur de tâches détermine quelle tâche exécuter ensuite en fonction de:
- Priorité assignée
- Temps d'attente
- Disponibilité des ressources
- Dépendances entre tâches

Il utilise un algorithme qui équilibre l'exécution entre les tâches prioritaires et celles qui attendent depuis longtemps, évitant ainsi la famine de ressources.

#### 3.3.3 Task State Manager

Ce composant gère l'état des tâches tout au long de leur cycle de vie:
- `PENDING`: En attente d'exécution
- `PROCESSING`: En cours de traitement
- `PAUSED`: Mise en pause par l'utilisateur
- `COMPLETED`: Traitement terminé avec succès
- `FAILED`: Échec du traitement
- `CANCELED`: Annulée par l'utilisateur

Il fournit également des mécanismes pour la persistance des états, permettant la reprise des tâches même après un redémarrage du serveur.

#### 3.3.4 Document Analyzer

Avant le traitement OCR proprement dit, le document est analysé pour déterminer:
- Le type de document (PDF texte, PDF scanné, image)
- La qualité du scan ou de l'image
- La complexité (nombre de colonnes, tableaux, images)
- La langue probable

Ces informations sont utilisées pour sélectionner la méthode OCR optimale et estimer le temps de traitement.

### 3.4 Workflow d'une tâche OCR

1. **Soumission**
   - L'utilisateur soumet un document via l'API
   - Le système analyse le document et crée une tâche
   - La tâche est placée dans la file d'attente avec sa priorité

2. **Planification**
   - Le Task Scheduler sélectionne la prochaine tâche à exécuter
   - Les ressources nécessaires sont réservées
   - L'état de la tâche passe à `PROCESSING`

3. **Traitement**
   - Le document est découpé en pages ou chunks si nécessaire
   - Le processeur OCR approprié est sélectionné et appliqué
   - La progression est mise à jour en temps réel

4. **Finalisation**
   - Les résultats sont agrégés et validés
   - Le texte extrait est structuré selon les besoins
   - Les métriques de qualité sont calculées
   - L'état passe à `COMPLETED`

5. **Notification**
   - WebSocket notifications envoyées au tableau de bord
   - Callbacks déclenchés pour les systèmes intégrés
   - Notifications email envoyées si configurées

### 3.5 API RESTful

L'API du système de file d'attente OCR est accessible via plusieurs endpoints:

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/ocr/tasks` | GET | Liste des tâches avec filtres et pagination |
| `/api/ocr/tasks` | POST | Création d'une nouvelle tâche OCR |
| `/api/ocr/tasks/{task_id}` | GET | Informations détaillées sur une tâche |
| `/api/ocr/tasks/{task_id}` | DELETE | Suppression d'une tâche |
| `/api/ocr/tasks/{task_id}/cancel` | POST | Annulation d'une tâche |
| `/api/ocr/tasks/{task_id}/pause` | POST | Mise en pause d'une tâche |
| `/api/ocr/tasks/{task_id}/resume` | POST | Reprise d'une tâche en pause |
| `/api/ocr/tasks/{task_id}/results` | GET | Récupération des résultats OCR |
| `/api/ocr/stats` | GET | Statistiques globales du système OCR |

### 3.6 WebSockets

Pour les mises à jour en temps réel, le système utilise WebSockets aux points de terminaison suivants:

| Endpoint | Description |
|----------|-------------|
| `/ws/ocr/dashboard` | Mises à jour pour le tableau de bord principal |
| `/ws/ocr/task/{task_id}` | Mises à jour pour une tâche spécifique |
| `/ws/ocr/all` | Mises à jour pour toutes les tâches et statistiques |

Les messages WebSocket utilisent un format JSON standardisé:

```json
{
  "type": "task_update",
  "task_id": "abc123",
  "data": {
    "status": "PROCESSING",
    "progress": 45,
    "current_step": "OCR processing page 9/20",
    "estimated_time_remaining": 120
  }
}
```

### 3.7 Configuration

Le système de file d'attente OCR est configurable via plusieurs paramètres:

```python
# Configuration dans config.py
OCR_QUEUE_CONFIG = {
    "max_concurrent_tasks": 3,  # Nombre maximum de tâches simultanées
    "default_priority": 5,      # Priorité par défaut (1-10)
    "results_ttl": 86400,       # Durée de conservation des résultats (secondes)
    "retry_attempts": 3,        # Nombre de tentatives en cas d'échec
    "timeout": 3600,            # Délai maximum pour une tâche (secondes)
    "chunk_size": 5,            # Nombre de pages à traiter par lot
    "notification_email": True,  # Activer les notifications par email
    "enable_metrics": True      # Collecter des métriques détaillées
}
```

Ces paramètres peuvent être modifiés directement dans le fichier de configuration ou via l'interface d'administration.

## 4. Intégration entre les pipelines

### 4.1 Flux complet de traitement

Le système complet de traitement des documents suit ce flux:

```
Upload → OCRQueueManager → OCR Processing → Text Extraction → Chunking → Embedding → Indexation
  ↓            ↓                 ↓                ↓              ↓           ↓           ↓
Document → File d'attente → Reconnaissance → Texte extrait → Fragments → Vecteurs → Base Qdrant
                                                                                       ↓
                                                                                    RAG System
```

### 4.2 Points d'intégration

1. **OCRQueueManager vers OCR Processing**
   - Le gestionnaire de file d'attente sélectionne et lance les processeurs OCR appropriés
   - Les tâches sont exécutées avec les paramètres optimaux
   - Les résultats sont validés et structurés

2. **OCR Processing vers Chunking**
   - Le texte extrait est transmis au module de chunking
   - Les métadonnées OCR (confiance, structure) sont préservées
   - Les relations entre texte et éléments visuels sont maintenues

3. **Chunking vers Embedding**
   - Les chunks sont transmis au service d'embedding
   - Traitement par lots pour optimiser les performances
   - Mise en cache des embeddings fréquents

4. **Embedding vers Indexation**
   - Les vecteurs sont stockés dans Qdrant
   - Les métadonnées sont enrichies pour la recherche
   - Les collections sont organisées par projet/domaine

### 4.3 Communication entre composants

Les différents composants du système communiquent via:
- API internes asynchrones
- File d'attente de messages (RabbitMQ/Redis)
- Callbacks et événements
- Stockage partagé pour les données volumineuses

## 5. Optimisations et considérations techniques

### 5.1 Performance

1. **Traitement parallèle**
   - Exécution simultanée de plusieurs tâches OCR
   - Traitement multi-thread des documents volumineux
   - Utilisation efficace des ressources CPU/GPU

2. **Mise en cache**
   - Cache des résultats intermédiaires
   - Mémoire partagée pour les modèles chargés
   - Stockage des métadonnées fréquemment utilisées

3. **Reprise sur erreur**
   - Checkpointing régulier des tâches longues
   - Capacité à reprendre après un échec à l'étape correspondante
   - Isolation des erreurs pour éviter les cascades d'échecs

### 5.2 Scalabilité

Le système est conçu pour être scalable horizontalement:
- Architecture modulaire
- Services indépendants
- Stateless quand possible
- Conteneurisation compatible

Pour augmenter la capacité de traitement:
- Ajouter des workers OCR supplémentaires
- Distribuer les tâches entre plusieurs serveurs
- Utiliser un stockage distribué pour les documents

### 5.3 Monitoring

Le système fournit plusieurs métriques pour le monitoring:
- Temps de traitement par page/document
- Taux de réussite et d'échec
- Utilisation des ressources
- Longueur de la file d'attente
- Précision OCR estimée

Ces métriques sont accessibles via:
- Tableau de bord OCR
- API dédiée
- Exports pour systèmes de monitoring externes (Prometheus)

## 6. Développements futurs

### 6.1 Améliorations planifiées

1. **OCR intelligent**
   - Sélection automatique du moteur OCR optimal par page
   - Apprentissage des paramètres optimaux par type de document
   - Détection et traitement spécial des zones complexes

2. **Traitement distribué**
   - Architecture distribuée pour le traitement OCR
   - Équilibrage de charge dynamique
   - Scaling automatique selon la demande

3. **Validation avancée**
   - Interface de validation manuelle pour les extractions à faible confiance
   - Boucle de feedback pour améliorer les processeurs
   - Métriques de qualité plus granulaires
