-- ============================================================
-- SEGREGAR FRETES POR CANAL E TIPO
-- Data: 2026-02-09
-- ============================================================
-- 
-- MUDANÇAS:
-- 1. Desativar "Fretes sobre Vendas" (genérico)
-- 2. Criar "Taxa de Frete" (Receita) por canal
-- 3. Criar "Frete Operacional" (Custo Direto) por canal
-- 4. Criar "Fretes sobre Compras" (CMV)
-- ============================================================

DO $$
DECLARE
    v_tenant_id UUID;
    v_cat_receitas INTEGER;
    v_cat_custos_diretos INTEGER;
    v_cat_cmv INTEGER;
BEGIN
    -- Pegar o tenant_id (assumindo que existe apenas 1 tenant no dev)
    SELECT id INTO v_tenant_id FROM tenants LIMIT 1;
    
    RAISE NOTICE 'Tenant ID: %', v_tenant_id;
    
    -- ================================================================
    -- ETAPA 1: DESATIVAR SUBCATEGORIA ANTIGA
    -- ================================================================
    
    UPDATE dre_subcategorias
    SET ativo = FALSE,
        nome = 'Fretes sobre Vendas (DESCONTINUADO)',
        updated_at = NOW()
    WHERE tenant_id = v_tenant_id 
      AND nome = 'Fretes sobre Vendas';
    
    RAISE NOTICE '✅ Subcategoria antiga desativada';
    
    -- ================================================================
    -- ETAPA 2: CRIAR TAXAS DE FRETE (RECEITA) POR CANAL
    -- ================================================================
    -- Taxa de frete é paga pelo cliente, entra como RECEITA
    
    SELECT id INTO v_cat_receitas 
    FROM dre_categorias 
    WHERE tenant_id = v_tenant_id 
      AND nome = 'Outras Receitas' 
    LIMIT 1;
    
    IF v_cat_receitas IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_receitas, 'Taxa de Frete - Loja Física', 'DIRETO', NULL, 'LOJA_FISICA', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_receitas, 'Taxa de Frete - Mercado Livre', 'DIRETO', NULL, 'ONLINE', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_receitas, 'Taxa de Frete - Shopee', 'DIRETO', NULL, 'ONLINE', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_receitas, 'Taxa de Frete - Amazon', 'DIRETO', NULL, 'ONLINE', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE '✅ Taxas de Frete (Receita) criadas por canal';
    ELSE
        RAISE NOTICE '⚠️ Categoria Outras Receitas não encontrada';
    END IF;
    
    -- ================================================================
    -- ETAPA 3: CRIAR FRETES OPERACIONAIS (CUSTO DIRETO) POR CANAL
    -- ================================================================
    -- Frete operacional é custo da empresa, independente do cliente pagar ou não
    
    SELECT id INTO v_cat_custos_diretos 
    FROM dre_categorias 
    WHERE tenant_id = v_tenant_id 
      AND nome = 'Custos Diretos de Venda' 
    LIMIT 1;
    
    IF v_cat_custos_diretos IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_custos_diretos, 'Frete Operacional - Loja Física', 'DIRETO', NULL, 'LOJA_FISICA', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_custos_diretos, 'Frete Operacional - Mercado Livre', 'DIRETO', NULL, 'ONLINE', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_custos_diretos, 'Frete Operacional - Shopee', 'DIRETO', NULL, 'ONLINE', TRUE, NOW(), NOW()),
        (v_tenant_id, v_cat_custos_diretos, 'Frete Operacional - Amazon', 'DIRETO', NULL, 'ONLINE', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE '✅ Fretes Operacionais (Custo Direto) criados por canal';
    ELSE
        RAISE NOTICE '⚠️ Categoria Custos Diretos de Venda não encontrada';
    END IF;
    
    -- ================================================================
    -- ETAPA 4: CRIAR FRETES SOBRE COMPRAS (CMV)
    -- ================================================================
    -- Frete pago na compra de mercadorias, integra o custo de aquisição
    
    SELECT id INTO v_cat_cmv 
    FROM dre_categorias 
    WHERE tenant_id = v_tenant_id 
      AND nome LIKE 'Custo das Mercadorias Vendidas%' 
    LIMIT 1;
    
    IF v_cat_cmv IS NOT NULL THEN
        INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo, created_at, updated_at) VALUES
        (v_tenant_id, v_cat_cmv, 'Fretes sobre Compras', 'DIRETO', NULL, 'AMBOS', TRUE, NOW(), NOW())
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE '✅ Fretes sobre Compras (CMV) criada';
    ELSE
        RAISE NOTICE '⚠️ Categoria CMV não encontrada';
    END IF;
    
    -- ================================================================
    -- ETAPA 5: ATUALIZAR REGRAS DE CLASSIFICAÇÃO
    -- ================================================================
    
    -- Desativar regra antiga de fretes sobre vendas
    UPDATE regras_classificacao_dre
    SET ativo = FALSE,
        sugerir_apenas = TRUE,
        updated_at = NOW()
    WHERE tenant_id = v_tenant_id 
      AND nome = 'Fretes sobre Vendas';
    
    RAISE NOTICE '✅ Regra antiga de fretes desativada';
    
    RAISE NOTICE '🎉 Segregação de fretes concluída com sucesso!';
    RAISE NOTICE '';
    RAISE NOTICE '📊 RESUMO:';
    RAISE NOTICE '  • Taxas de Frete (Receita): 4 subcategorias criadas';
    RAISE NOTICE '  • Fretes Operacionais (Custo Direto): 4 subcategorias criadas';
    RAISE NOTICE '  • Fretes sobre Compras (CMV): 1 subcategoria criada';
    RAISE NOTICE '  • Total: 9 novas subcategorias';
    
END $$;
