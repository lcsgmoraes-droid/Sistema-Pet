-- Migration Sprint 2: Produtos com Variação
-- Data: 2026-01-24
-- Objetivo: Adicionar suporte para produtos PAI e VARIAÇÃO

-- 1. Adicionar coluna tipo_produto (SIMPLES, PAI, VARIACAO)
ALTER TABLE produtos 
ADD COLUMN tipo_produto VARCHAR(20) DEFAULT 'SIMPLES' NOT NULL;

-- 2. Adicionar coluna produto_pai_id (FK para produtos PAI)
ALTER TABLE produtos 
ADD COLUMN produto_pai_id INTEGER NULL;

-- 3. Criar foreign key para produto_pai_id
ALTER TABLE produtos 
ADD CONSTRAINT fk_produto_pai 
FOREIGN KEY (produto_pai_id) REFERENCES produtos(id) 
ON DELETE CASCADE;

-- 4. Criar índice para melhorar performance de queries de variações
CREATE INDEX idx_produtos_tipo_produto ON produtos(tipo_produto);
CREATE INDEX idx_produtos_produto_pai_id ON produtos(produto_pai_id);

-- 5. Atualizar produtos existentes para tipo SIMPLES (já é o padrão, mas garantir)
UPDATE produtos SET tipo_produto = 'SIMPLES' WHERE tipo_produto IS NULL;

-- NOTAS:
-- - Produtos existentes automaticamente são SIMPLES
-- - Produtos PAI: tipo_produto = 'PAI', produto_pai_id = NULL
-- - Produtos VARIACAO: tipo_produto = 'VARIACAO', produto_pai_id = ID do PAI
-- - Produtos SIMPLES: tipo_produto = 'SIMPLES', produto_pai_id = NULL

-- VALIDAÇÃO:
-- SELECT tipo_produto, COUNT(*) FROM produtos GROUP BY tipo_produto;
