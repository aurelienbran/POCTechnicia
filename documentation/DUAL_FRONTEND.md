# Implémentation du Double Frontend

Ce document explique comment le système de double frontend a été implémenté, permettant d'accéder à la fois au frontend original et au nouveau frontend React pendant la phase de transition.

## Architecture

L'architecture mise en place permet de faire fonctionner deux frontends simultanément :

1. **Frontend Original** : Servi directement par FastAPI via Jinja2Templates sur le port 8000
2. **Nouveau Frontend React** : Exécuté via Vite sur le port 3001 en développement

### Diagramme d'architecture simplifié

```
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  Frontend React │     │  FastAPI Backend│
│  (Port 3001)    │     │  (Port 8000)    │
│                 │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │  API Calls (/api/...) │
         └───────────────────────┘
```

## Composants

### 1. Configuration CORS du Backend

Le backend FastAPI est configuré pour accepter les requêtes CORS depuis le frontend React. Les origines autorisées incluent `http://localhost:3001` pour permettre les appels API depuis cette origine.

### 2. Configuration du serveur Vite

Le serveur de développement Vite est configuré pour s'exécuter sur le port 3001 et pour proxifier les requêtes API vers le backend FastAPI sur le port 8000. Cette configuration est définie dans `vite.config.ts` :

```typescript
// Extrait de vite.config.ts
server: {
  port: 3001,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
    },
    '/static': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
    }
  }
}
```

### 3. Scripts utilitaires

Plusieurs scripts batch ont été créés pour faciliter le développement et le déploiement :

- `scripts/start_dual_frontend.bat` : Démarre les deux frontends simultanément
- `scripts/build_frontend.bat` : Construit le frontend React et copie les fichiers dans le dossier statique de FastAPI
- `scripts/setup_frontend.bat` : Installe les dépendances du frontend React

## Utilisation

### Développement

Pour développer avec les deux frontends en parallèle :

1. Exécutez `scripts/start_dual_frontend.bat`
2. Accédez au frontend original à l'adresse http://localhost:8000
3. Accédez au nouveau frontend React à l'adresse http://localhost:3001

### Accès aux API

Les deux frontends utilisent les mêmes API REST :
- Les endpoints API sont accessibles via `/api/v1/...`
- Le frontend React est configuré avec un proxy pour rediriger les appels API automatiquement

### Déploiement en production

Pour déployer le nouveau frontend en production :

1. Exécutez `scripts/build_frontend.bat` pour construire le frontend React
2. Les fichiers générés seront copiés dans `app/static/new`
3. Le backend FastAPI servira ces fichiers via la route `/new`

## Configuration

### Configuration CORS

Les origines autorisées dans `app/config.py` incluent :
```python
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:8000",
    "http://localhost:3001",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3001",
]
```

### Mode Mock API

Le frontend React peut fonctionner avec des données de test (mock data) ou avec l'API réelle :
```typescript
// Dans App.tsx
// Pour utiliser l'API réelle, définir à false
const useMockApi = false; // import.meta.env.DEV;
```

## Dépannage

### Problèmes courants

1. **Page blanche sur le Frontend React**
   - Vérifier que le serveur Vite est bien démarré sur le port 3001
   - Désactiver le mode "useMockApi" dans `src/App.tsx` pour utiliser l'API réelle
   - Vérifier les erreurs dans la console du navigateur

2. **Statistiques incorrectes**
   - Les statistiques affichées peuvent montrer 0 documents indexés même si des chunks vectorisés sont présents
   - C'est dû à une désynchronisation entre les compteurs en mémoire et la base vectorielle
   - L'indicateur "Documents disponibles" permet de voir si la base contient des données

3. **Erreurs CORS** 
   - Vérifiez que les origines autorisées dans `app/config.py` incluent à la fois `http://localhost:8000` et `http://localhost:3001`

### Logs

Les logs du backend FastAPI sont disponibles dans le dossier `logs/`. Les logs du frontend React sont affichés dans la console du navigateur.
