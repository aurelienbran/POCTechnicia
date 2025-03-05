# Organisation des Scripts

Ce dossier contient les scripts nécessaires au fonctionnement, à la maintenance et au diagnostic du projet. 
Les scripts ont été organisés dans différents sous-dossiers pour faciliter leur utilisation et leur maintenance.

## Structure des Dossiers

### 1. startup/
Scripts de démarrage des composants de l'application :
- 1-start-qdrant.bat : Démarrage du serveur Qdrant
- 2-start-backend.bat : Démarrage du backend FastAPI
- 3-start-frontend.bat : Démarrage du frontend React
- start-all-components.bat : Démarrage de tous les composants en une seule commande

### 2. maintenance/
Scripts de maintenance du système :
- clean_qdrant.bat : Nettoyage des collections Qdrant
- cleanup_project.bat : Nettoyage des fichiers temporaires
- portable_installer.bat : Création d'installateur portable
- setup_project.bat : Configuration initiale du projet

### 3. python/
Scripts Python pour la gestion de Qdrant :
- check_qdrant.py : Vérification de l'état de Qdrant
- clean_all_collections.py : Suppression des collections
- clean_documents.py : Nettoyage de la collection documents
- create_snapshot.py : Création de snapshots Qdrant
- initialize_qdrant.py : Initialisation de Qdrant
- restore_snapshot.py : Restauration de snapshots

### 4. tools/
Outils de diagnostic et de test :
- diagnostic_tool.py : Outil de diagnostic complet
- test_query.py : Test de requêtes Qdrant
- upload_file.py : Utilitaire d'upload de fichiers
- verify_index.py : Vérification d'index vectoriel

### 5. deprecated/
Scripts obsolètes (conservés pour référence) :
- Note : Ces scripts sont conservés uniquement pour référence et ne doivent pas être utilisés

## Utilisation Recommandée

1. Pour démarrer le projet :
   ```
   cd startup
   start-all-components.bat
   ```

2. Pour nettoyer Qdrant :
   ```
   cd maintenance
   clean_qdrant.bat
   ```

3. Pour diagnostiquer un problème :
   ```
   cd tools
   python diagnostic_tool.py
   ```

4. Pour configurer le projet pour la première fois :
   ```
   cd maintenance
   setup_project.bat
   ```

Pour plus d'informations, consultez la documentation complète du projet dans le dossier "documentation/".
