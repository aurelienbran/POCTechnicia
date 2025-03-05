# Dépannage de l'Installation Portable

Ce guide traite les problèmes courants liés à l'installateur portable et propose des solutions.

## Problèmes de Création de l'Installateur

### Erreur lors de la création de l'exécutable SFX

**Symptôme**: 
```
7z: Command not found
```
ou
```
The system cannot find the file 7zSD.sfx
```

**Causes possibles**:
- 7-Zip n'est pas installé
- 7-Zip n'est pas dans le PATH
- Le module SFX n'est pas disponible

**Solutions**:
1. Installer [7-Zip](https://www.7-zip.org/)
2. Télécharger [7-Zip Extra](https://www.7-zip.org/a/7z2301-extra.7z) qui contient les modules SFX
3. Extraire 7zSD.sfx dans le dossier de l'installateur
4. Utiliser des chemins absolus dans les commandes

### Fichiers manquants dans l'archive

**Symptôme**: L'installateur s'exécute mais certains composants sont manquants

**Causes possibles**:
- Chemin incorrect lors de la création de l'archive
- Fichiers exclus involontairement

**Solutions**:
1. Vérifier la commande de création d'archive:
```
7z a -r installer.7z project_source portable_deps install.bat README.txt
```
2. Vérifier que tous les dossiers nécessaires existent et contiennent les fichiers requis
3. Extraire manuellement l'archive pour vérifier son contenu

## Problèmes d'Installation

### Erreur lors de l'extraction

**Symptôme**: Message d'erreur lors de l'auto-extraction

**Causes possibles**:
- Droits d'accès insuffisants
- Espace disque insuffisant
- Corruption de l'exécutable

**Solutions**:
1. Exécuter l'installateur en tant qu'administrateur
2. Vérifier qu'il y a au moins 2GB d'espace disponible
3. Recréer l'installateur

### Échec de création des dossiers d'installation

**Symptôme**: 
```
Impossible de créer le répertoire
```

**Causes possibles**:
- Droits d'accès insuffisants
- Chemin trop long
- Caractères spéciaux dans le chemin

**Solutions**:
1. Choisir un chemin d'installation plus court
2. Éviter les caractères spéciaux dans le chemin
3. Vérifier les droits d'accès au dossier parent

## Problèmes avec les Versions Portables

### Python Portable ne s'exécute pas

**Symptôme**: 
```
'python.exe' n'est pas reconnu comme une commande interne ou externe
```
ou
```
DLL manquante
```

**Causes possibles**:
- Fichiers Python incomplets
- DLL système manquantes
- Conflit avec un Python installé

**Solutions**:
1. Vérifier que tous les fichiers Python sont présents dans `portable_deps\python_portable`
2. Installer les [Visual C++ Redistributable](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads)
3. Utiliser une version de Python compatible avec Windows

### Node.js Portable ne s'exécute pas

**Symptôme**:
```
'node.exe' n'est pas reconnu comme une commande interne ou externe
```

**Causes possibles**:
- Fichiers Node.js incomplets
- Chemin contenant des espaces

**Solutions**:
1. Vérifier que tous les fichiers Node.js sont présents
2. Utiliser un chemin sans espaces
3. Copier manuellement node.exe et npm.cmd dans le dossier de l'application

### Qdrant Portable ne démarre pas

**Symptôme**:
```
Le processus ne démarre pas
```
ou
```
Erreur de connexion à localhost:6333
```

**Causes possibles**:
- Port 6333 déjà utilisé
- Binaire Qdrant incompatible
- Fichiers de configuration manquants

**Solutions**:
1. Vérifier qu'aucun autre service n'utilise le port 6333
2. Télécharger une version Windows compatible de Qdrant
3. Vérifier les logs dans `qdrant_storage/qdrant.log`

## Problèmes de Scripts Portables

### setup_portable.bat échoue

**Symptôme**:
```
Échec de l'installation des dépendances
```

**Causes possibles**:
- Accès internet bloqué
- Conflit de versions de packages
- Erreur dans les chemins relatifs

**Solutions**:
1. Vérifier la connexion internet
2. Modifier le script pour utiliser des chemins absolus
3. Exécuter pip et npm manuellement pour voir les erreurs détaillées

### start_portable.bat ne démarre pas tous les services

**Symptôme**: Certains services ne démarrent pas

**Causes possibles**:
- Services interdépendants
- Ordre de démarrage incorrect
- Temps d'attente insuffisant

**Solutions**:
1. Augmenter les temps d'attente entre les démarrages
2. Vérifier les logs de chaque service
3. Démarrer les services manuellement un par un

## Vérification de l'Installation

Pour vérifier que l'installation portable fonctionne correctement:

1. **Vérifier Python portable**:
```
cd portable_deps\python
python.exe -c "print('Hello, World!')"
```

2. **Vérifier Node.js portable**:
```
cd portable_deps\nodejs
node.exe -v
```

3. **Vérifier Qdrant portable**:
```
cd portable_deps\qdrant
qdrant.exe --version
```

4. **Vérifier l'accessibilité des scripts**:
```
cd scripts
dir startup\*.bat
dir maintenance\*.bat
```

Si tous ces tests passent, l'installation portable devrait fonctionner correctement.
