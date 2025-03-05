# Installation Portable du Projet POC TECHNICIA

Ce document détaille la création et l'utilisation de l'installateur portable pour le projet POC TECHNICIA, permettant de déployer l'application sur n'importe quel PC sans installation complexe.

## Objectif

L'installateur portable permet de :
- Exécuter l'application à partir d'une clé USB ou d'un dossier partagé
- Distribuer facilement l'application à des partenaires ou testeurs
- Configurer automatiquement toutes les dépendances
- Démarrer tous les services avec un minimum d'intervention utilisateur

## Création de l'Installateur Portable

### Prérequis
- 7-Zip installé sur le PC de développement
- Module 7zSD.sfx pour créer l'exécutable auto-extractible
- Au moins 1 Go d'espace disque disponible

### Étape 1: Générer la Structure de l'Installateur
```bash
cd scripts/maintenance
portable_installer.bat
```

> **Note importante**: Ce script crée uniquement la structure de l'installateur. Les scripts de configuration (`setup_portable.bat`, `start_portable.bat`, et `clean_qdrant_portable.bat`) seront générés dans le dossier d'installation lorsque l'utilisateur exécutera l'installateur.

Ce script va créer une structure de dossiers comme suit :
```
POCTechnicia_Installer/
├── project_source/       # Code source du projet
├── portable_deps/        # Dépendances portables
│   ├── python_portable/  # Python portable 
│   ├── nodejs_portable/  # Node.js portable
│   └── qdrant_portable/  # Qdrant portable
├── install.bat           # Script d'installation principal
├── README.txt            # Instructions pour l'utilisateur
├── config.txt            # Configuration 7-Zip SFX
└── GUIDE_INSTALLATION.txt# Instructions pour finaliser l'installateur
```

### Étape 2: Ajouter les Dépendances Portables

1. **Python Portable**
   - Télécharger [Python 3.11+ Portable](https://www.python.org/downloads/)
   - Extraire dans `portable_deps/python_portable/`

2. **Node.js Portable**
   - Télécharger [Node.js Portable](https://nodejs.org/download/release/)
   - Extraire dans `portable_deps/nodejs_portable/`

3. **Qdrant Portable**
   - Télécharger [Qdrant Binary](https://github.com/qdrant/qdrant/releases)
   - Placer le binaire et ses dépendances dans `portable_deps/qdrant_portable/`

### Étape 3: Ajouter le Code Source du Projet
Copier le contenu complet du projet dans `project_source/`, en excluant :
- `.venv/`
- `node_modules/`
- Fichiers temporaires (voir `cleanup_project.bat`)

### Étape 4: Créer l'Exécutable Auto-Extractible

Utiliser les commandes suivantes (ajustez les chemins si nécessaire) :
```bash
cd POCTechnicia_Installer
7z a -r installer.7z project_source portable_deps install.bat README.txt
copy /b 7zSD.sfx + config.txt + installer.7z POCTechnicia_Installer.exe
```

## Utilisation de l'Installateur Portable

### Installation
1. Exécuter `POCTechnicia_Installer.exe`
2. Choisir le répertoire d'installation (par défaut: `%USERPROFILE%\POC TECHNICIA`)
3. Attendre la fin de l'extraction et de la configuration initiale

### Configuration
```bash
cd scripts/maintenance
setup_portable.bat
```
Ce script va :
- Utiliser Python portable pour installer les dépendances Python
- Utiliser NPM portable pour installer les dépendances du frontend
- Configurer l'environnement pour utiliser les versions portables

### Démarrage
```bash
cd scripts/startup
start_portable.bat
```
Ce script va :
- Démarrer Qdrant portable avec stockage local
- Démarrer le backend FastAPI avec Python portable
- Démarrer le frontend React avec Node.js portable

## Maintenance

### Nettoyage de Qdrant
```bash
cd scripts/maintenance
clean_qdrant_portable.bat
```

Ce script fonctionne comme `clean_qdrant.bat`, mais utilise Python portable.

## Structure des Scripts Portables

### setup_portable.bat
- Définit les chemins des versions portables de Python, Node.js et Qdrant
- Configure le frontend avec NPM portable
- Configure l'environnement Python avec le Python portable

### start_portable.bat
- Définit les chemins des versions portables
- Démarre Qdrant portable
- Démarre le backend FastAPI avec uvicorn et Python portable
- Démarre le frontend React avec NPM portable

### clean_qdrant_portable.bat
- Utilise Python portable pour nettoyer la base de données Qdrant

## Dépannage

### Problèmes Courants
1. **Python portable ne démarre pas**
   - Vérifier que tous les DLL nécessaires sont présents dans le dossier Python portable
   - Essayer d'exécuter `python.exe` directement pour voir les erreurs

2. **Node.js portable ne démarre pas**
   - Vérifier que le chemin ne contient pas d'espaces
   - Exécuter `node.exe -v` pour vérifier que Node.js fonctionne

3. **Qdrant ne démarre pas**
   - Vérifier les logs dans `qdrant_storage/qdrant.log`
   - S'assurer que le port 6333 est disponible

Pour un guide de dépannage plus détaillé, consultez [Portable_Installation.md](./TROUBLESHOOTING/Portable_Installation.md) dans le dossier TROUBLESHOOTING.

## Notes Importantes

1. Les chemins sont relatifs au répertoire d'installation
2. L'installateur portable ne modifie pas les variables d'environnement système
3. Toutes les dépendances sont contenues dans le dossier d'installation
4. La portabilité implique que tout est auto-contenu et ne modifie pas le système hôte
