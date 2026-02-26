-- ============================================================
-- MIGRAÇÃO: Configuração DRE + Pagar.me para ecommerce
-- Data: 2026-02-26
-- Objetivo: Criar categorias/subcategorias DRE, operadora Pagar.me
--           e formas de pagamento com taxas do Plano Parcelado.
--           Necessário para que pedidos do ecommerce (via webhook)
--           gerem DRE, contas a receber e contas a pagar (taxas).
-- Executar em: PRODUCAO (após deploy do backend)
-- ============================================================

-- ATENÇÃO: Ajuste o tenant_id abaixo para o UUID do tenant correto
-- Variável: substitua o UUID em todos os lugares abaixo
-- DEV:  7be8dad7-8956-4758-b7bc-855a5259fe2b
-- PROD: verificar no banco com: SELECT DISTINCT tenant_id FROM formas_pagamento LIMIT 5;

-- ----------------------------------------------------------------
-- 1. Categorias DRE (se não existirem)
-- ----------------------------------------------------------------
INSERT INTO dre_categorias (nome, tipo, ativo, tenant_id)
SELECT 'Receitas de Vendas', 'receita', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_categorias
    WHERE nome = 'Receitas de Vendas' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO dre_categorias (nome, tipo, ativo, tenant_id)
SELECT 'CMV - Custo de Produtos', 'despesa', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_categorias
    WHERE nome = 'CMV - Custo de Produtos' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO dre_categorias (nome, tipo, ativo, tenant_id)
SELECT 'Taxas Financeiras', 'despesa', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_categorias
    WHERE nome = 'Taxas Financeiras' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- ----------------------------------------------------------------
-- 2. Subcategorias DRE
-- (categoria_id = buscar pelo nome acima)
-- ----------------------------------------------------------------

-- Receitas
INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Receitas de Vendas - Produtos',
    (SELECT id FROM dre_categorias WHERE nome='Receitas de Vendas' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'AMBOS', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Receitas de Vendas - Produtos' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- CMV
INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'CMV - Custo dos Produtos Vendidos',
    (SELECT id FROM dre_categorias WHERE nome='CMV - Custo de Produtos' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'AMBOS', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'CMV - Custo dos Produtos Vendidos' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- Taxas - PIX
INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxa de PIX - Loja Fisica',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'LOJA_FISICA', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxa de PIX - Loja Fisica' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxa de PIX - E-commerce',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'AMBOS', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxa de PIX - E-commerce' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- Taxas - Cartão de Crédito
INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxas de Cartao de Credito - Loja Fisica',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'LOJA_FISICA', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxas de Cartao de Credito - Loja Fisica' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxas de Cartao de Credito - E-commerce',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'AMBOS', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxas de Cartao de Credito - E-commerce' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- Taxas - Cartão de Débito
INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxas de Cartao de Debito - Loja Fisica',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'LOJA_FISICA', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxas de Cartao de Debito - Loja Fisica' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxas de Cartao de Debito - E-commerce',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'AMBOS', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxas de Cartao de Debito - E-commerce' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- Taxas - Boleto
INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxas de Boleto - Loja Fisica',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'LOJA_FISICA', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxas de Boleto - Loja Fisica' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO dre_subcategorias (nome, categoria_id, tipo_custo, escopo_rateio, ativo, tenant_id)
SELECT
    'Taxas de Boleto - E-commerce',
    (SELECT id FROM dre_categorias WHERE nome='Taxas Financeiras' AND tenant_id='<<TENANT_ID>>'::uuid LIMIT 1),
    'DIRETO', 'AMBOS', true, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM dre_subcategorias
    WHERE nome = 'Taxas de Boleto - E-commerce' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- ----------------------------------------------------------------
-- 3. Operadora Pagar.me
-- ----------------------------------------------------------------
INSERT INTO operadoras_cartao (nome, codigo, max_parcelas, padrao, ativo, taxa_credito_vista, taxa_credito_parcelado, cor, icone, api_enabled, user_id, tenant_id)
SELECT 'Pagar.me', 'PAGARME', 12, false, true, 5.59, 13.59, '#00A868', 'credit-card', false, 1, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM operadoras_cartao WHERE codigo = 'PAGARME' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- ----------------------------------------------------------------
-- 4. Formas de Pagamento Pagar.me (Plano Parcelado)
-- PIX: 1.19% | Crédito à vista: 5.59% | Crédito parcelado: 13.59%
-- Boleto: R$3.49 (taxa fixa) | Recebimento: 15 dias
-- ----------------------------------------------------------------
INSERT INTO formas_pagamento (nome, tipo, taxa_percentual, taxa_fixa, prazo_dias, prazo_recebimento, ativo, user_id, tenant_id)
SELECT 'PIX Pagar.me', 'pix', 1.19, 0.00, 0, 0, true, 1, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM formas_pagamento WHERE nome = 'PIX Pagar.me' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO formas_pagamento (nome, tipo, taxa_percentual, taxa_fixa, prazo_dias, prazo_recebimento, ativo, user_id, tenant_id)
SELECT 'Credito Vista Pagar.me', 'cartao_credito', 5.59, 0.00, 15, 15, true, 1, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM formas_pagamento WHERE nome = 'Credito Vista Pagar.me' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO formas_pagamento (nome, tipo, taxa_percentual, taxa_fixa, prazo_dias, prazo_recebimento, ativo, user_id, tenant_id)
SELECT 'Credito Parcelado Pagar.me', 'cartao_credito', 13.59, 0.00, 15, 15, true, 1, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM formas_pagamento WHERE nome = 'Credito Parcelado Pagar.me' AND tenant_id = '<<TENANT_ID>>'::uuid
);

INSERT INTO formas_pagamento (nome, tipo, taxa_percentual, taxa_fixa, prazo_dias, prazo_recebimento, ativo, user_id, tenant_id)
SELECT 'Boleto Pagar.me', 'boleto', 0.00, 3.49, 15, 15, true, 1, '<<TENANT_ID>>'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM formas_pagamento WHERE nome = 'Boleto Pagar.me' AND tenant_id = '<<TENANT_ID>>'::uuid
);

-- FIM DA MIGRAÇÃO
