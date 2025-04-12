# Checklist de déploiement en environnement de staging

> **✅ Liste de vérification ✅**  
> Document opérationnel pour guider l'équipe technique pendant le déploiement en environnement de staging.  
> À utiliser comme référence étape par étape lors de l'installation du système Technicia.
>
> Dernière mise à jour : 7 avril 2025  
> État : Document initial

## Instructions générales

1. Cochez chaque élément une fois terminé
2. Documentez tout problème rencontré dans la section "Notes et observations"
3. Pour toute difficulté majeure, référez-vous au plan de déploiement complet et contactez le responsable technique
4. Complétez toutes les sections dans l'ordre indiqué

## 1. Préparation de l'environnement

### 1.1 Vérification des prérequis système

- [ ] Serveur avec minimum 16 Go RAM, 8 cœurs CPU, 500 Go espace disque
- [ ] Système d'exploitation compatible (Windows Server 2022 ou Ubuntu 22.04 LTS)
- [ ] Droits administrateur disponibles
- [ ] Accès réseau configuré (ports 80, 443, 5432, 6379 ouverts)
- [ ] Pare-feu correctement configuré
- [ ] Certificats SSL/TLS préparés (auto-signés acceptables pour staging)

### 1.2 Installation des dépendances

- [ ] Docker et docker-compose installés (version 20.10+ / 2.10+)
- [ ] Git installé (version 2.30+)
- [ ] PowerShell 7+ (Windows) ou Bash 5+ (Linux)
- [ ] Python 3.10+ avec pip
- [ ] Node.js 18+ et npm 8+
- [ ] AWS CLI (si utilisation des services AWS)
- [ ] Azure CLI (si utilisation des services Azure)

### 1.3 Configuration réseau

- [ ] Nom de domaine staging configuré (staging.technicia.local)
- [ ] DNS correctement configuré
- [ ] Test de connectivité réussi
- [ ] Proxy configuré (si applicable)
- [ ] VPN configuré (si applicable)

## 2. Récupération du code et des ressources

- [ ] Clone du dépôt Git principal (`git clone https://github.com/technicia/ocr-system.git`)
- [ ] Checkout de la branche/tag stable (`git checkout v1.0-staging`)
- [ ] Vérification de l'intégrité du code (`git verify-commit HEAD`)
- [ ] Téléchargement des modèles OCR préentraînés
- [ ] Téléchargement des données de test
- [ ] Préparation des clés API pour services externes (si nécessaire)

## 3. Configuration initiale

### 3.1 Préparation des fichiers de configuration

- [ ] Copie des templates de configuration (`cp config.template.yaml config.yaml`)
- [ ] Configuration des connexions base de données
- [ ] Configuration des chemins de stockage
- [ ] Configuration des clés API pour services externes
- [ ] Configuration des paramètres OCR
- [ ] Définition des variables d'environnement (`cp .env.template .env`)
- [ ] Vérification des fichiers de configuration (pas de secrets en clair)

### 3.2 Configuration Docker

- [ ] Vérification du fichier docker-compose.yml
- [ ] Adaptation des volumes persistants selon l'environnement
- [ ] Configuration des limites de ressources
- [ ] Configuration du réseau Docker
- [ ] Vérification des images Docker (versions fixées, pas de 'latest')
- [ ] Préparation des volumes de données

## 4. Déploiement des services

### 4.1 Base de données

- [ ] Démarrage du container PostgreSQL (`docker-compose up -d postgres`)
- [ ] Vérification du démarrage réussi (`docker-compose logs postgres`)
- [ ] Initialisation du schéma de base de données (`./scripts/init_db.sh`)
- [ ] Vérification de l'accès à la base (`psql -h localhost -U technicia -d ocr_system`)
- [ ] Import des données initiales si nécessaire (`./scripts/import_data.sh`)
- [ ] Test de sauvegarde/restauration de la base de données

### 4.2 Services de cache et file d'attente

- [ ] Démarrage de Redis (`docker-compose up -d redis`)
- [ ] Vérification du démarrage réussi (`docker-compose logs redis`)
- [ ] Test de connectivité Redis (`redis-cli ping`)
- [ ] Configuration des paramètres Redis (mémoire, persistance)
- [ ] Démarrage de RabbitMQ si utilisé (`docker-compose up -d rabbitmq`)
- [ ] Vérification des queues RabbitMQ

### 4.3 Déploiement du backend

- [ ] Démarrage des services backend (`docker-compose up -d api processor websockets`)
- [ ] Vérification du démarrage réussi de tous les services
- [ ] Vérification des logs pour erreurs potentielles
- [ ] Test de l'API health check (`curl http://localhost:8000/api/health`)
- [ ] Test du service WebSocket
- [ ] Test du service de traitement OCR

### 4.4 Déploiement du frontend

- [ ] Build des assets frontend si nécessaire (`docker-compose run --rm frontend npm run build`)
- [ ] Démarrage du service frontend (`docker-compose up -d frontend`)
- [ ] Vérification de l'accès à l'interface web
- [ ] Test du responsive design (desktop, tablette, mobile)
- [ ] Vérification des performances frontend
- [ ] Validation des ressources statiques (images, CSS, JS)

### 4.5 Mise en place du proxy inverse

- [ ] Configuration Nginx ou Traefik
- [ ] Mise en place des certificats SSL/TLS
- [ ] Configuration des règles de redirection
- [ ] Test des URLs principales
- [ ] Vérification de la sécurité des headers HTTP
- [ ] Test du HTTPS

## 5. Configuration du monitoring

- [ ] Déploiement de Prometheus (`docker-compose up -d prometheus`)
- [ ] Configuration des exporters (node-exporter, postgres-exporter, etc.)
- [ ] Déploiement de Grafana (`docker-compose up -d grafana`)
- [ ] Import des dashboards prédéfinis
- [ ] Configuration des alertes
- [ ] Test d'envoi des alertes
- [ ] Configuration des logs centralisés (ELK ou Loki)
- [ ] Vérification de l'accès aux dashboards

## 6. Tests de validation post-déploiement

### 6.1 Tests fonctionnels

- [ ] Exécution du script de tests automatisés (`./scripts/test_staging_deployment.ps1`)
- [ ] Vérification du rapport de tests
- [ ] Test manuel de connexion (admin et utilisateur standard)
- [ ] Test manuel d'upload de document
- [ ] Test manuel de traitement OCR
- [ ] Test manuel du chatbot
- [ ] Test manuel de l'interface d'administration

### 6.2 Tests de performance

- [ ] Test de charge légère (10 utilisateurs simultanés)
- [ ] Vérification des temps de réponse
- [ ] Vérification de l'utilisation des ressources
- [ ] Test de récupération après pic de charge
- [ ] Vérification des métriques dans Grafana
- [ ] Test des limites de taille de fichiers

### 6.3 Tests de sécurité

- [ ] Scan de vulnérabilités basique
- [ ] Test d'authentification et permissions
- [ ] Vérification des headers de sécurité
- [ ] Test HTTPS et validation certificat
- [ ] Vérification des logs d'accès
- [ ] Test des mécanismes de rate limiting

### 6.4 Tests de sauvegarde et restauration

- [ ] Exécution d'une sauvegarde complète
- [ ] Vérification de l'intégrité de la sauvegarde
- [ ] Test de restauration dans un environnement séparé
- [ ] Vérification de la cohérence des données après restauration
- [ ] Documentation du temps nécessaire pour sauvegarde/restauration

## 7. Configuration finale

- [ ] Création des comptes utilisateurs pour les tests
- [ ] Configuration des permissions et rôles
- [ ] Ajustement des paramètres de performance si nécessaire
- [ ] Configuration des sauvegardes automatiques
- [ ] Documentation des URLs et endpoints disponibles
- [ ] Mise à jour de la documentation de l'environnement

## 8. Validation finale

- [ ] Tous les tests automatisés passent avec succès
- [ ] Tous les services sont opérationnels
- [ ] Le monitoring est fonctionnel
- [ ] L'interface utilisateur est accessible et fonctionnelle
- [ ] Les sauvegardes sont configurées et fonctionnelles
- [ ] La documentation est à jour
- [ ] Le rapport de déploiement est complété

## Notes et observations

Utilisez cette section pour documenter tout problème rencontré, solution appliquée ou observation particulière pendant le déploiement.

```
Date/heure | Étape | Problème/Observation | Solution appliquée
-----------|-------|---------------------|-------------------
           |       |                     |
           |       |                     |
           |       |                     |
```

## Approbation finale

| Rôle | Nom | Signature | Date |
|------|-----|-----------|------|
| Responsable technique |  |  |  |
| DevOps |  |  |  |
| QA |  |  |  |
| Chef de projet |  |  |  |

## Historique des déploiements en staging

| Version | Date | Responsable | Résultat | Commentaires |
|---------|------|-------------|----------|--------------|
| v1.0 |  |  |  |  |

---

Document maintenu par l'équipe technique Technicia.
