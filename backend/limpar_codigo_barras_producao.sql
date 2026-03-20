-- ================================================================================================
-- Script SQL: Limpar códigos de barras de produtos PAI e VARIAÇÕES
-- Ambiente: PRODUÇÃO
-- Data: 2026-03-20
-- Descrição: Remove código_barras de todos os produtos com tipo_produto='PAI' e tipo_produto='VARIACAO'
-- ================================================================================================

-- 1. BACKUP: Criar tabela temporária com os dados antes da limpeza
CREATE TEMP TABLE backup_codigo_barras AS
SELECT 
  id,
  codigo,
  nome,
  tipo_produto,
  produto_pai_id,
  codigo_barras,
  NOW() as backup_timestamp
FROM produtos
WHERE (tipo_produto = 'PAI' OR tipo_produto = 'VARIACAO')
  AND codigo_barras IS NOT NULL
  AND tenant_id IS NOT NULL;

-- 2. Confirmar quantidade de registros antes da mudança
SELECT 
  tipo_produto,
  COUNT(*) as quantidade_com_codigo_barras
FROM backup_codigo_barras
GROUP BY tipo_produto
ORDER BY tipo_produto;

-- 3. LIMPEZA: Remover código_barras dos produtos PAI
UPDATE produtos
SET codigo_barras = NULL,
    updated_at = NOW()
WHERE tipo_produto = 'PAI'
  AND codigo_barras IS NOT NULL;

-- 4. LIMPEZA: Remover código_barras dos produtos VARIAÇÃO
UPDATE produtos
SET codigo_barras = NULL,
    updated_at = NOW()
WHERE tipo_produto = 'VARIACAO'
  AND codigo_barras IS NOT NULL;

-- 5. VERIFICAÇÃO: Confirmar que tudo foi limpo
SELECT 
  tipo_produto,
  COUNT(*) as registros_sem_codigo
FROM produtos
WHERE (tipo_produto = 'PAI' OR tipo_produto = 'VARIACAO')
  AND codigo_barras IS NULL
GROUP BY tipo_produto
ORDER BY tipo_produto;

-- 6. SUMMARY: Mostrar backup completo
SELECT 
  'BACKUP ANTES DA LIMPEZA' as status,
  COUNT(*) as total_registros_afetados
FROM backup_codigo_barras;

SELECT * FROM backup_codigo_barras LIMIT 5;
