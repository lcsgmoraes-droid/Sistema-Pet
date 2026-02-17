-- Migration: Sistema de Predecessor/Sucessor para Produtos
-- Data: 2026-02-07
-- Objetivo: Permitir vincular produtos que substituem outros, mantendo histórico consolidado

-- Adicionar colunas de predecessor/sucessor
ALTER TABLE produtos 
ADD COLUMN IF NOT EXISTS produto_predecessor_id INTEGER,
ADD COLUMN IF NOT EXISTS data_descontinuacao TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS motivo_descontinuacao VARCHAR(255);

-- Adicionar foreign key para predecessor (auto-referência)
ALTER TABLE produtos
ADD CONSTRAINT fk_produto_predecessor
FOREIGN KEY (produto_predecessor_id) 
REFERENCES produtos(id)
ON DELETE SET NULL;

-- Criar índice para melhorar performance de buscas
CREATE INDEX IF NOT EXISTS idx_produtos_predecessor 
ON produtos(produto_predecessor_id) 
WHERE produto_predecessor_id IS NOT NULL;

-- Criar índice para produtos descontinuados
CREATE INDEX IF NOT EXISTS idx_produtos_descontinuados
ON produtos(data_descontinuacao)
WHERE data_descontinuacao IS NOT NULL;

-- Comentários para documentação
COMMENT ON COLUMN produtos.produto_predecessor_id IS 'ID do produto que este substitui (cadeia de evolução do produto)';
COMMENT ON COLUMN produtos.data_descontinuacao IS 'Data em que o produto foi descontinuado (substituído por outro)';
COMMENT ON COLUMN produtos.motivo_descontinuacao IS 'Motivo da descontinuação (ex: Mudança de embalagem, Reformulação, etc)';

-- View helper: produtos com informações de predecessor e sucessor
CREATE OR REPLACE VIEW vw_produtos_evolucao AS
SELECT 
    p.id,
    p.nome,
    p.codigo,
    p.ativo,
    p.produto_predecessor_id,
    predecessor.nome as predecessor_nome,
    predecessor.codigo as predecessor_codigo,
    predecessor.data_descontinuacao as predecessor_data_desc,
    p.data_descontinuacao,
    p.motivo_descontinuacao,
    -- Encontrar sucessor (produto que tem este como predecessor)
    sucessor.id as sucessor_id,
    sucessor.nome as sucessor_nome,
    sucessor.codigo as sucessor_codigo,
    -- Status do produto na cadeia
    CASE 
        WHEN p.data_descontinuacao IS NOT NULL AND sucessor.id IS NOT NULL THEN 'DESCONTINUADO'
        WHEN p.produto_predecessor_id IS NOT NULL AND p.data_descontinuacao IS NULL THEN 'SUCESSOR'
        WHEN p.produto_predecessor_id IS NULL AND p.data_descontinuacao IS NULL THEN 'NORMAL'
        ELSE 'DESCONTINUADO_SEM_SUCESSOR'
    END as status_evolucao
FROM produtos p
LEFT JOIN produtos predecessor ON p.produto_predecessor_id = predecessor.id
LEFT JOIN produtos sucessor ON sucessor.produto_predecessor_id = p.id;

COMMENT ON VIEW vw_produtos_evolucao IS 'View que mostra a cadeia de evolução de produtos (predecessor e sucessor)';
