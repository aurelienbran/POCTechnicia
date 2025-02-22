# Tests de Performance

Ce module permet de mesurer les performances du système RAG en conditions réelles.

## Métriques mesurées

1. **Upload et Traitement des PDF**
   - Temps de traitement total
   - Consommation mémoire
   - Nombre de chunks traités
   - Taille des fichiers

2. **Performances des Requêtes**
   - Temps de réponse moyen
   - Temps min/max
   - Utilisation mémoire

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

1. Assurez-vous que le serveur est en cours d'exécution
2. Placez vos fichiers PDF de test dans le dossier approprié
3. Mettez à jour les chemins des fichiers dans `test_performance.py`
4. Exécutez les tests :

```bash
python test_performance.py
```

## Rapports

Les rapports sont générés dans le dossier `performance_reports` et comprennent :
- Un rapport HTML détaillé
- Des graphiques de performance
- Les données brutes au format CSV

## Critères de Performance

Selon le cahier des charges :
- Temps de réponse cible : < 5s
- Utilisation mémoire max : 1GB
- Taille max PDF : 150 MB
