# Dockerfile pour l'application Technicia OCR
# Version: 1.0
# Date: 2 avril 2025
#
# Ce Dockerfile permet de construire une image Docker complète pour le système OCR Technicia.
# Il utilise une approche multi-étapes pour optimiser la taille de l'image finale.

# ===== ÉTAPE 1: Image de base avec les dépendances Python =====
FROM python:3.10-slim AS base

# Définition des variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Installation des dépendances système de base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Création d'un utilisateur non-root
RUN useradd -m -r -u 1000 technicia
WORKDIR /app
RUN chown technicia:technicia /app

# ===== ÉTAPE 2: Installation des dépendances Python =====
FROM base AS python-deps

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ===== ÉTAPE 3: Installation des dépendances OCR =====
FROM python-deps AS ocr-deps

# Installation de Tesseract OCR et ses dépendances
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# ===== ÉTAPE 4: Application finale =====
FROM ocr-deps AS final

# Copie du code de l'application
COPY --chown=technicia:technicia . /app/

# Création des répertoires nécessaires
RUN mkdir -p /app/data/uploads /app/data/processed /app/data/temp /app/data/cache /app/logs \
    && chown -R technicia:technicia /app/data /app/logs

# Port exposé par l'application
EXPOSE 5000

# Utilisateur non-root pour l'exécution
USER technicia

# Commande par défaut
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app.wsgi:app"]
