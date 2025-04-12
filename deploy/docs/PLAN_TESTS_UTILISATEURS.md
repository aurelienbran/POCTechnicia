# Plan de tests utilisateurs - Technicia OCR

> **Document interne** | Version 1.0  
> Date: 8 avril 2025  
> État: Document initial  
> Responsable: Équipe Technicia

## Objectifs

Ce document définit la méthodologie et le plan d'exécution des tests utilisateurs pour le système OCR Technicia après son déploiement en environnement de staging. Ces tests visent à :

1. Valider l'utilisabilité du système dans des conditions réelles d'utilisation
2. Identifier les problèmes d'expérience utilisateur avant le déploiement en production
3. Recueillir des retours détaillés sur les différentes fonctionnalités du système
4. Évaluer la satisfaction générale des utilisateurs et la disposition à adopter le système
5. Collecter des suggestions d'amélioration pour les futures versions

## Participants et planification

### Profils des testeurs

Nous solliciterons un panel de 10-15 testeurs représentatifs des futurs utilisateurs du système, répartis comme suit :

| Profil | Nombre | Justification | Critères de sélection |
|--------|--------|---------------|------------------------|
| Administrateurs système | 2-3 | Validation des fonctionnalités d'administration | Expérience en gestion de systèmes similaires |
| Utilisateurs techniques | 4-5 | Évaluation des fonctionnalités avancées d'OCR | Travail régulier avec des documents techniques complexes |
| Utilisateurs standards | 4-5 | Validation des fonctionnalités de base | Peu ou pas d'expérience avec des systèmes OCR |
| Responsables département | 1-2 | Perspective stratégique et organisationnelle | Pouvoir de décision sur l'adoption du système |

### Calendrier des sessions

Les tests se dérouleront sur une période de 5 jours ouvrables selon le calendrier suivant :

| Jour | Matin (9h-12h) | Après-midi (14h-17h) |
|------|----------------|----------------------|
| Jour 1 | Formation des observateurs | 2 administrateurs système |
| Jour 2 | 2 utilisateurs techniques | 2 utilisateurs techniques |
| Jour 3 | 2 utilisateurs standards | 2 utilisateurs standards |
| Jour 4 | 1 utilisateur technique + 1 responsable | 1 utilisateur standard + 1 administrateur |
| Jour 5 | 1 responsable département | Session de débrief et analyse préliminaire |

### Logistique

**Lieu des tests :** 
- Salle de réunion équipée A304 (bâtiment principal)
- Configuration double écran pour visualisation simultanée

**Équipement requis :**
- Postes de travail avec configuration standard de l'entreprise (3)
- Tablettes et smartphones pour tester la version mobile (2 de chaque)
- Dispositif d'enregistrement d'écran et audio
- Tableau blanc et post-it pour les sessions de débrief

**Personnel nécessaire :**
- 1 animateur de session (guide l'utilisateur)
- 1 observateur technique (note les problèmes techniques)
- 1 observateur UX (note les problèmes d'expérience utilisateur)

## Méthodologie de test

### Approche

Nous utiliserons une combinaison de :
- **Tests guidés par scénarios** : Les utilisateurs suivront des scénarios prédéfinis couvrant les principales fonctionnalités
- **Tests exploratoires** : Les utilisateurs exploreront librement le système après les scénarios guidés
- **Méthode de la pensée à voix haute** : Les utilisateurs verbaliseront leurs pensées pendant l'utilisation
- **Entretiens post-test** : Discussion structurée sur l'expérience globale

### Scénarios de test

Chaque session comprendra l'exécution des scénarios suivants, adaptés selon le profil de l'utilisateur :

#### Scénarios communs à tous les utilisateurs

1. **Authentification et prise en main**
   - Connexion au système
   - Exploration de l'interface principale
   - Configuration des préférences utilisateur

2. **Traitement de documents simples**
   - Upload d'un document texte simple
   - Suivi du processus OCR
   - Visualisation et interaction avec les résultats
   - Téléchargement et partage des résultats

3. **Recherche et consultation**
   - Recherche dans les documents traités
   - Filtrage des résultats par type et date
   - Consultation de l'historique des traitements

#### Scénarios pour les utilisateurs techniques

4. **Traitement de documents techniques complexes**
   - Upload de schémas techniques
   - Configuration des paramètres OCR avancés
   - Traitement de documents avec formules et tableaux
   - Évaluation de la précision des résultats

5. **Extraction de données structurées**
   - Identification et extraction de tableaux
   - Export vers différents formats (CSV, Excel)
   - Validation de l'intégrité des données extraites

#### Scénarios pour les administrateurs

6. **Gestion des utilisateurs**
   - Création de nouveaux comptes
   - Attribution de rôles et permissions
   - Configuration des groupes d'utilisateurs

7. **Configuration système et monitoring**
   - Modification des paramètres système
   - Consultation des tableaux de bord de performance
   - Configuration des règles de traitement par défaut
   - Gestion des tâches et de la file d'attente

### Métriques d'évaluation

Pour chaque scénario, nous mesurerons :

**Métriques quantitatives :**
- Taux de réussite (% de tâches complétées sans aide)
- Temps d'exécution (durée pour accomplir chaque tâche)
- Nombre d'erreurs commises
- Nombre de clics/étapes pour accomplir la tâche

**Métriques qualitatives :**
- Satisfaction utilisateur (score de 1 à 5)
- Facilité d'utilisation perçue (score de 1 à 5)
- Commentaires verbaux pendant l'exécution
- Expressions faciales et langage corporel

## Documentation et collecte des données

### Outils de collecte

- **Modèle de rapport standardisé** : `MODELE_RAPPORT_EVALUATION_UTILISATEUR.md` pour chaque session
- **Grille d'observation** : Document pour noter chronologiquement les actions et réactions
- **Enregistrements** : Capture d'écran et audio de chaque session (avec consentement)
- **Questionnaires** : Formulaires pré-test et post-test pour recueillir les impressions

### Structure du rapport de synthèse

Le rapport final de synthèse comportera les sections suivantes :

1. Résumé exécutif
2. Méthodologie appliquée
3. Profils des participants
4. Résultats par scénario et par profil utilisateur
5. Analyse des problèmes identifiés (classés par sévérité)
6. Recommandations d'amélioration
7. Évaluation globale de la disposition à déployer en production
8. Annexes (rapports individuels, données brutes)

## Procédure de correction et validation

### Traitement des problèmes

1. **Triage des problèmes** :
   - Priorité 1 : Bloquants pour le déploiement en production
   - Priorité 2 : Importants, à corriger avant déploiement complet
   - Priorité 3 : Mineurs, à corriger dans une version ultérieure

2. **Cycle de correction** :
   - Définition des actions correctives pour chaque problème
   - Mise en œuvre des corrections par l'équipe technique
   - Validation des corrections par l'équipe qualité

3. **Sessions de validation** :
   - Tests de régression pour vérifier que les corrections n'ont pas introduit de nouveaux problèmes
   - Session de validation avec un sous-ensemble des testeurs originaux

### Critères de validation pour passage en production

Le système sera considéré prêt pour un déploiement progressif en production lorsque :

- Tous les problèmes de priorité 1 sont résolus
- Au moins 90% des problèmes de priorité 2 sont résolus
- La satisfaction utilisateur moyenne est supérieure à 4/5
- Le taux de réussite moyen des scénarios est supérieur à 90%
- Aucun incident critique n'est survenu pendant 72 heures consécutives d'utilisation

## Annexes

### Documents de référence

- `CHECKLIST_DEPLOIEMENT_STAGING.md` : Checklist pour la préparation de l'environnement de test
- `MODELE_RAPPORT_EVALUATION_UTILISATEUR.md` : Modèle détaillé pour chaque session
- `PLAN_DEPLOIEMENT.md` : Plan global de déploiement du système

### Matériel pour les sessions de test

- **Documents de test standardisés** : Ensemble de documents représentatifs pour les scénarios de test
- **Guide de l'animateur** : Instructions détaillées pour conduire les sessions
- **Formulaires de consentement** : Documents légaux pour l'enregistrement des sessions

---

*Ce document fait partie du processus de déploiement en environnement de staging du système Technicia OCR.  
Il sera mis à jour en fonction des retours et de l'évolution du projet.*
