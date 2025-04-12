#!/bin/bash
# Script d'installation Technicia OCR pour Linux
# Version: 1.0
# Date: 2 avril 2025
#
# Ce script permet l'installation et la configuration du système OCR Technicia
# sur un serveur Linux (Ubuntu/Debian).

set -e  # Arrêt en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Paramètres par défaut
INSTALL_DIR="/opt/technicia/ocr-system"
DATA_DIR="/var/lib/technicia/data"
LOG_DIR="/var/log/technicia"
POSTGRES_PASSWORD="SecureP@ssw0rd"
POSTGRES_PORT="5432"
APP_PORT="5000"
SKIP_PYTHON=false
SKIP_POSTGRES=false
SKIP_REDIS=false
INSTALL_AS_SERVICE=true

# Fonction pour afficher les messages avec horodatage
log_message() {
    local level="INFO"
    local message=$1
    
    if [ ! -z "$2" ]; then
        level=$2
    fi
    
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    if [ "$level" == "ERROR" ]; then
        echo -e "[$timestamp] [$level] ${RED}$message${NC}"
    elif [ "$level" == "WARN" ]; then
        echo -e "[$timestamp] [$level] ${YELLOW}$message${NC}"
    else
        echo -e "[$timestamp] [$level] ${GREEN}$message${NC}"
    fi
}

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Vérification des droits root
if [ "$(id -u)" -ne 0 ]; then
    log_message "Ce script doit être exécuté avec les privilèges root (sudo)." "ERROR"
    exit 1
fi

# Affichage du banner
log_message "Installation du système OCR Technicia pour Linux"
log_message "------------------------------------------------"

# Analyse des arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --install-dir=*)
            INSTALL_DIR="${1#*=}"
            ;;
        --data-dir=*)
            DATA_DIR="${1#*=}"
            ;;
        --log-dir=*)
            LOG_DIR="${1#*=}"
            ;;
        --postgres-password=*)
            POSTGRES_PASSWORD="${1#*=}"
            ;;
        --postgres-port=*)
            POSTGRES_PORT="${1#*=}"
            ;;
        --app-port=*)
            APP_PORT="${1#*=}"
            ;;
        --skip-python)
            SKIP_PYTHON=true
            ;;
        --skip-postgres)
            SKIP_POSTGRES=true
            ;;
        --skip-redis)
            SKIP_REDIS=true
            ;;
        --no-service)
            INSTALL_AS_SERVICE=false
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --install-dir=DIR       Répertoire d'installation (défaut: $INSTALL_DIR)"
            echo "  --data-dir=DIR          Répertoire des données (défaut: $DATA_DIR)"
            echo "  --log-dir=DIR           Répertoire des logs (défaut: $LOG_DIR)"
            echo "  --postgres-password=PWD Mot de passe PostgreSQL (défaut: SecureP@ssw0rd)"
            echo "  --postgres-port=PORT    Port PostgreSQL (défaut: 5432)"
            echo "  --app-port=PORT         Port de l'application (défaut: 5000)"
            echo "  --skip-python           Ne pas installer Python"
            echo "  --skip-postgres         Ne pas installer PostgreSQL"
            echo "  --skip-redis            Ne pas installer Redis"
            echo "  --no-service            Ne pas installer en tant que service"
            echo "  --help                  Afficher cette aide"
            exit 0
            ;;
        *)
            log_message "Option inconnue: $1" "ERROR"
            exit 1
            ;;
    esac
    shift
done

# Création des répertoires nécessaires
log_message "Création des répertoires d'installation..."
mkdir -p "$INSTALL_DIR" \
         "$DATA_DIR/uploads" \
         "$DATA_DIR/processed" \
         "$DATA_DIR/temp" \
         "$DATA_DIR/cache" \
         "$LOG_DIR"

# Mise à jour des dépôts
log_message "Mise à jour des dépôts apt..."
apt-get update

# Installation des dépendances système
log_message "Installation des dépendances système de base..."
apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    supervisor

# Installation de Python si nécessaire
if [ "$SKIP_PYTHON" = false ]; then
    log_message "Vérification de l'installation Python..."
    
    if ! command_exists python3; then
        log_message "Python n'est pas installé. Installation en cours..."
        apt-get install -y python3 python3-pip python3-venv
    else
        log_message "Python est déjà installé: $(python3 --version)"
    fi
    
    # Mise à jour de pip
    log_message "Mise à jour de pip..."
    python3 -m pip install --upgrade pip
fi

# Installation de PostgreSQL si nécessaire
if [ "$SKIP_POSTGRES" = false ]; then
    log_message "Vérification de l'installation PostgreSQL..."
    
    if ! command_exists psql; then
        log_message "PostgreSQL n'est pas installé. Installation en cours..."
        apt-get install -y postgresql postgresql-contrib
    else
        log_message "PostgreSQL est déjà installé: $(psql --version)"
    fi
    
    # Création de la base de données et de l'utilisateur
    log_message "Configuration de la base de données PostgreSQL..."
    
    # Vérification si la base de données existe déjà
    db_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='ocr_db'")
    
    if [ "$db_exists" != "1" ]; then
        # Création de la base de données et de l'utilisateur
        sudo -u postgres psql -c "CREATE DATABASE ocr_db;"
        sudo -u postgres psql -c "CREATE USER technicia WITH ENCRYPTED PASSWORD '$POSTGRES_PASSWORD';"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ocr_db TO technicia;"
        log_message "Base de données et utilisateur PostgreSQL créés avec succès"
    else
        log_message "La base de données ocr_db existe déjà" "WARN"
    fi
fi

# Installation de Redis si nécessaire
if [ "$SKIP_REDIS" = false ]; then
    log_message "Vérification de l'installation Redis..."
    
    if ! command_exists redis-cli; then
        log_message "Redis n'est pas installé. Installation en cours..."
        apt-get install -y redis-server
        
        # Configuration de Redis pour qu'il démarre au démarrage
        systemctl enable redis-server
        systemctl start redis-server
    else
        log_message "Redis est déjà installé: $(redis-cli --version)"
    fi
fi

# Installation de Tesseract OCR
log_message "Installation de Tesseract OCR..."
if ! command_exists tesseract; then
    apt-get install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng
else
    log_message "Tesseract OCR est déjà installé: $(tesseract --version)"
fi

# Installation des outils supplémentaires pour le traitement de documents
log_message "Installation des outils de traitement de documents..."
apt-get install -y \
    poppler-utils \
    ghostscript \
    imagemagick \
    libmagickwand-dev

# Clonage et installation du code source
log_message "Vérification du code source..."
if [ -d "$PWD/app" ] && [ -f "$PWD/requirements.txt" ]; then
    log_message "Copie des fichiers d'application vers le répertoire d'installation..."
    cp -r "$PWD"/* "$INSTALL_DIR"
    
    # Exclusion des répertoires inutiles
    rm -rf "$INSTALL_DIR/deploy" "$INSTALL_DIR/logs" "$INSTALL_DIR/data" "$INSTALL_DIR/.git"*
else
    log_message "CODE SOURCE NON TROUVÉ. Ce script devrait être exécuté depuis le répertoire du code source." "ERROR"
    log_message "Veuillez cloner le dépôt et réessayer." "ERROR"
    exit 1
fi

# Création d'un environnement Python virtuel
log_message "Création de l'environnement Python virtuel..."
python3 -m venv "$INSTALL_DIR/venv"

# Activation de l'environnement virtuel et installation des dépendances
log_message "Installation des dépendances Python..."
source "$INSTALL_DIR/venv/bin/activate"
pip install -r "$INSTALL_DIR/requirements.txt"
deactivate

# Création du fichier de configuration
log_message "Création du fichier de configuration..."
cat > "$INSTALL_DIR/config.ini" << EOF
# Configuration du système OCR Technicia
# Généré automatiquement par le script d'installation

[app]
name = Technicia OCR
environment = production
debug = False
secret_key = $(python3 -c "import uuid; print(uuid.uuid4())")
max_parallel_tasks = 4
ocr_quality_threshold = 0.75

[paths]
data_dir = $DATA_DIR
log_dir = $LOG_DIR

[database]
host = localhost
port = $POSTGRES_PORT
name = ocr_db
user = technicia
password = $POSTGRES_PASSWORD

[redis]
host = localhost
port = 6379
db = 0
EOF

# Configuration des permissions
log_message "Configuration des permissions..."
useradd -r -s /bin/false technicia || log_message "L'utilisateur technicia existe déjà" "WARN"
chown -R technicia:technicia "$INSTALL_DIR" "$DATA_DIR" "$LOG_DIR"
chmod -R 750 "$INSTALL_DIR" "$DATA_DIR" "$LOG_DIR"

# Installation du service système si demandé
if [ "$INSTALL_AS_SERVICE" = true ]; then
    log_message "Configuration des services systemd..."
    
    # Service API
    cat > /etc/systemd/system/technicia-ocr-api.service << EOF
[Unit]
Description=Technicia OCR API Service
After=network.target postgresql.service redis-server.service

[Service]
User=technicia
Group=technicia
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind 0.0.0.0:$APP_PORT --workers 4 --timeout 120 app.wsgi:app
Restart=on-failure
StandardOutput=append:$LOG_DIR/api.log
StandardError=append:$LOG_DIR/api-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Service Worker
    cat > /etc/systemd/system/technicia-ocr-worker.service << EOF
[Unit]
Description=Technicia OCR Worker Service
After=network.target postgresql.service redis-server.service technicia-ocr-api.service

[Service]
User=technicia
Group=technicia
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/celery -A app.celery_app worker --loglevel=info --concurrency=4
Restart=on-failure
StandardOutput=append:$LOG_DIR/worker.log
StandardError=append:$LOG_DIR/worker-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Service Beat
    cat > /etc/systemd/system/technicia-ocr-beat.service << EOF
[Unit]
Description=Technicia OCR Beat Service
After=network.target redis-server.service technicia-ocr-api.service

[Service]
User=technicia
Group=technicia
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/celery -A app.celery_app beat --loglevel=info
Restart=on-failure
StandardOutput=append:$LOG_DIR/beat.log
StandardError=append:$LOG_DIR/beat-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Rechargement systemd
    log_message "Rechargement systemd..."
    systemctl daemon-reload
    
    # Activation et démarrage des services
    log_message "Activation et démarrage des services..."
    for service in technicia-ocr-api.service technicia-ocr-worker.service technicia-ocr-beat.service; do
        systemctl enable $service
        systemctl start $service
        log_message "Service $service démarré."
    done
fi

# Création d'un script de démarrage pour une utilisation manuelle
cat > "$INSTALL_DIR/start.sh" << EOF
#!/bin/bash

# Script de démarrage manuel pour le système OCR Technicia
# Utiliser ce script si vous n'avez pas installé les services systemd

# Activation de l'environnement virtuel
source "$INSTALL_DIR/venv/bin/activate"

# Démarrage de l'API
gunicorn --bind 0.0.0.0:$APP_PORT --workers 4 --timeout 120 app.wsgi:app &

# Démarrage du worker Celery
celery -A app.celery_app worker --loglevel=info --concurrency=4 &

# Démarrage du beat Celery
celery -A app.celery_app beat --loglevel=info &

echo "Services démarrés. Appuyez sur Ctrl+C pour arrêter."
wait
EOF

chmod +x "$INSTALL_DIR/start.sh"

log_message "Installation terminée avec succès !"
log_message "L'API est accessible à l'adresse: http://localhost:$APP_PORT"
log_message "Pour plus d'informations, consultez le guide administrateur dans la documentation."
