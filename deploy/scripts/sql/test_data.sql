-- Script de données de test pour Technicia OCR
-- Version: 1.0
-- Date: 7 avril 2025
--
-- Ce script insère des données de test dans la base de données 
-- pour l'environnement de staging du système OCR Technicia.

BEGIN;

-- Variables pour les UUID
DO $$
DECLARE
    admin_id UUID;
    user_id UUID;
    tester_id UUID;
    admin_role_id UUID;
    user_role_id UUID;
    tester_role_id UUID;
BEGIN
    -- Insertion d'utilisateurs de test
    -- Mot de passe: 'StrongPassword123!' (hashé avec pgcrypto)
    INSERT INTO users.users (username, email, password_hash, first_name, last_name, is_active, is_superuser)
    VALUES 
        ('admin', 'admin@technicia.test', crypt('StrongPassword123!', gen_salt('bf')), 'Admin', 'Système', true, true),
        ('testuser', 'user@technicia.test', crypt('StrongPassword123!', gen_salt('bf')), 'Test', 'Utilisateur', true, false),
        ('tester', 'tester@technicia.test', crypt('StrongPassword123!', gen_salt('bf')), 'Test', 'Testeur', true, false)
    ON CONFLICT (email) DO NOTHING;

    -- Récupérer les IDs des utilisateurs créés
    SELECT id INTO admin_id FROM users.users WHERE email = 'admin@technicia.test';
    SELECT id INTO user_id FROM users.users WHERE email = 'user@technicia.test';
    SELECT id INTO tester_id FROM users.users WHERE email = 'tester@technicia.test';
    
    -- Récupérer les IDs des rôles
    SELECT id INTO admin_role_id FROM users.roles WHERE name = 'admin';
    SELECT id INTO user_role_id FROM users.roles WHERE name = 'user';
    SELECT id INTO tester_role_id FROM users.roles WHERE name = 'tester';
    
    -- Associer les utilisateurs aux rôles
    INSERT INTO users.user_roles (user_id, role_id)
    VALUES 
        (admin_id, admin_role_id),
        (user_id, user_role_id),
        (tester_id, tester_role_id)
    ON CONFLICT DO NOTHING;
    
    -- Insérer des préférences utilisateur
    INSERT INTO users.user_settings (user_id, settings)
    VALUES
        (admin_id, '{"theme": "dark", "language": "fr", "notifications": true, "pageSize": 25}'),
        (user_id, '{"theme": "light", "language": "fr", "notifications": true, "pageSize": 10}'),
        (tester_id, '{"theme": "system", "language": "fr", "notifications": false, "pageSize": 50}')
    ON CONFLICT (user_id) DO NOTHING;
    
    -- Insérer des documents fictifs pour les tests
    INSERT INTO ocr.documents (
        user_id, title, original_filename, file_path, file_size, mime_type, md5_hash, 
        status, is_public, metadata, tags
    )
    VALUES
        (
            admin_id, 
            'Facture EDF Mars 2025', 
            'facture_edf_mars_2025.pdf', 
            '/data/documents/2025/03/facture_edf_mars_2025.pdf', 
            245678, 
            'application/pdf', 
            md5('facture_edf_mars_2025.pdf'), 
            'processed', 
            false, 
            '{"type": "facture", "fournisseur": "EDF", "montant": 79.95, "date": "2025-03-15"}',
            ARRAY['facture', 'électricité', 'mars2025']
        ),
        (
            admin_id, 
            'Contrat d''assurance', 
            'contrat_assurance_2025.pdf', 
            '/data/documents/2025/01/contrat_assurance_2025.pdf', 
            1245678, 
            'application/pdf', 
            md5('contrat_assurance_2025.pdf'), 
            'processed', 
            false, 
            '{"type": "contrat", "assureur": "MMA", "montant_annuel": 459.99, "date_debut": "2025-01-01", "date_fin": "2025-12-31"}',
            ARRAY['contrat', 'assurance', '2025']
        ),
        (
            user_id, 
            'Relevé bancaire Janvier 2025', 
            'releve_bancaire_01_2025.pdf', 
            '/data/documents/2025/01/releve_bancaire_01_2025.pdf', 
            156789, 
            'application/pdf', 
            md5('releve_bancaire_01_2025.pdf'), 
            'processed', 
            false, 
            '{"type": "relevé", "banque": "Crédit Mutuel", "mois": "janvier", "année": 2025, "solde": 1250.45}',
            ARRAY['relevé', 'banque', 'janvier2025']
        ),
        (
            user_id, 
            'Facture Téléphone Février 2025', 
            'facture_mobile_02_2025.pdf', 
            '/data/documents/2025/02/facture_mobile_02_2025.pdf', 
            98765, 
            'application/pdf', 
            md5('facture_mobile_02_2025.pdf'), 
            'processing', 
            false, 
            '{"type": "facture", "fournisseur": "Orange", "montant": 29.99, "date": "2025-02-15"}',
            ARRAY['facture', 'téléphone', 'février2025']
        ),
        (
            tester_id, 
            'Document test OCR 1', 
            'test_ocr_01.png', 
            '/data/documents/tests/test_ocr_01.png', 
            256789, 
            'image/png', 
            md5('test_ocr_01.png'), 
            'uploaded', 
            true, 
            '{"type": "test", "contenu": "texte formaté", "langue": "français"}',
            ARRAY['test', 'ocr', 'png']
        ),
        (
            tester_id, 
            'Document test OCR 2', 
            'test_ocr_02.tiff', 
            '/data/documents/tests/test_ocr_02.tiff', 
            1589456, 
            'image/tiff', 
            md5('test_ocr_02.tiff'), 
            'uploaded', 
            true, 
            '{"type": "test", "contenu": "tableau complexe", "langue": "français"}',
            ARRAY['test', 'ocr', 'tiff', 'tableau']
        );
    
    -- Récupérer les IDs des documents
    DECLARE
        doc1_id UUID;
        doc2_id UUID;
        doc3_id UUID;
        doc4_id UUID;
        doc5_id UUID;
        doc6_id UUID;
    BEGIN
        SELECT id INTO doc1_id FROM ocr.documents WHERE original_filename = 'facture_edf_mars_2025.pdf';
        SELECT id INTO doc2_id FROM ocr.documents WHERE original_filename = 'contrat_assurance_2025.pdf';
        SELECT id INTO doc3_id FROM ocr.documents WHERE original_filename = 'releve_bancaire_01_2025.pdf';
        SELECT id INTO doc4_id FROM ocr.documents WHERE original_filename = 'facture_mobile_02_2025.pdf';
        SELECT id INTO doc5_id FROM ocr.documents WHERE original_filename = 'test_ocr_01.png';
        SELECT id INTO doc6_id FROM ocr.documents WHERE original_filename = 'test_ocr_02.tiff';
        
        -- Ajouter des pages aux documents
        -- Document 1: Facture EDF
        INSERT INTO ocr.document_pages (document_id, page_number, image_path, width, height, dpi, status, processed_at)
        VALUES
            (doc1_id, 1, '/data/images/2025/03/facture_edf_mars_2025_p1.png', 2480, 3508, 300, 'processed', NOW() - interval '2 days');
        
        -- Document 2: Contrat d'assurance (multi-pages)
        INSERT INTO ocr.document_pages (document_id, page_number, image_path, width, height, dpi, status, processed_at)
        VALUES
            (doc2_id, 1, '/data/images/2025/01/contrat_assurance_2025_p1.png', 2480, 3508, 300, 'processed', NOW() - interval '3 days'),
            (doc2_id, 2, '/data/images/2025/01/contrat_assurance_2025_p2.png', 2480, 3508, 300, 'processed', NOW() - interval '3 days'),
            (doc2_id, 3, '/data/images/2025/01/contrat_assurance_2025_p3.png', 2480, 3508, 300, 'processed', NOW() - interval '3 days'),
            (doc2_id, 4, '/data/images/2025/01/contrat_assurance_2025_p4.png', 2480, 3508, 300, 'processed', NOW() - interval '3 days');
        
        -- Document 3: Relevé bancaire
        INSERT INTO ocr.document_pages (document_id, page_number, image_path, width, height, dpi, status, processed_at)
        VALUES
            (doc3_id, 1, '/data/images/2025/01/releve_bancaire_01_2025_p1.png', 2480, 3508, 300, 'processed', NOW() - interval '10 days'),
            (doc3_id, 2, '/data/images/2025/01/releve_bancaire_01_2025_p2.png', 2480, 3508, 300, 'processed', NOW() - interval '10 days');
        
        -- Document 4: Facture téléphone (en cours de traitement)
        INSERT INTO ocr.document_pages (document_id, page_number, image_path, width, height, dpi, status)
        VALUES
            (doc4_id, 1, '/data/images/2025/02/facture_mobile_02_2025_p1.png', 2480, 3508, 300, 'processing');
        
        -- Document 5: Test OCR 1
        INSERT INTO ocr.document_pages (document_id, page_number, image_path, width, height, dpi, status)
        VALUES
            (doc5_id, 1, '/data/images/tests/test_ocr_01.png', 1240, 1754, 150, 'pending');
        
        -- Document 6: Test OCR 2
        INSERT INTO ocr.document_pages (document_id, page_number, image_path, width, height, dpi, status)
        VALUES
            (doc6_id, 1, '/data/images/tests/test_ocr_02.png', 2480, 3508, 300, 'pending');
        
        -- Ajouter des résultats OCR pour certaines pages
        -- Récupérer les IDs des pages
        DECLARE
            page1_id UUID;
            page2_id UUID;
            page3_id UUID;
            page4_id UUID;
            page5_id UUID;
            page6_id UUID;
            page7_id UUID;
        BEGIN
            SELECT id INTO page1_id FROM ocr.document_pages WHERE document_id = doc1_id AND page_number = 1;
            SELECT id INTO page2_id FROM ocr.document_pages WHERE document_id = doc2_id AND page_number = 1;
            SELECT id INTO page3_id FROM ocr.document_pages WHERE document_id = doc2_id AND page_number = 2;
            SELECT id INTO page4_id FROM ocr.document_pages WHERE document_id = doc3_id AND page_number = 1;
            SELECT id INTO page5_id FROM ocr.document_pages WHERE document_id = doc3_id AND page_number = 2;
            
            -- Ajouter des résultats OCR pour certaines pages
            INSERT INTO ocr.ocr_results (page_id, ocr_engine, language, confidence, full_text, processing_time)
            VALUES
                (page1_id, 'tesseract', 'fra', 0.89, 'EDF
Facture d''électricité
Référence client: EDF123456789
Date de facturation: 15/03/2025
Montant total: 79,95 €
Période de consommation: 15/02/2025 - 14/03/2025
Consommation: 456 kWh', 1250),
                (page2_id, 'tesseract', 'fra', 0.92, 'CONTRAT D''ASSURANCE
MMA Assurances
Numéro de contrat: AS987654321
Date de début: 01/01/2025
Date de fin: 31/12/2025
Montant annuel: 459,99 €
Paiement mensuel: 38,33 €', 1540),
                (page3_id, 'tesseract', 'fra', 0.87, 'DÉTAIL DES GARANTIES
- Responsabilité civile: Inclus
- Protection juridique: Inclus
- Assistance 24/7: Inclus
- Garantie accidents: Inclus
Franchise: 150 €', 1320),
                (page4_id, 'tesseract', 'fra', 0.91, 'CRÉDIT MUTUEL
Relevé de compte
Période: 01/01/2025 - 31/01/2025
IBAN: FR76 1234 5678 9012 3456 7890 123
Solde au 01/01/2025: 1050,75 €
Solde au 31/01/2025: 1250,45 €', 980),
                (page5_id, 'tesseract', 'fra', 0.88, 'DÉTAIL DES OPÉRATIONS
01/01/2025 - Virement entrant - Salaire - +1500,00 €
05/01/2025 - Prélèvement - Loyer - -650,00 €
10/01/2025 - Carte bancaire - Supermarché - -125,30 €
15/01/2025 - Prélèvement - Assurance - -45,00 €
20/01/2025 - Carte bancaire - Restaurant - -65,00 €
25/01/2025 - Virement sortant - Épargne - -415,00 €', 1050);
            
            -- Ajouter des tâches OCR
            INSERT INTO ocr.ocr_tasks (document_id, user_id, status, priority, progress, started_at, completed_at)
            VALUES
                (doc1_id, admin_id, 'completed', 0, 100, NOW() - interval '2 days 1 hour', NOW() - interval '2 days'),
                (doc2_id, admin_id, 'completed', 0, 100, NOW() - interval '3 days 2 hours', NOW() - interval '3 days'),
                (doc3_id, user_id, 'completed', 0, 100, NOW() - interval '10 days 3 hours', NOW() - interval '10 days'),
                (doc4_id, user_id, 'processing', 0, 45, NOW() - interval '1 hour', NULL),
                (doc5_id, tester_id, 'pending', 1, 0, NULL, NULL),
                (doc6_id, tester_id, 'pending', 2, 0, NULL, NULL);
            
            -- Ajouter des zones d'intérêt sur certains documents
            INSERT INTO ocr.zones_of_interest (document_id, name, description, x_coord, y_coord, width, height, page_number, category, created_by)
            VALUES
                (doc1_id, 'Montant total', 'Zone contenant le montant total de la facture', 350, 450, 200, 50, 1, 'montant', admin_id),
                (doc1_id, 'Référence client', 'Zone contenant la référence client', 200, 300, 250, 50, 1, 'référence', admin_id),
                (doc2_id, 'Numéro de contrat', 'Zone contenant le numéro de contrat', 250, 250, 300, 50, 1, 'référence', admin_id),
                (doc2_id, 'Montant annuel', 'Zone contenant le montant annuel du contrat', 350, 450, 200, 50, 1, 'montant', admin_id),
                (doc3_id, 'IBAN', 'Zone contenant l''IBAN du compte', 200, 350, 400, 50, 1, 'référence', user_id),
                (doc3_id, 'Solde final', 'Zone contenant le solde final du compte', 350, 420, 200, 50, 1, 'montant', user_id);
            
            -- Ajouter des données extraites structurées
            INSERT INTO ocr.structured_extractions (document_id, field_name, field_value, confidence, extraction_method, page_number, x_coord, y_coord, width, height)
            VALUES
                (doc1_id, 'montant_total', '79,95', 0.95, 'template', 1, 350, 450, 200, 50),
                (doc1_id, 'reference_client', 'EDF123456789', 0.98, 'template', 1, 200, 300, 250, 50),
                (doc1_id, 'date_facturation', '15/03/2025', 0.94, 'template', 1, 250, 350, 250, 50),
                (doc2_id, 'numero_contrat', 'AS987654321', 0.97, 'template', 1, 250, 250, 300, 50),
                (doc2_id, 'montant_annuel', '459,99', 0.96, 'template', 1, 350, 450, 200, 50),
                (doc2_id, 'date_debut', '01/01/2025', 0.93, 'template', 1, 250, 350, 250, 50),
                (doc2_id, 'date_fin', '31/12/2025', 0.93, 'template', 1, 250, 400, 250, 50),
                (doc3_id, 'iban', 'FR76 1234 5678 9012 3456 7890 123', 0.99, 'template', 1, 200, 350, 400, 50),
                (doc3_id, 'solde_initial', '1050,75', 0.94, 'template', 1, 350, 380, 200, 50),
                (doc3_id, 'solde_final', '1250,45', 0.95, 'template', 1, 350, 420, 200, 50);
            
            -- Insérer des statistiques OCR
            INSERT INTO stats.ocr_statistics (user_id, document_id, ocr_engine, document_count, page_count, character_count, processing_time, accuracy, date)
            VALUES
                (admin_id, doc1_id, 'tesseract', 1, 1, 245, 1250, 0.89, CURRENT_DATE - interval '2 days'),
                (admin_id, doc2_id, 'tesseract', 1, 4, 1245, 5490, 0.91, CURRENT_DATE - interval '3 days'),
                (user_id, doc3_id, 'tesseract', 1, 2, 876, 2030, 0.90, CURRENT_DATE - interval '10 days');
            
            -- Insérer des logs d'audit
            INSERT INTO audit.audit_logs (user_id, action, entity_type, entity_id, details, occurred_at)
            VALUES
                (admin_id, 'upload', 'document', doc1_id::text, '{"filename": "facture_edf_mars_2025.pdf", "size": 245678}', NOW() - interval '2 days 2 hours'),
                (admin_id, 'process', 'document', doc1_id::text, '{"ocr_engine": "tesseract", "language": "fra"}', NOW() - interval '2 days 1 hour'),
                (admin_id, 'complete', 'document', doc1_id::text, '{"status": "success", "processing_time": 1250}', NOW() - interval '2 days'),
                (admin_id, 'upload', 'document', doc2_id::text, '{"filename": "contrat_assurance_2025.pdf", "size": 1245678}', NOW() - interval '3 days 3 hours'),
                (admin_id, 'process', 'document', doc2_id::text, '{"ocr_engine": "tesseract", "language": "fra"}', NOW() - interval '3 days 2 hours'),
                (admin_id, 'complete', 'document', doc2_id::text, '{"status": "success", "processing_time": 5490}', NOW() - interval '3 days'),
                (user_id, 'upload', 'document', doc3_id::text, '{"filename": "releve_bancaire_01_2025.pdf", "size": 156789}', NOW() - interval '10 days 4 hours'),
                (user_id, 'process', 'document', doc3_id::text, '{"ocr_engine": "tesseract", "language": "fra"}', NOW() - interval '10 days 3 hours'),
                (user_id, 'complete', 'document', doc3_id::text, '{"status": "success", "processing_time": 2030}', NOW() - interval '10 days'),
                (user_id, 'upload', 'document', doc4_id::text, '{"filename": "facture_mobile_02_2025.pdf", "size": 98765}', NOW() - interval '1 hour 30 minutes'),
                (user_id, 'process', 'document', doc4_id::text, '{"ocr_engine": "tesseract", "language": "fra"}', NOW() - interval '1 hour'),
                (tester_id, 'upload', 'document', doc5_id::text, '{"filename": "test_ocr_01.png", "size": 256789}', NOW() - interval '5 hours'),
                (tester_id, 'upload', 'document', doc6_id::text, '{"filename": "test_ocr_02.tiff", "size": 1589456}', NOW() - interval '4 hours'),
                (admin_id, 'login', 'user', admin_id::text, '{"ip": "192.168.1.100", "browser": "Chrome"}', NOW() - interval '3 days 5 hours'),
                (user_id, 'login', 'user', user_id::text, '{"ip": "192.168.1.101", "browser": "Firefox"}', NOW() - interval '10 days 6 hours'),
                (tester_id, 'login', 'user', tester_id::text, '{"ip": "192.168.1.102", "browser": "Edge"}', NOW() - interval '5 hours 30 minutes');
            
            -- Insérer des statistiques d'activité utilisateur
            INSERT INTO stats.user_activity (user_id, action, details)
            VALUES
                (admin_id, 'login', '{"ip": "192.168.1.100", "browser": "Chrome"}'),
                (admin_id, 'upload', '{"document_count": 2, "total_size": 1491356}'),
                (admin_id, 'ocr', '{"document_count": 2, "page_count": 5, "success_rate": 1.0}'),
                (user_id, 'login', '{"ip": "192.168.1.101", "browser": "Firefox"}'),
                (user_id, 'upload', '{"document_count": 2, "total_size": 255554}'),
                (user_id, 'ocr', '{"document_count": 2, "page_count": 3, "success_rate": 0.67}'),
                (tester_id, 'login', '{"ip": "192.168.1.102", "browser": "Edge"}'),
                (tester_id, 'upload', '{"document_count": 2, "total_size": 1846245}');
        END;
    END;
END;
$$;

COMMIT;

-- Fin du script de données de test
SELECT 'Données de test importées avec succès' AS status;
