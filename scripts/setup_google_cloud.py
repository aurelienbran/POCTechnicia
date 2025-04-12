#!/usr/bin/env python
"""
Script de configuration et test de l'intégration avec Google Cloud.
Vérifie la configuration des APIs Document AI et Vision AI pour le projet Technicia.

Utilisation:
    python setup_google_cloud.py [--check] [--setup]

Options:
    --check: Vérifie la configuration actuelle
    --setup: Guide l'utilisateur dans la configuration initiale
"""

import argparse
import os
import sys
import logging
import json
from pathlib import Path
import subprocess
import webbrowser

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au chemin pour importer les modules du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Configuration et test de l'intégration Google Cloud")
    parser.add_argument("--check", action="store_true", help="Vérifie la configuration actuelle")
    parser.add_argument("--setup", action="store_true", help="Guide l'utilisateur dans la configuration initiale")
    return parser.parse_args()

def check_gcloud_installed():
    """Vérifie si gcloud CLI est installé."""
    try:
        result = subprocess.run(['gcloud', '--version'], 
                              capture_output=True, text=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_credentials():
    """Vérifie les identifiants Google Cloud."""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not creds_path:
        logger.error("Variable d'environnement GOOGLE_APPLICATION_CREDENTIALS non définie")
        return False
    
    creds_path = Path(creds_path)
    if not creds_path.exists():
        logger.error(f"Fichier d'identifiants non trouvé: {creds_path}")
        return False
    
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
        
        required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        for key in required_keys:
            if key not in creds:
                logger.error(f"Clé manquante dans le fichier d'identifiants: {key}")
                return False
        
        logger.info(f"Fichier d'identifiants valide: {creds_path}")
        logger.info(f"Projet GCP: {creds['project_id']}")
        return True
    
    except json.JSONDecodeError:
        logger.error(f"Format de fichier d'identifiants invalide: {creds_path}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des identifiants: {e}")
        return False

def check_apis():
    """Vérifie si les APIs nécessaires sont activées."""
    if not check_gcloud_installed():
        logger.error("gcloud CLI n'est pas installé ou n'est pas dans le PATH")
        logger.error("Installez-le depuis: https://cloud.google.com/sdk/docs/install")
        return False
    
    apis_to_check = [
        "documentai.googleapis.com",
        "vision.googleapis.com"
    ]
    
    all_enabled = True
    
    for api in apis_to_check:
        try:
            result = subprocess.run(
                ['gcloud', 'services', 'list', '--filter', f"NAME:{api}"],
                capture_output=True, text=True, check=False
            )
            
            if api in result.stdout:
                logger.info(f"✅ API {api} est activée")
            else:
                logger.error(f"❌ API {api} n'est pas activée")
                all_enabled = False
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'API {api}: {e}")
            all_enabled = False
    
    return all_enabled

def setup_google_cloud():
    """Guide l'utilisateur dans la configuration de Google Cloud."""
    logger.info("=== Assistant de configuration Google Cloud pour Technicia ===")
    
    # 1. Vérifier/installer gcloud CLI
    if not check_gcloud_installed():
        logger.info("\n1. Installation de gcloud CLI")
        logger.info("Veuillez installer gcloud CLI depuis: https://cloud.google.com/sdk/docs/install")
        open_browser = input("Ouvrir la page d'installation dans votre navigateur? (o/n): ")
        if open_browser.lower() == 'o':
            webbrowser.open("https://cloud.google.com/sdk/docs/install")
        
        logger.info("Une fois gcloud CLI installé, exécutez 'gcloud init' pour configurer votre compte")
        logger.info("Puis relancez ce script")
        return
    
    # 2. Authentification
    logger.info("\n2. Authentification Google Cloud")
    logger.info("Vous devez vous authentifier avec Google Cloud")
    auth_browser = input("Lancer l'authentification dans le navigateur? (o/n): ")
    if auth_browser.lower() == 'o':
        subprocess.run(['gcloud', 'auth', 'login'], check=False)
    
    # 3. Sélection/création du projet
    logger.info("\n3. Configuration du projet")
    create_new = input("Créer un nouveau projet? (o/n): ")
    
    if create_new.lower() == 'o':
        project_id = input("Entrez l'ID du nouveau projet (ex: technicia-123): ")
        try:
            subprocess.run(['gcloud', 'projects', 'create', project_id], check=True)
            logger.info(f"Projet {project_id} créé avec succès")
            
            # Définir le projet actif
            subprocess.run(['gcloud', 'config', 'set', 'project', project_id], check=True)
        except Exception as e:
            logger.error(f"Erreur lors de la création du projet: {e}")
            return
    else:
        # Lister les projets disponibles
        logger.info("Projets disponibles:")
        subprocess.run(['gcloud', 'projects', 'list'], check=False)
        
        project_id = input("Entrez l'ID du projet à utiliser: ")
        try:
            subprocess.run(['gcloud', 'config', 'set', 'project', project_id], check=True)
            logger.info(f"Projet {project_id} défini comme projet actif")
        except Exception as e:
            logger.error(f"Erreur lors de la définition du projet: {e}")
            return
    
    # 4. Activer les APIs nécessaires
    logger.info("\n4. Activation des APIs")
    apis = [
        "documentai.googleapis.com",
        "vision.googleapis.com"
    ]
    
    for api in apis:
        logger.info(f"Activation de l'API {api}...")
        try:
            subprocess.run(['gcloud', 'services', 'enable', api], check=True)
            logger.info(f"✅ API {api} activée avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'activation de l'API {api}: {e}")
    
    # 5. Créer un compte de service
    logger.info("\n5. Création d'un compte de service")
    service_account_name = input("Nom du compte de service (ex: technicia-sa): ")
    service_account_id = f"{service_account_name}@{project_id}.iam.gserviceaccount.com"
    
    try:
        # Créer le compte de service
        subprocess.run([
            'gcloud', 'iam', 'service-accounts', 'create', service_account_name,
            '--display-name', f"Compte de service pour Technicia"
        ], check=True)
        
        logger.info(f"✅ Compte de service {service_account_id} créé avec succès")
        
        # Attribuer les rôles nécessaires
        roles = [
            "roles/documentai.admin",
            "roles/vision.admin"
        ]
        
        for role in roles:
            subprocess.run([
                'gcloud', 'projects', 'add-iam-policy-binding', project_id,
                '--member', f"serviceAccount:{service_account_id}",
                '--role', role
            ], check=True)
            logger.info(f"✅ Rôle {role} attribué au compte de service")
        
        # Créer la clé de compte de service
        key_file = Path(f"{service_account_name}-key.json")
        subprocess.run([
            'gcloud', 'iam', 'service-accounts', 'keys', 'create',
            str(key_file), '--iam-account', service_account_id
        ], check=True)
        
        logger.info(f"✅ Clé de compte de service créée: {key_file.absolute()}")
        
        # Conseiller sur la configuration de la variable d'environnement
        logger.info("\n6. Configuration de la variable d'environnement")
        logger.info("Ajoutez la ligne suivante à votre fichier .env:")
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS={key_file.absolute()}")
        
        with open(".env", "a") as f:
            f.write(f"\n# Configuration Google Cloud\n")
            f.write(f"GOOGLE_APPLICATION_CREDENTIALS={key_file.absolute()}\n")
            f.write(f"DOCUMENT_AI_PROJECT_ID={project_id}\n")
            f.write(f"DOCUMENT_AI_LOCATION=eu\n")
        
        logger.info("✅ Variables ajoutées au fichier .env")
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du compte de service: {e}")
        return
    
    # 7. Configuration de Document AI
    logger.info("\n7. Configuration de Document AI")
    logger.info("Vous devez maintenant créer un processeur Document AI:")
    logger.info("1. Accédez à la console Document AI: https://console.cloud.google.com/ai/document-ai")
    logger.info("2. Créez un processeur de type 'Document OCR Processor'")
    logger.info("3. Notez l'ID du processeur créé")
    
    open_browser = input("Ouvrir la console Document AI dans votre navigateur? (o/n): ")
    if open_browser.lower() == 'o':
        webbrowser.open(f"https://console.cloud.google.com/ai/document-ai?project={project_id}")
    
    processor_id = input("Entrez l'ID du processeur Document AI créé (ou laissez vide pour plus tard): ")
    if processor_id:
        with open(".env", "a") as f:
            f.write(f"DOCUMENT_AI_PROCESSOR_ID={processor_id}\n")
        logger.info("✅ ID du processeur Document AI ajouté au fichier .env")
    
    logger.info("\n✅ Configuration de Google Cloud terminée avec succès!")
    logger.info("Pour tester la configuration, exécutez: python setup_google_cloud.py --check")

def main():
    """Fonction principale."""
    args = get_args()
    
    if not (args.check or args.setup):
        logger.info("Aucune option spécifiée. Utilisation par défaut: --check")
        args.check = True
    
    if args.check:
        logger.info("=== Vérification de la configuration Google Cloud ===")
        
        credentials_ok = check_credentials()
        if credentials_ok:
            apis_ok = check_apis()
        else:
            apis_ok = False
        
        if credentials_ok and apis_ok:
            logger.info("\n✅ Configuration Google Cloud correcte!")
        else:
            logger.warning("\n⚠️ Des problèmes ont été détectés dans la configuration.")
            logger.info("Pour configurer Google Cloud, exécutez: python setup_google_cloud.py --setup")
    
    if args.setup:
        setup_google_cloud()

if __name__ == "__main__":
    main()
