-- Migração: Adicionar tenant_id à tabela produto_imagens
-- Data: 2026-01-27
-- Descrição: Adiciona coluna tenant_id com referência à tabela tenants

BEGIN;

-- Adicionar coluna tenant_id
ALTER TABLE produto_imagens
ADD COLUMN tenant_id UUID;

-- Preencher tenant_id com base no tenant do produto relacionado
UPDATE produto_imagens pi
SET tenant_id = p.tenant_id
FROM produtos p
WHERE pi.produto_id = p.id;

-- Tornar a coluna NOT NULL após popular
ALTER TABLE produto_imagens
ALTER COLUMN tenant_id SET NOT NULL;

-- Adicionar foreign key constraint
ALTER TABLE produto_imagens
ADD CONSTRAINT fk_produto_imagens_tenant
FOREIGN KEY (tenant_id)
REFERENCES tenants(id)
ON DELETE CASCADE;

-- Criar índice para melhorar performance nas consultas filtradas por tenant
CREATE INDEX idx_produto_imagens_tenant ON produto_imagens(tenant_id);

-- Criar índice composto para consultas que filtram por tenant e produto
CREATE INDEX idx_produto_imagens_tenant_produto ON produto_imagens(tenant_id, produto_id);

COMMIT;
