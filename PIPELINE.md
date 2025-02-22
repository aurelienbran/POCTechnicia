# Pipelines de Traitement

Ce document décrit les trois pipelines principaux de notre système RAG (Retrieval Augmented Generation) :
1. Pipeline de traitement des documents PDF
2. Pipeline de discussion avec le chatbot
3. Pipeline de dialogue

## 1. Pipeline de Traitement des Documents PDF

Ce pipeline transforme un document PDF en une base de connaissances interrogeable.

### Schéma du Pipeline
```
PDF Upload → Extraction → Découpage → Embeddings → Indexation
   ↓            ↓           ↓           ↓            ↓
[Fichier] → [PyMuPDF] → [Chunks] → [VoyageAI] → [Qdrant]
   150Mo     Texte      500-1000    Vecteurs     Point = {
   max       propre     tokens      1024dim      - id: uuid
                                                 - vector: [1024]
                                                 - payload: {
                                                     text: "...",
                                                     page: N,
                                                     ...
                                                   }
                                                 }
```

### Étapes Détaillées du Processus

1. **Upload du Document** (`app/api/routes/documents.py`)
   - L'utilisateur télécharge un PDF via l'interface
   - Validation :
     - Extension .pdf
     - Taille max 150 Mo
     - Intégrité du fichier
   - Stockage temporaire dans `uploads/{uuid}.pdf`

2. **Extraction du Texte** (`app/core/pdf_processor.py`)
   - PyMuPDF ouvre le PDF en mode optimisé
   - Pour chaque page :
     - Extraction du texte brut avec `page.get_text("text")`
     - Conservation de la mise en forme basique
     - Nettoyage :
       - Suppression des caractères spéciaux
       - Normalisation des espaces
       - Fusion des lignes cohérentes

3. **Découpage en Chunks** (`app/core/pdf_processor.py`)
   Stratégie de chunking optimisée :
   - Taille moyenne des chunks : 571 caractères
   - Distribution adaptative :
     - 64% chunks courts (<500 car.) pour précision
     - 15% chunks moyens (500-999 car.) pour contexte local
     - 21% chunks longs (>1000 car.) pour contexte étendu
   - Préservation des sections logiques du document

4. **Génération des Embeddings** (`app/core/llm_interface.py`)
   - Utilisation de Voyage AI pour les embeddings
   - Dimension des vecteurs : 1024
   - Distance cosinus pour la similarité
   - Configuration HNSW optimisée :
     - m=16 pour l'index
     - ef_construct=100 pour la construction

5. **Indexation dans Qdrant** (`app/core/vector_store.py`)
   État actuel :
   - 335 vecteurs indexés
   - 2 segments optimaux
   - Status "green" avec optimiseur actif
   - Payload on_disk activé pour performance

### Suivi de Progression
- Barre de progression pour chaque étape
- Estimation du temps restant
- Statut détaillé dans les logs
- Points de reprise en cas d'erreur

## 2. Pipeline de Recherche et Réponse

1. **Réception de la Question** (`app/api/routes/chat.py`)
   - Validation de l'entrée :
     - Longueur : 10-1000 caractères
     - Nettoyage basique du texte
   - Génération de l'embedding via VoyageAI :
     - Utilisation de `input_type="search_query"`
     - Optimisé pour la recherche sémantique

2. **Recherche Contextuelle** (`app/core/vector_store.py`)
   - Recherche des documents pertinents dans Qdrant
   - Score de similarité minimum : 0.7
   - Limite par défaut : 4 documents
   - Filtrage possible par métadonnées

3. **Génération de Réponse** (`app/core/llm_interface.py`)
   - Utilisation de Claude 3 Sonnet
   - Formatage du contexte avec scores
   - Prompt optimisé pour la précision
   - Génération de questions de suivi
   - Gestion des sources utilisées

### Interface Utilisateur
- Upload via sidebar compact
- Modal de progression avec détails
- Chat avec historique scrollable
- Affichage des sources avec scores
- Gestion des erreurs côté client
- Design responsive avec Tailwind CSS

## 3. Pipeline de Dialogue

### Modes de Fonctionnement

1. **Mode Conversation**
   - Questions générales
   - Salutations et interactions basiques
   - Utilisation directe de Claude 3 Sonnet
   - Maintien du contexte conversationnel

2. **Mode Documentation**
   - Questions techniques
   - Recherche de spécifications
   - Procédures et instructions
   - Utilisation de la recherche vectorielle + Claude

3. **Mode Hybride**
   - Détection automatique du mode approprié
   - Transition fluide entre les modes
   - Combinaison des sources d'information
   - Maintien de la cohérence du dialogue

### Gestion du Contexte
- Historique des conversations
- Contexte des documents pertinents
- État de l'interface utilisateur
- Préférences utilisateur

### Optimisations en Cours
1. **Performance**
   - Mise en cache des embeddings fréquents
   - Optimisation des requêtes Qdrant
   - Réduction des temps de réponse

2. **Qualité des Réponses**
   - Amélioration du chunking
   - Enrichissement des métadonnées
   - Optimisation des prompts

3. **Interface Utilisateur**
   - Correction des problèmes d'upload
   - Amélioration du feedback
   - Gestion des erreurs plus intuitive

## Performance et Optimisation

### Pipeline de Traitement PDF

```
[PDF] --> [Extraction] --> [Chunking] --> [Vectorisation] --> [Stockage]
 |            |              |               |                  |
 |        ~0.5-1s/MB     4-10/page     ~1-2s/chunk      ~0.1s/chunk
 |
Taille : 0.1-150MB
```

### Métriques de Performance

#### Traitement PDF
- Vitesse : 0.90-11.22 MB/s selon la taille
- Mémoire : ~2-3 MB pour les petits fichiers
- Chunks : ~10 chunks/MB en moyenne

#### Vectorisation
- Dimension : 1024 (VoyageAI)
- Batch size : 10 chunks
- Latence moyenne : ~1-2s/chunk

#### Stockage Vectoriel
- Backend : Qdrant (local)
- Index : HNSW
- Latence recherche : < 100ms

### Limites Actuelles
1. Traitement
   - Maximum : 150 MB par fichier
   - Temps moyen : 5.43s (objectif < 5s)
   - Mémoire : < 1GB

2. Chunks
   - Taille : 200-1000 caractères
   - Chevauchement : 20%
   - Métadonnées : page, position, contexte

3. Recherche
   - Top-k : 5 chunks par défaut
   - Score minimum : 0.7
   - Timeout : 30s

## Optimisations Actuelles

### Traitement PDF
- Lecture page par page (mémoire optimisée)
- Nettoyage intelligent du texte
- Chunking avec chevauchement
- Traitement asynchrone

### Recherche et Réponse
- Seuil de similarité : 0.7
- Cache des embeddings fréquents
- Limitation intelligente du contexte
- Retry automatique en cas d'erreur API

## Monitoring
```
┌─ Performance ──────────┐  ┌─ Ressources ───────┐
│ PDF Process: 2.3s/page │  │ RAM: 824MB/1GB     │
│ Embedding: 0.4s/chunk  │  │ CPU: 45%           │
│ Search: 0.8s          │  │ Disk: 2.1GB        │
│ Response: 3.1s        │  │ Qdrant: 500MB      │
└──────────────────────┘  └───────────────────┘
```

- Logs détaillés dans `logs/app.log`
- Métriques de performance dans `performance_reports/`
- Alertes Discord pour les erreurs critiques
- Suivi des temps de réponse
