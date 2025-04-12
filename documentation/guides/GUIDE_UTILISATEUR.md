# Guide Utilisateur - Système OCR Technicia

**Version :** 1.0  
**Date :** 2 avril 2025  
**Public cible :** Utilisateurs finaux du système OCR Technicia

## Table des matières

1. [Introduction](#1-introduction)
2. [Prise en main rapide](#2-prise-en-main-rapide)
3. [Fonctionnalités principales](#3-fonctionnalités-principales)
4. [Interface utilisateur](#4-interface-utilisateur)
5. [Traitement des documents](#5-traitement-des-documents)
6. [Suivi des tâches](#6-suivi-des-tâches)
7. [Résolution des problèmes courants](#7-résolution-des-problèmes-courants)
8. [Assistance et support](#8-assistance-et-support)

## 1. Introduction

Le système OCR Technicia est une solution avancée de reconnaissance optique de caractères spécialement conçue pour traiter des documents techniques complexes. Il permet d'extraire du texte, des formules mathématiques, des schémas et des tableaux à partir de différents types de documents (PDF, images, documents scannés).

Ce guide vous aidera à prendre en main l'application et à exploiter pleinement ses fonctionnalités.

## 2. Prise en main rapide

### Prérequis
- Un navigateur web moderne (Chrome, Firefox, Edge, Safari)
- Une connexion internet stable
- Un compte utilisateur valide sur le système OCR Technicia

### Première connexion
1. Accédez à l'interface web à l'adresse : `https://[adresse-du-serveur]/ocr/dashboard`
2. Connectez-vous avec vos identifiants fournis par votre administrateur
3. Lors de la première connexion, vous serez invité à changer votre mot de passe

### Soumettre votre premier document
1. Dans le tableau de bord, cliquez sur le bouton `+ Nouveau traitement` en haut à droite
2. Sélectionnez le fichier à traiter depuis votre ordinateur
3. Choisissez le type de traitement souhaité dans le menu déroulant
4. Cliquez sur `Démarrer le traitement`
5. Suivez l'avancement du traitement dans la section `Tâches en cours`

## 3. Fonctionnalités principales

### Reconnaissance de documents techniques
- Extraction de texte standard (OCR classique)
- Reconnaissance de formules mathématiques
- Détection et extraction de schémas techniques
- Extraction structurée de tableaux
- Préservation des relations entre les différents éléments du document

### Traitement par lots
- Soumission simultanée de plusieurs documents
- Configuration de paramètres de traitement par lot
- Planification de traitements récurrents

### Suivi et gestion
- Tableau de bord en temps réel des traitements
- Notifications d'achèvement des tâches
- Historique des traitements
- Filtrage et recherche dans les tâches
- Exportation des résultats dans différents formats

## 4. Interface utilisateur

### Tableau de bord principal

![Tableau de bord OCR](../images/ocr_dashboard_overview.png)

Le tableau de bord principal est divisé en plusieurs sections :

1. **Barre de navigation supérieure**
   - Menu principal de l'application
   - Bouton de déconnexion
   - Indicateur de notifications
   - Accès aux paramètres utilisateur

2. **Section "Tâches en cours"**
   - Liste des traitements actuellement en cours
   - Indicateur de progression en temps réel
   - Estimation du temps restant
   - Boutons d'action (Pause, Annuler)

3. **Section "Tâches terminées"**
   - Liste des traitements récemment terminés
   - Statut final (Réussi, Échec, Attention)
   - Boutons d'action (Télécharger, Visualiser, Retraiter)

4. **Section "Statistiques"**
   - Métriques de performance globale
   - Graphiques de répartition des types de documents
   - Tendances d'utilisation

### Écran de détail d'une tâche

Lorsque vous cliquez sur une tâche, vous accédez à l'écran de détail qui présente :

- Informations générales sur le document traité
- Aperçu du résultat de l'extraction
- Métriques de qualité de l'OCR
- Liste des actions possibles sur le document
- Historique des traitements pour ce document

## 5. Traitement des documents

### Types de documents supportés
- PDF (numérique et scanné)
- Images (JPG, PNG, TIFF)
- Documents Microsoft Office (DOCX, XLSX, PPTX)
- Formats d'image spécialisés (DJVU, WebP)

### Modes de traitement

#### Mode standard
Traitement OCR classique adapté aux documents principalement textuels. Ce mode est idéal pour les documents administratifs, rapports ou articles.

#### Mode technique
Spécialement conçu pour les documents techniques contenant des formules mathématiques, schémas et tableaux complexes. Ce mode active les processeurs spécialisés.

#### Mode haute précision
Utilise des algorithmes plus avancés et plusieurs passes de traitement pour maximiser la qualité d'extraction. Ce mode est plus lent mais produit des résultats de meilleure qualité pour les documents difficiles.

### Options avancées

Lors de la soumission d'un document, vous pouvez configurer plusieurs options avancées :

- **Langue principale** : Spécifiez la langue principale du document pour améliorer la précision
- **Prétraitement** : Options de prétraitement d'image (redressement, suppression du bruit, etc.)
- **Niveau de validation** : Détermine le niveau de rigueur pour la validation des résultats
- **Extraction spécialisée** : Active/désactive l'extraction des formules, schémas ou tableaux
- **Priorité** : Définit la priorité de traitement pour cette tâche

## 6. Suivi des tâches

### Statuts des tâches

- **En attente** : La tâche est dans la file d'attente
- **En cours** : Le traitement est en cours
- **Terminé avec succès** : Traitement réussi sans problème détecté
- **Terminé avec avertissements** : Traitement réussi mais avec des zones de faible confiance
- **Échec** : Le traitement a échoué
- **Annulé** : La tâche a été annulée par l'utilisateur

### Notifications

Le système peut vous notifier de l'achèvement des tâches par différents moyens :
- Notifications dans l'interface
- Notifications par e-mail (configurable dans les paramètres)
- Notifications par WebSocket pour les mises à jour en temps réel

### Gestion des tâches à problèmes

Pour les documents dont le traitement a échoué ou présentant des zones de faible confiance :

1. Accédez au détail de la tâche
2. Consultez les zones problématiques surlignées en rouge
3. Choisissez une action :
   - **Retraiter** : Lance un nouveau traitement avec des paramètres ajustés
   - **Édition manuelle** : Ouvre l'interface d'édition pour corriger manuellement les erreurs
   - **Ignorer** : Accepte les résultats tels quels

## 7. Résolution des problèmes courants

### Document mal reconnu

Problème : Le texte extrait contient de nombreuses erreurs.

Solutions :
- Assurez-vous que le document est bien orienté
- Essayez le mode "Haute précision"
- Vérifiez que la langue principale est correctement spécifiée
- Pour les documents scannés, assurez-vous que la résolution est d'au moins 300 DPI

### Formules mathématiques non détectées

Problème : Les formules sont traitées comme du texte ou des images.

Solutions :
- Activez l'option "Extraction spécialisée" lors de la soumission
- Sélectionnez le mode "Technique"
- Vérifiez que les formules sont suffisamment lisibles dans le document source
- Si les formules sont manuscrites, précisez-le dans les options avancées

### Tâche bloquée en cours de traitement

Problème : Une tâche reste en statut "En cours" pendant une durée anormalement longue.

Solutions :
- Actualisez la page du tableau de bord
- Annulez la tâche et soumettez-la à nouveau
- Divisez les documents volumineux en fichiers plus petits
- Contactez votre administrateur système

## 8. Assistance et support

### Documentation supplémentaire
- [FAQ](../faq/FAQ_UTILISATEUR.md)
- [Tutoriels vidéo](https://video.technicia.com/tutorials)
- [Exemples de cas d'usage](../exemples/CAS_USAGE.md)

### Support technique
- E-mail de support : support@technicia.com
- Portail de tickets : https://support.technicia.com
- Heures d'assistance : 9h-18h (UTC+1), du lundi au vendredi

### Formation
Des sessions de formation en ligne sont régulièrement organisées. Consultez le calendrier dans la section "Formation" de l'interface ou contactez votre administrateur système.
