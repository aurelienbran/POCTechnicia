# Guide administrateur - Interface Technicia

> **🔧 Guide Administrateur 🔧**  
> Ce document présente les fonctionnalités d'administration de l'interface Technicia.  
> Il est destiné aux administrateurs système et gestionnaires de la plateforme.
>
> Dernière mise à jour : 7 avril 2025  
> État : Document initial

## 1. Introduction

Ce guide détaille les fonctionnalités d'administration disponibles dans l'interface Technicia. En tant qu'administrateur, vous disposez d'un accès privilégié permettant de gérer l'ensemble du système, les utilisateurs, les documents et les bases de connaissances. Ce document vous guidera à travers les différentes tâches d'administration et vous fournira les meilleures pratiques pour assurer le bon fonctionnement de la plateforme.

## 2. Tableau de bord administrateur

Le tableau de bord administrateur est votre point d'entrée principal pour la gestion du système Technicia.

### 2.1 Accéder au tableau de bord

1. Connectez-vous avec vos identifiants administrateur
2. Vous êtes automatiquement dirigé vers le tableau de bord administrateur
3. Vous pouvez également y accéder à tout moment en cliquant sur "Tableau de bord" dans le menu principal

### 2.2 Comprendre les métriques clés

Le tableau de bord affiche plusieurs sections de métriques importantes :

#### Métriques système
- **Utilisation des ressources** : CPU, mémoire, stockage utilisé
- **Temps de réponse** : Latence moyenne des différents services
- **Files d'attente** : État des files d'attente OCR et traitement
- **Erreurs système** : Alertes et erreurs récentes

#### Métriques d'utilisation
- **Documents traités** : Nombre de documents par période (jour/semaine/mois)
- **Activité utilisateurs** : Utilisateurs actifs et nombre de sessions
- **Utilisation OCR** : Répartition par fournisseur OCR
- **Requêtes chatbot** : Volume et taux de satisfaction

#### Performances OCR
- **Qualité d'extraction** : Score de confiance moyen
- **Temps de traitement** : Durée moyenne par page/document
- **Répartition des formats** : Types de documents traités
- **Zones problématiques** : Pourcentage de contenu à faible confiance

### 2.3 Filtrer et analyser les données

1. Utilisez les filtres en haut de chaque widget pour ajuster la période d'analyse
2. Cliquez sur "Exporter" pour télécharger les données en format CSV ou PDF
3. Survolez les graphiques pour voir les détails précis de chaque point de données
4. Cliquez sur les sections des graphiques pour accéder aux détails correspondants

### 2.4 Configurer le tableau de bord

1. Cliquez sur l'icône d'engrenage en haut à droite du tableau de bord
2. Sélectionnez "Personnaliser le tableau de bord"
3. Ajoutez, supprimez ou réorganisez les widgets selon vos besoins
4. Configurez les seuils d'alerte pour les métriques importantes
5. Enregistrez votre configuration personnalisée

## 3. Gestion des utilisateurs

L'interface d'administration vous permet de gérer l'ensemble des utilisateurs du système.

### 3.1 Vue d'ensemble des utilisateurs

1. Accédez à la section "Utilisateurs" depuis le menu principal
2. Consultez la liste complète des utilisateurs avec leur statut, rôle et dernière connexion
3. Utilisez les filtres pour affiner l'affichage par rôle, statut, etc.
4. Effectuez une recherche rapide par nom ou email

### 3.2 Créer un nouvel utilisateur

1. Dans la section "Utilisateurs", cliquez sur "Nouvel utilisateur"
2. Remplissez le formulaire avec les informations requises :
   - Email (obligatoire)
   - Nom et prénom
   - Rôle (Administrateur ou Utilisateur standard)
   - Permissions spécifiques (si nécessaire)
   - Groupes d'utilisateurs (si applicable)
3. Choisissez le mode d'invitation :
   - Génération automatique de mot de passe + email
   - Lien d'invitation par email
   - Configuration manuelle (pour les comptes de service)
4. Cliquez sur "Créer l'utilisateur"

> **Important :** Chaque compte administrateur créé a accès à toutes les fonctionnalités d'administration. Créez ces comptes avec précaution.

### 3.3 Modifier un utilisateur existant

1. Cliquez sur un utilisateur dans la liste pour accéder à son profil
2. Modifiez les informations selon les besoins
3. Pour changer le rôle, utilisez le sélecteur de rôle
4. Pour ajuster les permissions spécifiques, utilisez l'onglet "Permissions"
5. Cliquez sur "Enregistrer les modifications"

### 3.4 Gérer les permissions avancées

Pour les besoins spécifiques, vous pouvez créer des profils de permission personnalisés :

1. Dans la section "Utilisateurs", accédez à l'onglet "Permissions"
2. Cliquez sur "Nouveau profil de permissions"
3. Donnez un nom au profil
4. Configurez les permissions détaillées pour chaque module :
   - Documents (lecture, écriture, suppression, partage)
   - OCR (configuration, exécution, gestion des fournisseurs)
   - Bases de connaissances (création, modification, indexation)
   - Chatbot (configuration, analyse des conversations)
   - Statistiques (lecture, export)
5. Enregistrez le profil
6. Attribuez ce profil aux utilisateurs concernés

### 3.5 Gestion des groupes d'utilisateurs

Les groupes permettent d'organiser les utilisateurs et de gérer les accès collectivement :

1. Accédez à l'onglet "Groupes" dans la section "Utilisateurs"
2. Cliquez sur "Nouveau groupe"
3. Donnez un nom et une description au groupe
4. Ajoutez des utilisateurs au groupe
5. Configurez les permissions et accès partagés pour le groupe
6. Enregistrez le groupe

### 3.6 Audit des activités utilisateurs

Pour surveiller les actions des utilisateurs sur le système :

1. Accédez à l'onglet "Audit" dans la section "Utilisateurs"
2. Consultez le journal des activités utilisateurs
3. Filtrez par type d'action, utilisateur, période, etc.
4. Exportez les journaux d'audit pour documentation
5. Configurez les alertes pour les actions sensibles

## 4. Gestion avancée des documents

En tant qu'administrateur, vous disposez d'outils avancés pour gérer les documents dans le système.

### 4.1 Configuration du processus d'upload

1. Accédez à "Paramètres" > "Documents" > "Configuration upload"
2. Définissez les paramètres par défaut pour l'upload :
   - Taille maximale de fichier
   - Types de fichiers autorisés
   - Paramètres OCR par défaut
   - Destinations de stockage
3. Configurez les règles de validation des documents
4. Définissez les workflows post-upload (notification, indexation, etc.)
5. Enregistrez la configuration

### 4.2 Orchestration des processeurs OCR

Pour optimiser le traitement OCR selon les types de documents :

1. Accédez à "Paramètres" > "OCR" > "Orchestration"
2. Configurez les règles d'orchestration :
   - Par type de document (schéma, formule, texte dense, etc.)
   - Par taille de fichier
   - Par qualité d'image
3. Définissez la séquence des processeurs pour chaque règle
4. Configurez les stratégies de fallback en cas d'échec
5. Testez les règles avec l'outil de simulation

### 4.3 Gestion des métadonnées de documents

Pour enrichir les documents avec des métadonnées structurées :

1. Accédez à "Paramètres" > "Documents" > "Schémas de métadonnées"
2. Créez ou modifiez des schémas de métadonnées
3. Définissez les champs obligatoires et optionnels
4. Configurez l'extraction automatique de métadonnées
5. Appliquez les schémas aux collections de documents

### 4.4 Archive et suppression des documents

Pour gérer le cycle de vie des documents :

1. Accédez à la section "Documents" > "Archive"
2. Configurez les règles d'archivage automatique :
   - Par ancienneté
   - Par utilisation (documents non consultés)
   - Par statut (traités, validés, etc.)
3. Programmez les tâches de purge pour les documents archivés
4. Configurez les règles de sauvegarde avant suppression
5. Consultez les logs d'archivage et de suppression

## 5. Configuration avancée des bases de connaissances

Les bases de connaissances sont essentielles pour le bon fonctionnement du chatbot.

### 5.1 Création d'une architecture de bases optimale

1. Accédez à la section "Bases de connaissances"
2. Planifiez une structure de bases selon les domaines techniques :
   - Créez des bases spécialisées par domaine
   - Utilisez des bases transversales pour les connaissances communes
3. Configurez la priorité des bases lors des requêtes multi-bases
4. Déterminez les stratégies de chunking appropriées pour chaque base

### 5.2 Configuration avancée de l'indexation

1. Accédez à "Paramètres" > "Bases de connaissances" > "Indexation"
2. Configurez les paramètres avancés :
   - Taille des chunks et chevauchement
   - Algorithme d'embedding
   - Paramètres de similarité vectorielle
   - Préprocesseurs de texte spécialisés
3. Créez des profiles d'indexation pour différents types de contenu
4. Configurez les règles d'extraction d'entités nommées
5. Testez différentes configurations avec l'outil de benchmark

### 5.3 Optimisation des requêtes chatbot

1. Accédez à "Paramètres" > "Chatbot" > "Configuration des requêtes"
2. Configurez les paramètres d'interrogation :
   - Nombre de chunks à récupérer
   - Seuil de pertinence
   - Stratégie de ranking et reranking
   - Gestion du contexte conversationnel
3. Définissez des règles pour les requêtes spécialisées (techniques, mathématiques, etc.)
4. Configurez des templates de réponse pour certains types de questions
5. Testez les performances avec l'outil d'évaluation de requêtes

### 5.4 Surveillance et maintenance des bases

1. Accédez à l'onglet "Diagnostic" dans la section "Bases de connaissances"
2. Consultez les métriques de santé des bases :
   - Taille et distribution des chunks
   - Qualité des embeddings
   - Taux de hit/miss lors des requêtes
   - Zones de connaissance manquantes
3. Identifiez les problèmes potentiels
4. Utilisez l'outil de reindexation ciblée pour résoudre les problèmes
5. Programmez des maintenances régulières

## 6. Surveillance du système et résolution des problèmes

### 6.1 Surveillance en temps réel

1. Accédez à la section "Surveillance" depuis le menu principal
2. Consultez le tableau de bord de surveillance en temps réel :
   - État des services
   - Utilisation des ressources
   - Files d'attente
   - Erreurs actives
3. Configurez les vues spécifiques selon vos besoins de monitoring
4. Réglez les seuils d'alerte pour chaque métrique

### 6.2 Gestion des alertes

1. Accédez à "Paramètres" > "Système" > "Alertes"
2. Configurez les canaux de notification :
   - Email
   - Webhook vers systèmes externes
   - SMS (si configuré)
   - Notifications push dans l'interface
3. Définissez les règles d'alerte pour différentes situations
4. Configurez l'escalade des alertes critiques
5. Testez le système d'alerte avec la fonction de test

### 6.3 Journaux système (logs)

1. Accédez à la section "Journaux" depuis le menu principal
2. Consultez les différents journaux disponibles :
   - Logs d'application
   - Logs OCR
   - Logs d'authentification
   - Logs d'erreurs
3. Utilisez les filtres pour affiner l'affichage
4. Recherchez des événements spécifiques avec la fonction de recherche
5. Exportez les logs pour analyse externe

### 6.4 Diagnostics et résolution des problèmes courants

#### Problèmes d'OCR
1. Accédez à "Diagnostics" > "OCR"
2. Utilisez l'outil de test OCR pour isoler les problèmes
3. Vérifiez la configuration des fournisseurs OCR
4. Consultez les journaux spécifiques aux tâches OCR problématiques
5. Suivez les recommandations de l'assistant de résolution

#### Problèmes d'indexation
1. Accédez à "Diagnostics" > "Indexation"
2. Vérifiez l'état des services d'indexation
3. Consultez les erreurs d'indexation détaillées
4. Utilisez l'outil de réindexation pour les documents problématiques
5. Vérifiez les paramètres de chunking et d'embedding

#### Problèmes de performance
1. Accédez à "Diagnostics" > "Performance"
2. Identifiez les goulots d'étranglement avec l'outil de profilage
3. Vérifiez l'utilisation des ressources système
4. Consultez les temps de réponse des différents services
5. Appliquez les recommandations d'optimisation suggérées

## 7. Sauvegarde et restauration

### 7.1 Configuration des sauvegardes

1. Accédez à "Paramètres" > "Système" > "Sauvegarde & Restauration"
2. Configurez les paramètres de sauvegarde :
   - Fréquence des sauvegardes automatiques
   - Types de données à sauvegarder
   - Destinations de stockage (local, réseau, cloud)
   - Politique de rétention
3. Définissez des sauvegardes différentielles ou complètes
4. Configurez la compression et le chiffrement des sauvegardes
5. Testez la configuration avec une sauvegarde manuelle

### 7.2 Gestion des sauvegardes

1. Accédez à l'onglet "Sauvegardes" dans la section "Sauvegarde & Restauration"
2. Consultez la liste des sauvegardes disponibles
3. Vérifiez l'état et l'intégrité des sauvegardes
4. Téléchargez ou exportez des sauvegardes si nécessaire
5. Supprimez les sauvegardes obsolètes manuellement

### 7.3 Restauration du système

En cas de besoin de restauration :

1. Accédez à l'onglet "Restauration" dans la section "Sauvegarde & Restauration"
2. Sélectionnez la sauvegarde à restaurer
3. Choisissez le type de restauration :
   - Restauration complète
   - Restauration sélective (documents, utilisateurs, configurations)
4. Confirmez l'opération de restauration
5. Suivez la progression de la restauration
6. Vérifiez l'intégrité du système après restauration

> **Attention :** La restauration complète remplace toutes les données actuelles. Assurez-vous de comprendre l'impact avant de procéder.

## 8. Personnalisation de l'interface

### 8.1 Personnalisation de la marque

1. Accédez à "Paramètres" > "Interface" > "Personnalisation"
2. Configurez les éléments de marque :
   - Logo (header et favicon)
   - Couleurs principales et secondaires
   - Police de caractères
   - Textes d'accueil et de pied de page
3. Prévisualisez les modifications en temps réel
4. Appliquez les changements lorsque vous êtes satisfait

### 8.2 Configuration des options d'interface

1. Accédez à "Paramètres" > "Interface" > "Options"
2. Configurez les options générales :
   - Page d'accueil par défaut
   - Timeout de session
   - Options d'affichage (thème clair/sombre par défaut)
   - Paramètres de notification
3. Définissez les options spécifiques aux modules
4. Configurez les raccourcis clavier personnalisés
5. Enregistrez la configuration

### 8.3 Gestion des extensions et widgets

1. Accédez à "Paramètres" > "Interface" > "Extensions"
2. Activez ou désactivez les extensions disponibles
3. Configurez les widgets pour le tableau de bord
4. Personnalisez les paramètres de chaque extension
5. Déterminez les extensions disponibles par rôle utilisateur

## 9. Déploiement et mise à jour

### 9.1 Stratégie de déploiement

Pour déployer le frontend sur de nouveaux environnements :

1. Accédez à "Système" > "Déploiement"
2. Consultez la documentation de déploiement détaillée
3. Suivez le processus recommandé :
   - Configuration de l'environnement
   - Installation des dépendances
   - Déploiement des fichiers frontend
   - Configuration des services backend
   - Tests de validation

### 9.2 Gestion des mises à jour

Lorsqu'une nouvelle version est disponible :

1. Accédez à "Système" > "Mises à jour"
2. Consultez les notes de version pour comprendre les changements
3. Planifiez la mise à jour selon l'impact estimé
4. Suivez le processus de mise à jour recommandé :
   - Sauvegarde préalable
   - Application de la mise à jour
   - Tests post-mise à jour
   - Validation de fonctionnement
5. En cas de problème, utilisez l'option de restauration

### 9.3 Environnements multiples

Si vous gérez plusieurs environnements (développement, test, production) :

1. Accédez à "Système" > "Environnements"
2. Configurez les paramètres spécifiques à chaque environnement
3. Utilisez l'outil de synchronisation pour aligner les configurations
4. Définissez les stratégies de promotion entre environnements
5. Configurez les indicateurs visuels pour identifier facilement l'environnement actif

## 10. Meilleures pratiques d'administration

### 10.1 Optimisation des performances

- Surveillez régulièrement les métriques de performance
- Configurez des sauvegardes fréquentes mais en dehors des heures de pointe
- Utilisez l'outil d'analyse des performances pour identifier les goulots d'étranglement
- Optimisez les règles d'orchestration OCR selon les types de documents
- Configurez des limites de ressources appropriées pour éviter la surcharge

### 10.2 Sécurité

- Changez régulièrement les mots de passe administrateur
- Activez l'authentification à deux facteurs pour tous les comptes administrateur
- Révisez régulièrement les permissions utilisateurs
- Configurez les verrouillages de compte après tentatives échouées
- Surveillez les journaux d'authentification pour détecter les activités suspectes
- Définissez des politiques de complexité des mots de passe

### 10.3 Maintenance système

- Planifiez des maintenances régulières (hebdomadaires/mensuelles)
- Vérifiez régulièrement l'intégrité des bases de connaissances
- Testez périodiquement le processus de sauvegarde/restauration
- Nettoyez les fichiers temporaires et documents obsolètes
- Optimisez les index de base de données régulièrement

### 10.4 Formation et support

- Formez les nouveaux administrateurs aux particularités du système
- Documentez les procédures spécifiques à votre déploiement
- Créez une base de connaissances interne pour les problèmes récurrents
- Établissez un processus clair d'escalade des incidents
- Maintenez à jour la documentation utilisateur

## 11. Annexes

### 11.1 Liste des permissions système

| Code permission | Description | Niveau recommandé |
|----------------|-------------|-------------------|
| `admin.full` | Accès complet à toutes les fonctionnalités | Admin uniquement |
| `admin.users` | Gestion des utilisateurs | Admin |
| `admin.system` | Configuration système | Admin |
| `documents.create` | Création de documents | Admin/Utilisateur avancé |
| `documents.delete` | Suppression de documents | Admin uniquement |
| `documents.share` | Partage de documents | Admin/Utilisateur avancé |
| `kb.create` | Création de bases de connaissances | Admin uniquement |
| `kb.update` | Mise à jour des bases existantes | Admin/Utilisateur avancé |
| `ocr.configure` | Configuration des paramètres OCR | Admin uniquement |
| `chat.history.view` | Consultation historique des conversations | Admin |
| `chat.history.delete` | Suppression conversations | Admin uniquement |
| `stats.view` | Consultation des statistiques | Admin/Utilisateur avancé |
| `system.logs` | Accès aux journaux système | Admin uniquement |

### 11.2 Variables d'environnement

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `FRONTEND_URL` | URL de base du frontend | http://localhost:3000 |
| `API_URL` | URL de l'API backend | http://localhost:8000 |
| `WS_URL` | URL du service WebSocket | ws://localhost:8000/ws |
| `SESSION_TIMEOUT` | Timeout de session (ms) | 3600000 |
| `DEFAULT_THEME` | Thème par défaut (light/dark) | light |
| `LOG_LEVEL` | Niveau de journalisation | info |
| `ENABLE_ANALYTICS` | Activer les analytics d'usage | true |

### 11.3 Codes d'erreur communs

| Code | Message | Cause probable | Résolution |
|------|---------|----------------|------------|
| E1001 | Authentication failed | Identifiants invalides | Vérifier les identifiants ou réinitialiser le mot de passe |
| E2001 | Document processing failed | Erreur OCR | Vérifier le format du document et les logs OCR |
| E3001 | Knowledge base index error | Problème d'indexation | Consulter les logs d'indexation et réessayer |
| E4001 | API connection error | Serveur backend inaccessible | Vérifier la connectivité et l'état des services |
| E5001 | WebSocket connection lost | Problème réseau | Vérifier la connexion et les pare-feu |

### 11.4 Ressources et documentation complémentaire

- [Architecture technique complète](../technique/ARCHITECTURE_TECHNIQUE_COMPLETE.md)
- [Architecture frontend détaillée](../technique/ARCHITECTURE_FRONTEND.md)
- [Documentation API](../api/API_DOCUMENTATION.md)
- [Procédures de backup et restauration](../technique/BACKUP_RESTORE_PROCEDURES.md)
- [Documentation des fournisseurs OCR](../technique/OCR_HYBRIDE.md)

---

Pour toute question ou suggestion concernant ce guide, veuillez contacter l'équipe technique Technicia.
