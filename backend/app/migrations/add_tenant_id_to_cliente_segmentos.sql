-- =====================================================
-- MIGRATION: Adicionar tenant_id à tabela cliente_segmentos
-- Data: 27/01/2026
-- Descrição: Migração para suporte multi-tenant
-- =====================================================

-- 1) Adicionar coluna tenant_id (permitindo NULL temporariamente)
ALTER TABLE cliente_segmentos
ADD COLUMN IF NOT EXISTS tenant_id UUID;

-- 2) Se há dados existentes, atualizar com tenant padrão
-- IMPORTANTE: Ajustar o UUID conforme seu tenant de desenvolvimento
UPDATE cliente_segmentos
SET tenant_id = '7be8dad7-8956-4758-b7bc-855a5259fe2b'
WHERE tenant_id IS NULL;

-- 3) Tornar coluna obrigatória
ALTER TABLE cliente_segmentos
ALTER COLUMN tenant_id SET NOT NULL;

-- 4) Criar índice para performance e isolamento
CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_tenant
ON cliente_segmentos (tenant_id);

-- 5) Criar índice composto para queries otimizadas
CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_tenant_cliente
ON cliente_segmentos (tenant_id, cliente_id);

-- 6) Remover constraint antiga e criar nova
ALTER TABLE cliente_segmentos
DROP CONSTRAINT IF EXISTS cliente_segmentos_cliente_id_user_id_key;

-- 7) Adicionar constraint única com tenant_id
ALTER TABLE cliente_segmentos
ADD CONSTRAINT cliente_segmentos_tenant_cliente_unique
UNIQUE (tenant_id, cliente_id);

-- =====================================================
-- FIM DA MIGRATION
-- =====================================================
