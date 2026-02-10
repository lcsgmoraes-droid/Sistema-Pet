-- ============================================================
-- POPULAR PLANO DE CONTAS DRE - Pet Shop Pro
-- ============================================================

-- Obter tenant_id
DO $$
DECLARE
    v_tenant_id UUID;
    v_cat_id INTEGER;
    v_subcat_id INTEGER;
BEGIN
    -- Pegar o tenant_id  (assumindo que existe apenas 1 tenant no dev)
    SELECT id INTO v_tenant_id FROM tenants LIMIT 1;
    
    RAISE NOTICE 'Tenant ID: %', v_tenant_id;
    
    -- =================================================================
    -- 1. RECEITAS DE VENDAS
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Receitas de Vendas', 1, 'RECEITA', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Vendas de Produtos - Pet Food', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Vendas de Produtos - Acessórios', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Vendas de Produtos - Higiene', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Vendas de Produtos - Medicamentos', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Serviços - Banho e Tosa', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Serviços - Veterinário', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Serviços - Hotel/Day Care', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Serviços - Adestramento', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Categoria Receitas de Vendas criada';
    END IF;
    
    -- =================================================================
    -- 2. OUTRAS RECEITAS
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Outras Receitas', 2, 'RECEITA', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Receitas Financeiras', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Descontos Obtidos', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Bonificações de Fornecedores', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Outras Receitas Operacionais', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- =================================================================
    -- 3. CMV
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Custo das Mercadorias Vendidas (CMV)', 4, 'CUSTO', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'CMV - Pet Food', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'CMV - Acessórios', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'CMV - Higiene', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'CMV - Medicamentos', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'CMV - Materiais Serviços', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- =================================================================
    -- 4. CUSTOS DIRETOS DE VENDA
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Custos Diretos de Venda', 5, 'CUSTO', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Fretes sobre Vendas', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Embalagens', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Taxas de Marketplace - Mercado Livre', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Taxas de Marketplace - Shopee', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Taxas de Marketplace - Amazon', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Taxas de Cartão de Crédito', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Taxas de Cartão de Débito', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Taxas PIX/Boleto', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Comissões de Vendas - Vendedores', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Comissões de Vendas - Afiliados', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- =================================================================
    -- 5. DESPESAS COM PESSOAL
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Despesas com Pessoal', 6, 'DESPESA', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Salários - Administrativo', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Salários - Vendas', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Salários - Operacional', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Pró-Labore Sócios', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'INSS Patronal', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'FGTS', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'PIS sobre Folha', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Vale Transporte', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Vale Alimentação/Refeição', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Plano de Saúde', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Férias e 13º Salário', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- =================================================================
    -- 6. DESPESAS DE OCUPAÇÃO
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Despesas de Ocupação', 7, 'DESPESA', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Aluguel - Loja', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Aluguel - Escritório', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Condomínio', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'IPTU', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Energia Elétrica', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Água e Esgoto', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Internet e Telefonia', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Limpeza e Conservação', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- =================================================================
    -- 7. DESPESAS COMERCIAIS
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Despesas Comerciais', 8, 'DESPESA', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Marketing Digital - Google Ads', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Marketing Digital - Facebook/Instagram Ads', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Brindes e Amostras Grátis', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Programas de Fidelidade', 'INDIRETO_RATEAVEL', 'FATURAMENTO', 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- =================================================================
    -- 8. DESPESAS ADMINISTRATIVAS
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Despesas Administrativas', 9, 'DESPESA', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Contabilidade', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Softwares e Sistemas - ERP', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Material de Escritório', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Tarifas Bancárias', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- =================================================================
    -- 9. DESPESAS FINANCEIRAS
    -- =================================================================
    INSERT INTO dre_categorias (tenant_id, nome, ordem, natureza, ativo, created_at, updated_at)
    VALUES (v_tenant_id, 'Despesas Financeiras', 10, 'DESPESA', TRUE, NOW(), NOW())
    ON CONFLICT DO NOTHING
    RETURNING id INTO v_cat_id;
    
    IF v_cat_id IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_id, 'Juros de Empréstimos', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_id, 'Multas e Juros por Atraso', 'CORPORATIVO', NULL, 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    RAISE NOTICE '✅ Plano de Contas DRE criado com sucesso!';
    
END $$;


-- =================================================================
-- POPULAR REGRAS INICIAIS
-- =================================================================

DO $$
DECLARE
    v_tenant_id UUID;
    v_subcat_fretes INTEGER;
    v_subcat_fgts INTEGER;
    v_subcat_aluguel INTEGER;
    v_subcat_energia INTEGER;
BEGIN
    SELECT id INTO v_tenant_id FROM tenants LIMIT 1;
    
    -- Buscar IDs das subcategorias
    SELECT id INTO v_subcat_fretes FROM dre_subcategorias WHERE tenant_id = v_tenant_id AND nome = 'Fretes sobre Vendas' LIMIT 1;
    SELECT id INTO v_subcat_fgts FROM dre_subcategorias WHERE tenant_id = v_tenant_id AND nome = 'FGTS' LIMIT 1;
    SELECT id INTO v_subcat_aluguel FROM dre_subcategorias WHERE tenant_id = v_tenant_id AND nome LIKE 'Aluguel%' LIMIT 1;
    SELECT id INTO v_subcat_energia FROM dre_subcategorias WHERE tenant_id = v_tenant_id AND nome = 'Energia Elétrica' LIMIT 1;
    
    -- Regra: Fretes
    IF v_subcat_fretes IS NOT NULL THEN
        INSERT INTO regras_classificacao_dre (tenant_id, nome, descricao, tipo_regra, origem, criterios, dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas, created_at, updated_at)
        VALUES (v_tenant_id, 'Fretes sobre Vendas', 'Identificação automática de despesas com frete e entrega', 'palavra_chave', 'sistema', 
                '{"palavras": ["frete", "entrega", "entregador", "delivery"], "modo": "any"}', 
                v_subcat_fretes, 90, 95, TRUE, TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- Regra: FGTS
    IF v_subcat_fgts IS NOT NULL THEN
        INSERT INTO regras_classificacao_dre (tenant_id, nome, descricao, tipo_regra, origem, criterios, dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas, created_at, updated_at)
        VALUES (v_tenant_id, 'FGTS', 'Guias e pagamentos de FGTS', 'combo', 'sistema', 
                '{"tipo_documento": "GUIA_FGTS", "palavras": ["fgts"], "modo": "any"}', 
                v_subcat_fgts, 90, 100, TRUE, FALSE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- Regra: Aluguel
    IF v_subcat_aluguel IS NOT NULL THEN
        INSERT INTO regras_classificacao_dre (tenant_id, nome, descricao, tipo_regra, origem, criterios, dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas, created_at, updated_at)
        VALUES (v_tenant_id, 'Aluguel', 'Pagamentos de aluguel e locação', 'palavra_chave', 'sistema', 
                '{"palavras": ["aluguel", "locacao", "locação"], "modo": "any"}', 
                v_subcat_aluguel, 85, 95, TRUE, TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    -- Regra: Energia
    IF v_subcat_energia IS NOT NULL THEN
        INSERT INTO regras_classificacao_dre (tenant_id, nome, descricao, tipo_regra, origem, criterios, dre_subcategoria_id, prioridade, confianca, ativo, sugerir_apenas, created_at, updated_at)
        VALUES (v_tenant_id, 'Energia Elétrica', 'Contas de luz', 'palavra_chave', 'sistema', 
                '{"palavras": ["energia", "luz", "cemig", "copel", "cpfl"], "modo": "any"}', 
                v_subcat_energia, 85, 95, TRUE, TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
    END IF;
    
    RAISE NOTICE '✅ Regras de classificação criadas!';
END $$;


-- =================================================================
-- ATUALIZAR BENEFICIARIOS
-- =================================================================

UPDATE contas_pagar cp
SET beneficiario = c.nome
FROM clientes c
WHERE cp.fornecedor_id = c.id
  AND cp.beneficiario IS NULL;

UPDATE contas_receber cr
SET beneficiario = c.nome
FROM clientes c
WHERE cr.cliente_id = c.id
  AND cr.beneficiario IS NULL;

-- Atualizar afeta_dre para compras de mercadoria
UPDATE contas_pagar
SET afeta_dre = FALSE
WHERE nota_entrada_id IS NOT NULL;

SELECT '✅ Setup DRE completo!' as resultado;

