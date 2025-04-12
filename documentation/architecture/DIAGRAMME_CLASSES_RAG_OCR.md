# Diagramme de classes détaillé: RAG et OCR

> **ℹ️ État d'implémentation ℹ️**  
> Ce document présente les classes et composants du système RAG et OCR de Technicia.  
> État actuel (1 avril 2025) :
> - ✅ Système RAG : entièrement implémenté
> - ✅ Système OCR hybride : implémenté
> - 🔄 Tableau de bord OCR : en cours de développement
> - ⏳ Traitement par lots des documents volumineux : planifié

## Diagramme de classes du système RAG

```
+-----------------------+       +---------------------+
|    RAGEngine          |       |  QuestionClassifier |
+-----------------------+       +---------------------+
| - vector_store        |------>| - model             |
| - llm_interface       |       | - threshold         |
| - embedding_model     |       +---------------------+
| - cache               |       | + classify()        |
+-----------------------+       | + get_keywords()    |
| + ask_question()      |       +---------------------+
| + search_context()    |               ^
| + generate_answer()   |               |
| + get_sources()       |       +-------+-----------+
| + index_document()    |       |  ClassifierConfig |
| - _get_chunks()       |       +-------------------+
| - _format_prompt()    |       | - model_name      |
| - _augment_with_src() |       | - parameters      |
+-----------+-----------+       +-------------------+
            |
            v
+------------------------+      +---------------------+
|    VectorStore         |      |   ChunkManager      |
+------------------------+      +---------------------+
| - client               |----->| - chunk_size        |
| - collection_name      |      | - chunk_overlap     |
| - embedding_dim        |      | - max_chunks        |
+------------------------+      +---------------------+
| + add_texts()          |      | + create_chunks()   |
| + similarity_search()  |      | + optimize_chunks() |
| + delete_collection()  |      | + merge_small()     |
| + health_check()       |      +---------------------+
+------------------------+

+------------------------+      +---------------------+
|    LLMInterface        |      |   SourceFormatter   |
+------------------------+      +---------------------+
| - api_key              |----->| - max_sources       |
| - model_name           |      | - format_template   |
| - max_tokens           |      +---------------------+
| - temperature          |      | + format_sources()  |
+------------------------+      | + deduplicate()     |
| + generate()           |      | + extract_metadata()|
| + stream_generate()    |      +---------------------+
| + create_embedding()   |
| + embed_document()     |
+------------------------+
```

### Relations et responsabilités clés

1. **RAGEngine**: Composant central qui coordonne l'ensemble du processus RAG.
   - Utilise **VectorStore** pour stocker et rechercher des chunks de texte similaires
   - Interagit avec **LLMInterface** pour générer des réponses
   - Emploie **QuestionClassifier** pour optimiser les recherches
   - Utilise **SourceFormatter** pour présenter les sources utilisées

2. **Problème de timeout identifié**: 
   - Lors du traitement des documents volumineux (>28 Mo), des timeouts se produisent pendant la génération des embeddings via l'API Voyage AI
   - Le timeout actuel est de 600 secondes (10 minutes)
   - Solution à implémenter: traitement par lots (batching) et mécanisme de reprise

## Diagramme de classes du système OCR (implémenté)

```
+---------------------+        +----------------------+
|    PDFProcessor     |        |    OCRSelector       |
+---------------------+        +----------------------+
| - min_text_percent  |------->| - confidence_threshold|
| - storage_manager   |        | - providers          |
+---------------------+        +----------------------+
| + process_pdf()     |        | + select_ocr_method()|
| + extract_text()    |        | + analyze_document() |
| + needs_ocr()       |        | + get_best_provider()|
+----------+----------+        +----------------------+
           |                             ^
           v                             |
+---------------------+        +--------+-------------+
|    OCRHelper        |        |   OCRProviderManager |
+---------------------+        +----------------------+
| - ocrmypdf_config   |------->| - available_providers|
| - tesseract_config  |        | - provider_configs   |
| - logger            |        +----------------------+
+---------------------+        | + register_provider()|
| + process()         |        | + get_provider()     |
| + detect_language() |        | + list_providers()   |
| + enhance_image()   |        +----------------------+
+----------+----------+
           |
           v
+---------------------+        +----------------------+
|    OCRLogger        |        |   OCRMetricsCollector|
+---------------------+        +----------------------+
| - log_level         |------->| - metrics_store      |
| - log_path          |        | - collection_enabled |
+---------------------+        +----------------------+
| + log_process()     |        | + record_metrics()   |
| + log_error()       |        | + get_provider_stats()|
| + get_logs()        |        | + reset_metrics()    |
+---------------------+        +----------------------+
```

### Relations et responsabilités clés (système implémenté)

1. **PDFProcessor**: Point d'entrée pour le traitement des documents PDF.
   - Coordonne l'extraction de texte et la détection de besoin d'OCR
   - Délègue le traitement OCR à **OCRHelper** quand nécessaire
   - Gère les fichiers via **StorageManager**

2. **OCRSelector**: ✅ IMPLÉMENTÉ
   - Analyse les caractéristiques du document pour sélectionner la méthode OCR optimale
   - Évalue la qualité du document (résolution, contraste, etc.)
   - Choisit entre OCRmyPDF, Tesseract direct, ou autre fournisseur

3. **OCRHelper**: ✅ IMPLÉMENTÉ
   - Détecte automatiquement si un document a besoin d'OCR
   - Configure et utilise OCRmyPDF, Tesseract, et autres outils
   - Fournit des diagnostics via **OCRLogger**

4. **OCRMetricsCollector**: ✅ IMPLÉMENTÉ
   - Collecte les métriques de performance pour chaque traitement OCR
   - Alimente le tableau de bord OCR avec des statistiques
   - Permet de comparer l'efficacité des différents fournisseurs OCR

## Diagramme de classes du tableau de bord OCR (en cours de développement)

```
+---------------------+        +----------------------+
|    DashboardAPI     |        |    TaskManager       |
+---------------------+        +----------------------+
| - router            |------->| - active_tasks       |
| - auth_dependency   |        | - task_history       |
+---------------------+        +----------------------+
| + get_statistics()  |        | + create_task()      |
| + ocr_performance() |        | + get_task_by_id()   |
| + get_active_tasks()|        | + update_task()      |
| + get_task_history()|        | + get_task_stats()   |
+----------+----------+        +--------+-------------+
           |                            |
           v                            v
+---------------------+        +----------------------+
|    ExportAPI        |        |   WebSocketManager   |
+---------------------+        +----------------------+
| - export_formats    |        | - active_connections |
| - background_tasks  |        | - event_handlers     |
+---------------------+        +----------------------+
| + export_history()  |        | + connect_client()   |
| + export_metrics()  |        | + disconnect_client()|
| + download_export() |        | + broadcast_event()  |
+---------------------+        +----------------------+
```

### État d'implémentation du tableau de bord OCR

1. **DashboardAPI**: 🔄 PARTIELLEMENT IMPLÉMENTÉ
   - Endpoints pour les statistiques et l'historique des tâches: ✅ implémentés
   - Endpoints pour les performances OCR: 🔄 en cours
   - Actions sur les tâches (pause, reprise): 🔄 en cours

2. **TaskManager**: ✅ IMPLÉMENTÉ
   - Gestion du cycle de vie des tâches OCR
   - Stockage de l'historique et des statistiques
   - Interfaces avec les fournisseurs OCR

3. **ExportAPI**: ✅ IMPLÉMENTÉ
   - Exportation des données d'historique et des métriques
   - Support des formats CSV, JSON et PDF
   - Génération de rapports en arrière-plan

4. **WebSocketManager**: 🔄 EN COURS
   - Backend partiellement implémenté
   - Intégration frontend en cours de développement
   - Diffusion des mises à jour en temps réel

## Architecture de traitement des documents volumineux (planifiée pour future implémentation)

```
+---------------------+       +------------------------+
| DocumentProcessor   |       |  BatchProcessor        |
+---------------------+       +------------------------+
| - batch_size        |------>| - current_batch        |
| - timeout           |       | - batch_states         |
| - retry_strategy    |       | - batch_results        |
+---------------------+       +------------------------+
| + process()         |       | + divide_into_batches()|
| + resume_failed()   |       | + process_batch()      |
| + monitor_progress()|       | + combine_results()    |
+---------------------+       | + get_state()          |
         |                    +------------------------+
         |
         v
+---------------------+       +------------------------+
| ProcessingStrategy  |       |  ErrorHandler          |
+---------------------+       +------------------------+
| + choose_strategy() |------>| - error_types          |
| + parallel_process()|       | - recovery_strategies  |
| + sequential_proc() |       +------------------------+
+---------------------+       | + handle_error()       |
                              | + can_recover()        |
                              | + log_error()          |
                              +------------------------+
```

### Conception du système de traitement par lots

1. **DocumentProcessor**: Nouveau composant central pour le traitement de documents.
   - Divise les documents volumineux en lots gérables
   - Configure des timeouts adaptés à chaque type de traitement
   - Implémente des stratégies de reprise intelligentes

2. **BatchProcessor**: Gère le traitement par lots.
   - Maintient l'état de chaque lot
   - Permet de reprendre le traitement après un échec
   - Combine les résultats partiels

3. **ErrorHandler**: Gère les erreurs de manière intelligente.
   - Catégorise les erreurs (timeout, réseau, etc.)
   - Applique des stratégies de récupération spécifiques
   - Enregistre les erreurs pour analyse

## Recommandations d'implémentation

1. **Pour les timeouts OCR/embedding**:
   - Implémenter le système de traitement par lots avec état persistant
   - Configurer des timeouts différents selon la taille du document
   - Créer un mécanisme de reprise qui sauvegarde les résultats partiels

2. **Pour l'OCR avancé**:
   - Maintenir le système OCR existant comme fallback
   - Ajouter une couche d'abstraction pour Google Document AI
   - Développer un sélecteur intelligent basé sur la qualité du document

3. **Pour l'optimisation des performances**:
   - Ajouter un système de cache pour les embeddings fréquemment utilisés
   - Implémenter un prétraitement plus intelligent des documents
   - Optimiser les chunks de texte pour maximiser la pertinence
