-- Criar schema básico para login funcionar
-- Este é um setup mínimo emergencial

-- Tabela tenants
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    nome VARCHAR(255),
    telefone VARCHAR(50),
    cpf_cnpj VARCHAR(20),
    foto_url TEXT,
    consent_date TIMESTAMP WITH TIME ZONE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    backup_codes TEXT,
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMP WITH TIME ZONE,
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    nome_loja VARCHAR(255),
    endereco_loja TEXT,
    telefone_loja VARCHAR(50),
    data_fechamento_comissao INTEGER DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    tenant_id UUID
);

-- Tabela user_tenants (relação many-to-many)
CREATE TABLE IF NOT EXISTS user_tenants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tenant_id)
);

-- Tabela user_sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(36) NOT NULL UNIQUE,
    ip_address VARCHAR(50),
    user_agent TEXT,
    device_info TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(255)
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_jti ON user_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_user_tenants_user_id ON user_tenants(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tenants_tenant_id ON user_tenants(tenant_id);

-- Inserir tenant padrão
INSERT INTO tenants (id, name) 
VALUES ('00000000-0000-0000-0000-000000000001', 'Tenant Padrão')
ON CONFLICT (name) DO NOTHING;

-- Inserir usuário admin (senha: test123)
-- Hash bcrypt de "test123": $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEMule
INSERT INTO users (email, hashed_password, is_active, is_admin, nome, tenant_id)
VALUES ('admin@test.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEMule', TRUE, TRUE, 'Administrador', '00000000-0000-0000-0000-000000000001')
ON CONFLICT (email) DO UPDATE SET 
    hashed_password = EXCLUDED.hashed_password,
    is_active = TRUE,
    is_admin = TRUE;

-- Associar usuário ao tenant
INSERT INTO user_tenants (user_id, tenant_id, role_id)
SELECT u.id, t.id, 1
FROM users u, tenants t
WHERE u.email = 'admin@test.com' 
AND t.name = 'Tenant Padrão'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

SELECT 'Setup concluído!' as status;
