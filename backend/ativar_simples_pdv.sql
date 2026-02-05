-- ================================================================================
-- ATIVAR SIMPLES NACIONAL NO PDV (PostgreSQL)
-- ================================================================================

-- 1️⃣ Ativar Simples Nacional com alíquota 6%
UPDATE empresa_config_fiscal
SET
  simples_ativo = true,
  simples_anexo = 'I',
  simples_aliquota_vigente = 6.00,
  simples_ultima_atualizacao = CURRENT_DATE;

-- 2️⃣ Verificar configuração
SELECT
  uf,
  regime_tributario,
  simples_ativo,
  simples_anexo,
  simples_aliquota_vigente,
  simples_ultima_atualizacao
FROM empresa_config_fiscal;

-- ================================================================================
-- RESULTADO ESPERADO:
-- uf | regime_tributario  | simples_ativo | simples_anexo | simples_aliquota_vigente | simples_ultima_atualizacao
-- SP | Simples Nacional   | true          | I             | 6.00                     | 2026-01-31
-- ================================================================================

-- 📝 COMO TESTAR NO PDV:
--
-- 1️⃣ Endpoint de Listagem:
--    GET /api/formas-pagamento/impostos
--    → Deve retornar Simples Nacional 6% como opção
--
-- 2️⃣ Análise de Venda:
--    POST /api/formas-pagamento/analisar-venda
--    → Deve aplicar Simples Nacional 6% automaticamente
--
-- 3️⃣ Para desativar:
--    UPDATE empresa_config_fiscal SET simples_ativo = false;
