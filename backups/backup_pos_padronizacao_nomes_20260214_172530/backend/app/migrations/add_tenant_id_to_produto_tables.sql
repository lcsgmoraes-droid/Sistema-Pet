-- Migração em lote: Adicionar tenant_id às tabelas de produtos
-- Data: 2026-01-27
-- Descrição: Adiciona tenant_id às tabelas que ainda não têm

BEGIN;

-- =============================================================================
-- 1. DEPARTAMENTOS
-- =============================================================================
ALTER TABLE departamentos ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE departamentos d
SET tenant_id = (SELECT tenant_id FROM produtos LIMIT 1)
WHERE tenant_id IS NULL;

ALTER TABLE departamentos ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE departamentos 
ADD CONSTRAINT fk_departamentos_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_departamentos_tenant ON departamentos(tenant_id);

-- =============================================================================
-- 2. PRODUTO_KIT_COMPONENTES
-- =============================================================================
ALTER TABLE produto_kit_componentes ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE produto_kit_componentes pkc
SET tenant_id = p.tenant_id
FROM produtos p
WHERE pkc.kit_id = p.id AND pkc.tenant_id IS NULL;

ALTER TABLE produto_kit_componentes ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE produto_kit_componentes 
ADD CONSTRAINT fk_produto_kit_componentes_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_produto_kit_componentes_tenant ON produto_kit_componentes(tenant_id);

-- =============================================================================
-- 3. PRODUTO_FORNECEDORES
-- =============================================================================
ALTER TABLE produto_fornecedores ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE produto_fornecedores pf
SET tenant_id = p.tenant_id
FROM produtos p
WHERE pf.produto_id = p.id AND pf.tenant_id IS NULL;

ALTER TABLE produto_fornecedores ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE produto_fornecedores 
ADD CONSTRAINT fk_produto_fornecedores_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_produto_fornecedores_tenant ON produto_fornecedores(tenant_id);

-- =============================================================================
-- 4. PRODUTOS_ATRIBUTOS
-- =============================================================================
ALTER TABLE produtos_atributos ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE produtos_atributos pa
SET tenant_id = (SELECT tenant_id FROM produtos LIMIT 1)
WHERE tenant_id IS NULL;

ALTER TABLE produtos_atributos ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE produtos_atributos 
ADD CONSTRAINT fk_produtos_atributos_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_produtos_atributos_tenant ON produtos_atributos(tenant_id);

-- =============================================================================
-- 5. PRODUTOS_ATRIBUTOS_OPCOES
-- =============================================================================
ALTER TABLE produtos_atributos_opcoes ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE produtos_atributos_opcoes pao
SET tenant_id = pa.tenant_id
FROM produtos_atributos pa
WHERE pao.atributo_id = pa.id AND pao.tenant_id IS NULL;

ALTER TABLE produtos_atributos_opcoes ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE produtos_atributos_opcoes 
ADD CONSTRAINT fk_produtos_atributos_opcoes_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_produtos_atributos_opcoes_tenant ON produtos_atributos_opcoes(tenant_id);

-- =============================================================================
-- 6. PRODUTOS_HISTORICO_PRECOS
-- =============================================================================
ALTER TABLE produtos_historico_precos ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE produtos_historico_precos php
SET tenant_id = p.tenant_id
FROM produtos p
WHERE php.produto_id = p.id AND php.tenant_id IS NULL;

ALTER TABLE produtos_historico_precos ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE produtos_historico_precos 
ADD CONSTRAINT fk_produtos_historico_precos_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_produtos_historico_precos_tenant ON produtos_historico_precos(tenant_id);

-- =============================================================================
-- 7. PRODUTOS_VARIACOES_ATRIBUTOS
-- =============================================================================
ALTER TABLE produtos_variacoes_atributos ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE produtos_variacoes_atributos pva
SET tenant_id = pv.tenant_id
FROM product_variations pv
WHERE pva.variacao_id = pv.id AND pva.tenant_id IS NULL;

ALTER TABLE produtos_variacoes_atributos ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE produtos_variacoes_atributos 
ADD CONSTRAINT fk_produtos_variacoes_atributos_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_produtos_variacoes_atributos_tenant ON produtos_variacoes_atributos(tenant_id);

-- =============================================================================
-- 8. LISTAS_PRECO
-- =============================================================================
ALTER TABLE listas_preco ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE listas_preco
SET tenant_id = (SELECT tenant_id FROM produtos LIMIT 1)
WHERE tenant_id IS NULL;

ALTER TABLE listas_preco ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE listas_preco 
ADD CONSTRAINT fk_listas_preco_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_listas_preco_tenant ON listas_preco(tenant_id);

-- =============================================================================
-- 9. PRODUTO_LISTAS_PRECO
-- =============================================================================
ALTER TABLE produto_listas_preco ADD COLUMN IF NOT EXISTS tenant_id UUID;

UPDATE produto_listas_preco plp
SET tenant_id = p.tenant_id
FROM produtos p
WHERE plp.produto_id = p.id AND plp.tenant_id IS NULL;

ALTER TABLE produto_listas_preco ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE produto_listas_preco 
ADD CONSTRAINT fk_produto_listas_preco_tenant 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_produto_listas_preco_tenant ON produto_listas_preco(tenant_id);

COMMIT;
