-- Script d'initialisation de la base de données PostgreSQL pour Technicia OCR
-- Version: 1.0
-- Date: 7 avril 2025
--
-- Ce script initialise la base de données pour l'environnement de staging
-- du système OCR Technicia.

-- Création des extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Configuration des paramètres
ALTER SYSTEM SET max_connections = '100';
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET max_worker_processes = 8;
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET max_parallel_maintenance_workers = 4;
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_min_duration_statement = 500;

-- Création des schémas
CREATE SCHEMA IF NOT EXISTS ocr;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS stats;
CREATE SCHEMA IF NOT EXISTS audit;

COMMENT ON SCHEMA ocr IS 'Schéma pour les données OCR et les documents';
COMMENT ON SCHEMA users IS 'Schéma pour les utilisateurs et les autorisations';
COMMENT ON SCHEMA stats IS 'Schéma pour les statistiques et la télémétrie';
COMMENT ON SCHEMA audit IS 'Schéma pour l''audit et la traçabilité';

-- Table de configuration globale
CREATE TABLE IF NOT EXISTS public.global_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(100)
);

COMMENT ON TABLE public.global_settings IS 'Paramètres globaux du système';

-- Insérer les paramètres par défaut
INSERT INTO public.global_settings (key, value, description, modified_by)
VALUES 
    ('environment', 'staging', 'Environnement d''exécution du système', 'system'),
    ('ocr_engine', 'tesseract', 'Moteur OCR utilisé par défaut', 'system'),
    ('default_language', 'fra', 'Langue par défaut pour l''OCR', 'system'),
    ('max_file_size_mb', '50', 'Taille maximale des fichiers en MB', 'system'),
    ('allowed_file_types', 'pdf,jpg,jpeg,png,tiff,tif,bmp', 'Types de fichiers autorisés', 'system'),
    ('enable_audit', 'true', 'Active la journalisation d''audit', 'system'),
    ('retention_days', '90', 'Durée de conservation des données en jours', 'system')
ON CONFLICT (key) DO UPDATE
    SET value = EXCLUDED.value,
        description = EXCLUDED.description,
        modified_at = CURRENT_TIMESTAMP,
        modified_by = EXCLUDED.modified_by;

-- Création d'une fonction pour l'horodatage automatique
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Fin du script d'initialisation
SELECT 'Base de données initialisée avec succès' AS status;
