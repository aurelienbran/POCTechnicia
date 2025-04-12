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

## Tableau de Bord OCR

> **ℹ️ Note ℹ️**  
> Pour une documentation complète du tableau de bord OCR, consultez : [OCR_DASHBOARD_COMPLET.md](./OCR_DASHBOARD_COMPLET.md)

### Métriques OCR Disponibles
1. **Performance par Fournisseur**
   - Temps moyen de traitement par page
   - Taux de réussite
   - Qualité moyenne de reconnaissance
   - Nombre de documents traités

2. **Statistiques Globales**
   - Nombre total de tâches (par statut)
   - Répartition des types de documents
   - Volume de données traitées
   - Évolution des performances dans le temps

3. **Métriques de Qualité**
   - Score de confiance moyen
   - Taux d'erreurs détectées
   - Analyse comparative des fournisseurs

### Accès au Tableau de Bord
- Interface web : `http://localhost:8000/dashboard`
- WebSockets : `ws://localhost:8000/ws/dashboard`
- API REST : `http://localhost:8000/api/dashboard/metrics`

### Exportation des Données
Le tableau de bord permet l'exportation des métriques et statistiques au format :
- CSV pour l'analyse dans des outils tiers
- PDF pour les rapports
- JSON pour l'intégration avec d'autres systèmes

### Alertes et Notifications
Le système peut être configuré pour envoyer des alertes en cas de :
- Tâches en échec
- Dépassement de seuils de performance
- Files d'attente trop longues
- Erreurs récurrentes

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
