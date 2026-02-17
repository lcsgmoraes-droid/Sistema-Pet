-- ============================================================
-- MIGRATION: Sistema de Classificação DRE Automática
-- Data: 2026-02-09
-- Descrição: Adiciona campos para aprendizado automático e 
--            cria tabelas de regras de classificação
-- ============================================================

-- ============================================================
-- 1. ADICIONAR CAMPOS EM CONTAS_PAGAR
-- ============================================================

-- Adicionar campos para aprendizado automático
ALTER TABLE contas_pagar 
ADD COLUMN IF NOT EXISTS beneficiario VARCHAR(255),
ADD COLUMN IF NOT EXISTS tipo_documento VARCHAR(50),
ADD COLUMN IF NOT EXISTS afeta_dre BOOLEAN DEFAULT TRUE;

-- Comentários para documentação
COMMENT ON COLUMN contas_pagar.beneficiario IS 'Nome do beneficiário (para aprendizado automático)';
COMMENT ON COLUMN contas_pagar.tipo_documento IS 'PIX, BOLETO, TRANSFERENCIA, GUIA_FGTS, GUIA_INSS, DARF, DARE, CARTAO, CHEQUE';
COMMENT ON COLUMN contas_pagar.afeta_dre IS 'Se FALSE, não entra na DRE (ex: compras de mercadoria para estoque)';

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_contas_pagar_beneficiario ON contas_pagar(tenant_id, beneficiario);
CREATE INDEX IF NOT EXISTS idx_contas_pagar_tipo_documento ON contas_pagar(tenant_id, tipo_documento);
CREATE INDEX IF NOT EXISTS idx_contas_pagar_afeta_dre ON contas_pagar(tenant_id, afeta_dre);

-- Preencher beneficiario com dados de fornecedor existentes
UPDATE contas_pagar cp
SET beneficiario = c.nome_completo
FROM clientes c
WHERE cp.fornecedor_id = c.id
  AND cp.beneficiario IS NULL;

-- Marcar compras de mercadoria como afeta_dre = FALSE
UPDATE contas_pagar
SET afeta_dre = FALSE
WHERE nota_entrada_id IS NOT NULL;


-- ============================================================
-- 2. ADICIONAR CAMPOS EM CONTAS_RECEBER (se necessário)
-- ============================================================

ALTER TABLE contas_receber 
ADD COLUMN IF NOT EXISTS beneficiario VARCHAR(255),
ADD COLUMN IF NOT EXISTS tipo_documento VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_contas_receber_beneficiario ON contas_receber(tenant_id, beneficiario);
CREATE INDEX IF NOT EXISTS idx_contas_receber_tipo_documento ON contas_receber(tenant_id, tipo_documento);

COMMENT ON COLUMN contas_receber.beneficiario IS 'Nome do pagador (cliente)';
COMMENT ON COLUMN contas_receber.tipo_documento IS 'PIX, BOLETO, TRANSFERENCIA, CARTAO_CREDITO, CARTAO_DEBITO, DINHEIRO';

-- Preencher beneficiario com dados de cliente existentes
UPDATE contas_receber cr
SET beneficiario = c.nome_completo
FROM clientes c
WHERE cr.cliente_id = c.id
  AND cr.beneficiario IS NULL;


-- ============================================================
-- 3. CRIAR TABELA DE REGRAS DE CLASSIFICAÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS regras_classificacao_dre (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    
    -- Identificação
    nome VARCHAR(150) NOT NULL,
    descricao TEXT,
    
    -- Tipo e origem
    tipo_regra VARCHAR(50) NOT NULL,  -- beneficiario, palavra_chave, tipo_documento, combo, venda_automatica, nota_entrada
    origem VARCHAR(50) NOT NULL DEFAULT 'sistema',  -- sistema, aprendizado, usuario
    
    -- Critérios (JSONB para flexibilidade)
    criterios JSONB NOT NULL,
    
    -- Classificação a aplicar
    dre_subcategoria_id INTEGER NOT NULL REFERENCES dre_subcategorias(id) ON DELETE CASCADE,
    canal VARCHAR(50),
    
    -- Controle de qualidade
    prioridade INTEGER DEFAULT 100,
    confianca INTEGER DEFAULT 100,  -- 0-100
    aplicacoes_sucesso INTEGER DEFAULT 0,
    aplicacoes_rejeitadas INTEGER DEFAULT 0,
    
    -- Flags
    ativo BOOLEAN DEFAULT TRUE,
    sugerir_apenas BOOLEAN DEFAULT FALSE,
    
    -- Auditoria
    criado_por_user_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_regras_classificacao_tenant ON regras_classificacao_dre(tenant_id);
CREATE INDEX IF NOT EXISTS idx_regras_classificacao_tipo ON regras_classificacao_dre(tenant_id, tipo_regra);
CREATE INDEX IF NOT EXISTS idx_regras_classificacao_ativo ON regras_classificacao_dre(tenant_id, ativo);
CREATE INDEX IF NOT EXISTS idx_regras_classificacao_subcategoria ON regras_classificacao_dre(dre_subcategoria_id);
CREATE INDEX IF NOT EXISTS idx_regras_classificacao_criterios ON regras_classificacao_dre USING GIN (criterios);

-- Comentários
COMMENT ON TABLE regras_classificacao_dre IS 'Regras para classificação automática e sugestões de DRE';
COMMENT ON COLUMN regras_classificacao_dre.criterios IS 'JSON com condições: {"beneficiario": "MÉRCIO", "forma_pagamento": "PIX"}';
COMMENT ON COLUMN regras_classificacao_dre.confianca IS 'Confiança da regra (0-100). Atualizada com base em sucessos/rejeições';
COMMENT ON COLUMN regras_classificacao_dre.sugerir_apenas IS 'TRUE = apenas sugere, FALSE = aplica automaticamente';


-- ============================================================
-- 4. CRIAR TABELA DE HISTÓRICO DE CLASSIFICAÇÕES
-- ============================================================

CREATE TABLE IF NOT EXISTS historico_classificacao_dre (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    
    -- Referência ao lançamento
    tipo_lancamento VARCHAR(20) NOT NULL,  -- 'pagar' ou 'receber'
    lancamento_id INTEGER NOT NULL,
    
    -- Classificação aplicada
    dre_subcategoria_id INTEGER NOT NULL REFERENCES dre_subcategorias(id) ON DELETE CASCADE,
    canal VARCHAR(50),
    
    -- Como foi classificado
    forma_classificacao VARCHAR(50) NOT NULL,  -- automatico_regra, automatico_sistema, sugestao_aceita, manual, reclassificacao
    regra_aplicada_id INTEGER REFERENCES regras_classificacao_dre(id) ON DELETE SET NULL,
    
    -- Snapshot do lançamento
    descricao VARCHAR(255),
    beneficiario VARCHAR(255),
    tipo_documento VARCHAR(50),
    valor BIGINT NOT NULL,  -- Valor em centavos
    
    -- Feedback
    usuario_aceitou BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    
    -- Auditoria
    classificado_por_user_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_historico_classificacao_tenant ON historico_classificacao_dre(tenant_id);
CREATE INDEX IF NOT EXISTS idx_historico_classificacao_lancamento ON historico_classificacao_dre(tenant_id, tipo_lancamento, lancamento_id);
CREATE INDEX IF NOT EXISTS idx_historico_classificacao_subcategoria ON historico_classificacao_dre(dre_subcategoria_id);
CREATE INDEX IF NOT EXISTS idx_historico_classificacao_regra ON historico_classificacao_dre(regra_aplicada_id);
CREATE INDEX IF NOT EXISTS idx_historico_classificacao_forma ON historico_classificacao_dre(tenant_id, forma_classificacao);

COMMENT ON TABLE historico_classificacao_dre IS 'Histórico de todas classificações DRE para aprendizado e auditoria';


-- ============================================================
-- 5. POPULAR REGRAS INICIAIS DO SISTEMA
-- ============================================================

-- REGRA 1: Vendas automáticas (já vem classificado do PDV)
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Vendas PDV/Online (Automático)',
    'Todas as vendas geradas pelo sistema já vêm com classificação DRE',
    'venda_automatica',
    'sistema',
    '{"origem": "venda_id"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome LIKE 'Vendas de Produtos%' LIMIT 1),
    999,
    100,
    TRUE,
    FALSE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.tipo_regra = 'venda_automatica'
);

-- REGRA 2: Compras de mercadoria (não entra na DRE como despesa)
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Compras de Mercadoria (Estoque/CMV)',
    'Boletos de notas fiscais de entrada - vão para estoque, não para DRE diretamente',
    'nota_entrada',
    'sistema',
    '{"origem": "nota_entrada_id"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome LIKE 'CMV%' LIMIT 1),
    999,
    100,
    TRUE,
    FALSE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.tipo_regra = 'nota_entrada'
);

-- REGRA 3: Fretes sobre vendas
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Fretes sobre Vendas',
    'Identificação automática de despesas com frete e entrega',
    'palavra_chave',
    'sistema',
    '{"palavras": ["frete", "entrega", "entregador", "delivery"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome = 'Fretes sobre Vendas' LIMIT 1),
    90,
    95,
    TRUE,
    TRUE  -- Sugere, usuário confirma
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'Fretes sobre Vendas'
);

-- REGRA 4: FGTS
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'FGTS',
    'Guias e pagamentos de FGTS',
    'combo',
    'sistema',
    '{"tipo_documento": "GUIA_FGTS", "palavras": ["fgts"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome = 'FGTS' LIMIT 1),
    90,
    100,
    TRUE,
    FALSE  -- Aplica automaticamente
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'FGTS'
);

-- REGRA 5: INSS Patronal
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'INSS Patronal',
    'Guias e pagamentos de INSS',
    'combo',
    'sistema',
    '{"tipo_documento": "GUIA_INSS", "palavras": ["inss", "previdencia"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome = 'INSS Patronal' LIMIT 1),
    90,
    100,
    TRUE,
    FALSE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'INSS Patronal'
);

-- REGRA 6: Taxas de cartão
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Taxas de Cartão',
    'Taxas de operadoras de cartão',
    'palavra_chave',
    'sistema',
    '{"palavras": ["taxa cartao", "stone", "cielo", "rede", "getnet", "pagseguro", "mercado pago"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome LIKE 'Taxas de Cartão%' LIMIT 1),
    85,
    90,
    TRUE,
    TRUE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'Taxas de Cartão'
);

-- REGRA 7: Aluguel
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Aluguel',
    'Pagamentos de aluguel e locação',
    'palavra_chave',
    'sistema',
    '{"palavras": ["aluguel", "locacao", "locação"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome LIKE 'Aluguel%' LIMIT 1),
    85,
    95,
    TRUE,
    TRUE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'Aluguel'
);

-- REGRA 8: Energia elétrica
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Energia Elétrica',
    'Contas de luz',
    'palavra_chave',
    'sistema',
    '{"palavras": ["energia", "luz", "cemig", "copel", "cpfl", "elektro", "light"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome = 'Energia Elétrica' LIMIT 1),
    85,
    95,
    TRUE,
    TRUE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'Energia Elétrica'
);

-- REGRA 9: Água
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Água e Esgoto',
    'Contas de água',
    'palavra_chave',
    'sistema',
    '{"palavras": ["agua", "água", "esgoto", "saneamento", "sabesp", "copasa"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome = 'Água e Esgoto' LIMIT 1),
    85,
    95,
    TRUE,
    TRUE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'Água e Esgoto'
);

-- REGRA 10: Internet
INSERT INTO regras_classificacao_dre (
    tenant_id, nome, descricao, tipo_regra, origem, criterios, 
    dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas
)
SELECT 
    t.id as tenant_id,
    'Internet e Telefonia',
    'Contas de internet e telefone',
    'palavra_chave',
    'sistema',
    '{"palavras": ["internet", "telefone", "vivo", "claro", "tim", "oi", "net", "sky"], "modo": "any"}'::jsonb,
    (SELECT id FROM dre_subcategorias WHERE tenant_id = t.id AND nome = 'Internet e Telefonia' LIMIT 1),
    85,
    90,
    TRUE,
    TRUE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM regras_classificacao_dre r 
    WHERE r.tenant_id = t.id AND r.nome = 'Internet e Telefonia'
);

COMMENT ON TABLE regras_classificacao_dre IS 'Regras criadas em 2026-02-09 - Sistema de classificação automática DRE';
