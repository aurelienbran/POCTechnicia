# Monitoring et Métriques

## Configuration des Logs

### Structure des Logs
```
logs/
├── app.log        # Logs applicatifs
├── error.log      # Erreurs critiques
├── access.log     # Logs d'accès HTTP
└── websocket.log  # Logs WebSocket
```

### Niveaux de Log
- **DEBUG** : Informations détaillées pour le développement
- **INFO** : Événements normaux
- **WARNING** : Situations anormales mais non critiques
- **ERROR** : Erreurs nécessitant une attention
- **CRITICAL** : Erreurs bloquantes

### Rotation des Logs
- Rotation quotidienne
- Compression des anciens logs
- Conservation pendant 30 jours

## Métriques de Performance

### Métriques Clés
1. **Temps de Réponse**
   - Génération des embeddings
   - Recherche vectorielle
   - Génération de réponse LLM
   - Questions de suivi

2. **Utilisation des Ressources**
   - CPU par composant
   - Mémoire par composant
   - Stockage Qdrant
   - Taille des logs

3. **Qualité du Service**
   - Taux de succès des requêtes
   - Temps de réponse moyen
   - Nombre de retries
   - Score de pertinence

### Dashboards
- Grafana pour la visualisation
- Prometheus pour la collecte
- Alerting configurable

## Diagnostic

### Outils de Diagnostic
1. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Status Qdrant**
   ```bash
   curl http://localhost:6333/collections/documents
   ```

3. **Logs en Temps Réel**
   ```bash
   tail -f logs/app.log
   ```

### Commandes Utiles
```bash
# Vérifier l'état des composants
python scripts/check_status.py

# Générer un rapport de performance
python scripts/generate_report.py

# Nettoyer les logs anciens
python scripts/cleanup_logs.py
```

## Paramètres Actuels (25/02/2025)

### Recherche Sémantique
```python
# VectorStore.similarity_search
k = 6                    # Nombre de documents retournés
score_threshold = 0.5    # Seuil minimum de similarité
```

### Génération de Réponses
```python
# LLMInterface._call_claude_technical
model = "claude-3-sonnet-20240229"
max_tokens = 2000
temperature = 0.5       # Équilibre précision/créativité
```

### Extraction des Sources
```python
# RAGEngine._extract_sources
score_threshold = 0.6   # Seuil minimum pour inclusion des sources
metadata = ["source", "page", "section"]  # Informations incluses
```

## Métriques à Surveiller

### Performance
1. Temps de réponse
   - Recherche sémantique : < 1s
   - Génération de réponse : < 3s
   - Total : < 5s

2. Qualité des résultats
   - Score moyen de similarité
   - Taux d'utilisation des sources
   - Complétude des réponses

### Ressources
1. Mémoire
   - Usage des embeddings
   - Cache de documents

2. CPU/GPU
   - Charge lors des recherches
   - Charge lors de la génération

## Alertes et Seuils

### Critiques
- Temps de réponse > 10s
- Score de similarité < 0.4
- Échec de génération de réponse

### Avertissements
- Temps de réponse > 5s
- Moins de 3 sources pertinentes
- Score moyen < 0.5

## Logs
- Niveau INFO : Opérations normales
- Niveau WARNING : Performances dégradées
- Niveau ERROR : Échecs et erreurs
- Rotation quotidienne des logs

## Alertes

### Configuration des Alertes
1. **Seuils Critiques**
   - Temps de réponse > 5s
   - Utilisation CPU > 80%
   - Mémoire > 90%
   - Erreurs > 5/minute

2. **Canaux de Notification**
   - Email
   - Slack
   - SMS (urgences)

### Actions Automatiques
- Redémarrage des services
- Nettoyage des caches
- Rotation des logs
- Sauvegarde d'urgence
