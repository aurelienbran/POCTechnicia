# Évaluation des fichiers du projet

Ce document contient une analyse des principaux fichiers du projet, évaluant leur pertinence pour le MVP et identifiant les potentiels candidats pour refactoring ou suppression.

## Structure globale des répertoires

| Répertoire | Pertinence | Description |
|------------|------------|-------------|
| `/app` | Critique | Contient le backend FastAPI et les composants principaux |
| `/app/core` | Critique | Cœur de l'application avec les modules RAG, LLM et OCR |
| `/app/api` | Critique | Endpoints de l'API REST |
| `/app/static` | Importante | Assets statiques et UI compilée |
| `/app/templates` | Moyenne | Templates HTML pour les interfaces serveur |
| `/documentation` | Haute | Documentation du projet |
| `/frontend` | Critique | Interface utilisateur React/TypeScript |
| `/scripts` | Moyenne | Scripts utilitaires pour le développement et le déploiement |
| `/tests` | Haute | Tests automatisés |
| `/storage` | Haute | Gestion des fichiers stockés |
| `/qdrant` | Critique | Configuration et données de la base vectorielle |
| `/uploads` | Critique | Répertoire temporaire pour les uploads de fichiers |

## Composants du cœur (/app/core)

| Fichier | Pertinence | Évaluation |
|---------|------------|------------|
| `llm_interface.py` | Critique | Interface avec les modèles de langage (Anthropic Claude). **À refactorer** pour rendre les prompts plus génériques et modulaires. |
| `rag_engine.py` | Critique | Moteur de recherche et génération augmentée. Bien conçu, mais nécessite optimisation pour le traitement des gros documents. |
| `pdf_processor.py` | Critique | Traitement des documents PDF. **À optimiser** pour gérer les timeouts et implémenter un traitement par lots plus efficace. |
| `ocr_helper.py` | Critique | Fonctions d'aide pour l'OCR. Bien structuré avec détection automatique, mais peut être amélioré avec l'intégration Document AI. |
| `ocr_logger.py` | Moyenne | Logging spécifique pour les opérations OCR. Utile pour le diagnostic. |
| `vector_store.py` | Critique | Interface avec la base de données vectorielle Qdrant. Bien conçu, à préserver. |
| `websocket_manager.py` | Haute | Gestion des WebSockets pour communication en temps réel. Architecture hybride robuste à conserver. |
| `question_classifier.py` | Moyenne | Classification des questions pour optimiser la recherche. Potentiel d'amélioration avec un système plus sophistiqué. |
| `proxy_middleware.py` | Basse | Middleware de proxy. À vérifier si toujours nécessaire pour le MVP. |

## Interface API (/app/api)

Une analyse plus détaillée des endpoints API sera effectuée dans une phase ultérieure, mais globalement, cette couche est bien structurée et doit être préservée avec des ajustements mineurs pour aligner avec le refactoring du core.

## Frontend (/frontend)

| Répertoire/Fichier | Pertinence | Évaluation |
|--------------------|------------|------------|
| `/src/components` | Critique | Composants React réutilisables. Bien structurés, à conserver. |
| `/src/hooks` | Haute | Hooks React personnalisés. Utiles pour la gestion de l'état et des WebSockets. |
| `/src/utils` | Moyenne | Fonctions utilitaires. À réviser pour éliminer les fonctions redondantes. |
| `/src/App.tsx` | Critique | Point d'entrée de l'application. **Nécessite une mise à jour** pour éliminer les références CFF restantes. |
| `/public` | Moyenne | Assets publics. Les logos et favicons ont déjà été mis à jour. |

## Fichiers de dépendances

| Fichier | Pertinence | Évaluation |
|---------|------------|------------|
| `requirements.txt` | Critique | Dépendances Python. Bien organisé, mais à revoir pour éliminer les packages non essentiels. |
| `package.json` | Critique | Dépendances JavaScript. Semble à jour et bien structuré. |
| `setup.py` | Moyenne | Configuration du package Python. À maintenir synchronisé avec requirements.txt. |

## Code potentiellement mort ou redondant

Une analyse plus approfondie avec des outils spécifiques sera nécessaire, mais les candidats initiaux pour révision incluent:

1. Scripts obsolètes dans `/scripts` qui peuvent être spécifiques à CFF
2. Templates non utilisés dans `/app/templates`
3. Fonctions utilitaires redondantes dans `/frontend/src/utils`
4. Potentiels endpoints API obsolètes dans `/app/api`

## Prochaines étapes

1. Effectuer une analyse statique complète avec des outils comme PyLint, ESLint et un analyseur de dépendances pour identifier précisément le code mort
2. Vérifier les références de code pour confirmer quels composants sont réellement utilisés
3. Mettre à jour les dépendances en supprimant celles qui ne sont plus nécessaires
4. Régénérer les fichiers JavaScript compilés pour éliminer les références CFF restantes
