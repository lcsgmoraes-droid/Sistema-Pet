-- =====================================================
-- MIGRATION: Adicionar tenant_id à tabela marcas
-- Data: 27/01/2026
-- Descrição: Migração para suporte multi-tenant em marcas
-- =====================================================

-- 1) Adicionar coluna tenant_id (permitindo NULL temporariamente)
ALTER TABLE marcas
ADD COLUMN IF NOT EXISTS tenant_id UUID;

-- 2) Atualizar dados existentes com tenant padrão
-- IMPORTANTE: Usar o mesmo tenant dos produtos
UPDATE marcas
SET tenant_id = '7be8dad7-8956-4758-b7bc-855a5259fe2b'
WHERE tenant_id IS NULL;

-- 3) Tornar coluna obrigatória
ALTER TABLE marcas
ALTER COLUMN tenant_id SET NOT NULL;

-- 4) Criar Foreign Key para garantir integridade
ALTER TABLE marcas
ADD CONSTRAINT fk_marcas_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

-- 5) Criar índice para performance e isolamento
CREATE INDEX IF NOT EXISTS idx_marcas_tenant
ON marcas (tenant_id);

-- 6) Criar índice composto para queries otimizadas
CREATE INDEX IF NOT EXISTS idx_marcas_tenant_ativo
ON marcas (tenant_id, ativo);

-- =====================================================
-- FIM DA MIGRATION
-- =====================================================
