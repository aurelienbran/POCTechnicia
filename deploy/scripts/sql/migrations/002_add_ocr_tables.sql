-- Migration 002: Ajout des tables OCR pour Technicia OCR
-- Version: 1.0
-- Date: 7 avril 2025
--
-- Cette migration ajoute les tables spécifiques à l'OCR pour le système Technicia OCR,
-- incluant les tables de documents, résultats OCR, et configurations OCR.

BEGIN;

-- Table des documents
CREATE TABLE IF NOT EXISTS ocr.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    md5_hash VARCHAR(32) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    is_public BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE ocr.documents IS 'Documents uploadés dans le système';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_documents_modified_at
BEFORE UPDATE ON ocr.documents
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Index pour les recherches sur les documents
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON ocr.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON ocr.documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON ocr.documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_title ON ocr.documents USING gin(to_tsvector('french', title));
CREATE INDEX IF NOT EXISTS idx_documents_tags ON ocr.documents USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON ocr.documents USING gin(metadata);

-- Table des pages de documents
CREATE TABLE IF NOT EXISTS ocr.document_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES ocr.documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    image_path VARCHAR(512) NOT NULL,
    width INTEGER,
    height INTEGER,
    dpi INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(document_id, page_number)
);

COMMENT ON TABLE ocr.document_pages IS 'Pages individuelles des documents';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_document_pages_modified_at
BEFORE UPDATE ON ocr.document_pages
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Table des résultats OCR
CREATE TABLE IF NOT EXISTS ocr.ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID NOT NULL REFERENCES ocr.document_pages(id) ON DELETE CASCADE,
    ocr_engine VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL,
    confidence FLOAT,
    full_text TEXT,
    hocr_content TEXT,
    json_content JSONB,
    processing_time INTEGER, -- temps en millisecondes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(page_id, ocr_engine, language)
);

COMMENT ON TABLE ocr.ocr_results IS 'Résultats OCR pour chaque page';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_ocr_results_modified_at
BEFORE UPDATE ON ocr.ocr_results
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Index pour la recherche en texte intégral
CREATE INDEX IF NOT EXISTS idx_ocr_results_full_text ON ocr.ocr_results USING gin(to_tsvector('french', full_text));

-- Table des configurations OCR
CREATE TABLE IF NOT EXISTS ocr.ocr_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    ocr_engine VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users.users(id) ON DELETE SET NULL
);

COMMENT ON TABLE ocr.ocr_configurations IS 'Configurations OCR disponibles';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_ocr_configurations_modified_at
BEFORE UPDATE ON ocr.ocr_configurations
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Table des zones d'intérêt des documents
CREATE TABLE IF NOT EXISTS ocr.zones_of_interest (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES ocr.documents(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    x_coord INTEGER NOT NULL,
    y_coord INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    category VARCHAR(50),
    extraction_rules JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users.users(id) ON DELETE SET NULL
);

COMMENT ON TABLE ocr.zones_of_interest IS 'Zones d''intérêt définies sur les documents';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_zones_of_interest_modified_at
BEFORE UPDATE ON ocr.zones_of_interest
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Table des extractions structurées
CREATE TABLE IF NOT EXISTS ocr.structured_extractions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES ocr.documents(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES ocr.zones_of_interest(id) ON DELETE SET NULL,
    field_name VARCHAR(100) NOT NULL,
    field_value TEXT,
    confidence FLOAT,
    extraction_method VARCHAR(50) NOT NULL,
    page_number INTEGER NOT NULL,
    x_coord INTEGER,
    y_coord INTEGER,
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ocr.structured_extractions IS 'Données structurées extraites des documents';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_structured_extractions_modified_at
BEFORE UPDATE ON ocr.structured_extractions
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Table des tâches OCR
CREATE TABLE IF NOT EXISTS ocr.ocr_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES ocr.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    configuration_id UUID REFERENCES ocr.ocr_configurations(id) ON DELETE SET NULL,
    priority INTEGER DEFAULT 0,
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ocr.ocr_tasks IS 'Tâches OCR en cours et historique';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_ocr_tasks_modified_at
BEFORE UPDATE ON ocr.ocr_tasks
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Index pour les recherches sur les tâches
CREATE INDEX IF NOT EXISTS idx_ocr_tasks_user_id ON ocr.ocr_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_ocr_tasks_status ON ocr.ocr_tasks(status);
CREATE INDEX IF NOT EXISTS idx_ocr_tasks_created_at ON ocr.ocr_tasks(created_at);

-- Table des statistiques OCR
CREATE TABLE IF NOT EXISTS stats.ocr_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users.users(id) ON DELETE SET NULL,
    document_id UUID REFERENCES ocr.documents(id) ON DELETE SET NULL,
    ocr_engine VARCHAR(50) NOT NULL,
    document_count INTEGER DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    character_count INTEGER DEFAULT 0,
    processing_time INTEGER DEFAULT 0, -- temps total en millisecondes
    accuracy FLOAT,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stats.ocr_statistics IS 'Statistiques quotidiennes d''utilisation OCR';

-- Index pour les recherches sur les statistiques
CREATE INDEX IF NOT EXISTS idx_ocr_statistics_user_id ON stats.ocr_statistics(user_id);
CREATE INDEX IF NOT EXISTS idx_ocr_statistics_date ON stats.ocr_statistics(date);
CREATE INDEX IF NOT EXISTS idx_ocr_statistics_ocr_engine ON stats.ocr_statistics(ocr_engine);

-- Insertion de configurations OCR par défaut
INSERT INTO ocr.ocr_configurations (name, description, ocr_engine, parameters, is_default)
VALUES 
    ('default_fra', 'Configuration par défaut pour le français', 'tesseract', 
     '{"lang": "fra", "dpi": 300, "psm": 3, "oem": 3}', true),
    ('default_eng', 'Configuration par défaut pour l''anglais', 'tesseract', 
     '{"lang": "eng", "dpi": 300, "psm": 3, "oem": 3}', false),
    ('high_quality_fra', 'Configuration haute qualité pour le français', 'tesseract', 
     '{"lang": "fra", "dpi": 600, "psm": 1, "oem": 3}', false),
    ('fast_fra', 'Configuration rapide pour le français', 'tesseract', 
     '{"lang": "fra", "dpi": 150, "psm": 6, "oem": 0}', false)
ON CONFLICT (name) DO NOTHING;

COMMIT;

-- Fin de la migration
SELECT '002_add_ocr_tables.sql exécuté avec succès' AS status;
