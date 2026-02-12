-- ============================================================================
-- MIGRATION: Recriar tabelas Especies e Racas com tipos corretos
-- Data: 2026-02-07
-- ============================================================================

-- PASSO 1: Dropar tabelas antigas (se existirem)
DROP TABLE IF EXISTS racas CASCADE;
DROP TABLE IF EXISTS especies CASCADE;

-- PASSO 2: Criar tabela especies
CREATE TABLE especies (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    nome VARCHAR(100) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_especies_tenant_id ON especies(tenant_id);
CREATE INDEX idx_especies_nome ON especies(nome);
CREATE INDEX idx_especies_ativo ON especies(ativo);

-- PASSO 3: Criar tabela racas
CREATE TABLE racas (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    nome VARCHAR(100) NOT NULL,
    especie_id INTEGER NOT NULL REFERENCES especies(id) ON DELETE RESTRICT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_racas_tenant_id ON racas(tenant_id);
CREATE INDEX idx_racas_nome ON racas(nome);
CREATE INDEX idx_racas_especie_id ON racas(especie_id);
CREATE INDEX idx_racas_ativo ON racas(ativo);

-- ============================================================================
-- DADOS PADRÃO: Espécies e Raças (será aplicado pelo backend)
-- ============================================================================

-- Fim da migration
