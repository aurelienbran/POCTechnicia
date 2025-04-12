-- Migration 001: Schéma initial de la base de données pour Technicia OCR
-- Version: 1.0
-- Date: 7 avril 2025
--
-- Cette migration crée la structure de base pour le système OCR Technicia,
-- incluant les tables des utilisateurs, des rôles et des autorisations.

BEGIN;

-- Création de la table des utilisateurs
CREATE TABLE IF NOT EXISTS users.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users.users IS 'Utilisateurs du système';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_users_modified_at
BEFORE UPDATE ON users.users
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Création de la table des rôles
CREATE TABLE IF NOT EXISTS users.roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users.roles IS 'Rôles des utilisateurs dans le système';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_roles_modified_at
BEFORE UPDATE ON users.roles
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Création de la table d'association utilisateurs-rôles
CREATE TABLE IF NOT EXISTS users.user_roles (
    user_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES users.roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

COMMENT ON TABLE users.user_roles IS 'Association entre utilisateurs et rôles';

-- Création de la table des permissions
CREATE TABLE IF NOT EXISTS users.permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users.permissions IS 'Permissions disponibles dans le système';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_permissions_modified_at
BEFORE UPDATE ON users.permissions
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Création de la table d'association rôles-permissions
CREATE TABLE IF NOT EXISTS users.role_permissions (
    role_id UUID NOT NULL REFERENCES users.roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES users.permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

COMMENT ON TABLE users.role_permissions IS 'Association entre rôles et permissions';

-- Création de la table des sessions
CREATE TABLE IF NOT EXISTS users.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users.sessions IS 'Sessions utilisateur actives';

-- Création de la table d'audit
CREATE TABLE IF NOT EXISTS audit.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address VARCHAR(45),
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE audit.audit_logs IS 'Journal d''audit pour toutes les actions importantes';

-- Création d'index sur la table d'audit
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type_id ON audit.audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_occurred_at ON audit.audit_logs(occurred_at);

-- Création de la table de configuration des utilisateurs
CREATE TABLE IF NOT EXISTS users.user_settings (
    user_id UUID PRIMARY KEY REFERENCES users.users(id) ON DELETE CASCADE,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users.user_settings IS 'Préférences et configurations spécifiques aux utilisateurs';

-- Trigger pour la mise à jour automatique de la date de modification
CREATE TRIGGER update_user_settings_modified_at
BEFORE UPDATE ON users.user_settings
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Insertion des rôles par défaut
INSERT INTO users.roles (name, description)
VALUES 
    ('admin', 'Administrateur système avec tous les privilèges'),
    ('user', 'Utilisateur standard'),
    ('tester', 'Utilisateur de test avec privilèges spécifiques pour les tests')
ON CONFLICT (name) DO NOTHING;

-- Insertion des permissions par défaut
INSERT INTO users.permissions (code, name, description)
VALUES 
    ('read', 'Lecture', 'Permission de lecture des documents et des données'),
    ('write', 'Écriture', 'Permission de création et de modification des documents'),
    ('delete', 'Suppression', 'Permission de suppression des documents et des données'),
    ('admin', 'Administration', 'Permission d''administration du système'),
    ('test', 'Test', 'Permission de test du système')
ON CONFLICT (code) DO NOTHING;

-- Association des permissions aux rôles
DO $$
DECLARE
    admin_role_id UUID;
    user_role_id UUID;
    tester_role_id UUID;
    read_perm_id UUID;
    write_perm_id UUID;
    delete_perm_id UUID;
    admin_perm_id UUID;
    test_perm_id UUID;
BEGIN
    SELECT id INTO admin_role_id FROM users.roles WHERE name = 'admin';
    SELECT id INTO user_role_id FROM users.roles WHERE name = 'user';
    SELECT id INTO tester_role_id FROM users.roles WHERE name = 'tester';
    
    SELECT id INTO read_perm_id FROM users.permissions WHERE code = 'read';
    SELECT id INTO write_perm_id FROM users.permissions WHERE code = 'write';
    SELECT id INTO delete_perm_id FROM users.permissions WHERE code = 'delete';
    SELECT id INTO admin_perm_id FROM users.permissions WHERE code = 'admin';
    SELECT id INTO test_perm_id FROM users.permissions WHERE code = 'test';
    
    -- Admin a toutes les permissions
    INSERT INTO users.role_permissions (role_id, permission_id)
    VALUES 
        (admin_role_id, read_perm_id),
        (admin_role_id, write_perm_id),
        (admin_role_id, delete_perm_id),
        (admin_role_id, admin_perm_id),
        (admin_role_id, test_perm_id)
    ON CONFLICT DO NOTHING;
    
    -- User a uniquement read et write
    INSERT INTO users.role_permissions (role_id, permission_id)
    VALUES 
        (user_role_id, read_perm_id),
        (user_role_id, write_perm_id)
    ON CONFLICT DO NOTHING;
    
    -- Tester a read, write et test
    INSERT INTO users.role_permissions (role_id, permission_id)
    VALUES 
        (tester_role_id, read_perm_id),
        (tester_role_id, write_perm_id),
        (tester_role_id, test_perm_id)
    ON CONFLICT DO NOTHING;
END
$$;

-- Création des statistiques de base
CREATE TABLE IF NOT EXISTS stats.user_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE stats.user_activity IS 'Activité des utilisateurs pour les statistiques';

-- Création d'index sur la table d'activité
CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON stats.user_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_action ON stats.user_activity(action);
CREATE INDEX IF NOT EXISTS idx_user_activity_occurred_at ON stats.user_activity(occurred_at);

COMMIT;

-- Fin de la migration
SELECT '001_initial_schema.sql exécuté avec succès' AS status;
