-- ============================================================================
-- CRIAR SUBCATEGORIAS DRE PARA TAXAS DE PAGAMENTO POR CANAL
-- ============================================================================
-- Data: 2026-02-09
-- Objetivo: Criar subcategorias específicas para lançamento de taxas de 
--           pagamento (cartão crédito, débito, PIX) por canal de venda
-- 
-- Estrutura:
-- - Categoria: Custos Diretos de Venda (ID 6)
-- - Subcategorias novas:
--   * Taxas de Cartão de Crédito - Loja Física (inclui PDV)
--   * Taxas de Cartão de Débito - Loja Física (inclui PDV)
--   * Taxa de PIX - Loja Física (inclui PDV)
-- 
-- Nota: PDV e Loja Física são a mesma coisa, não precisam de subcategorias separadas
-- 
-- Mantém compatibilidade com subcategorias genéricas existentes:
-- - ID 24: Taxas de Cartão de Crédito
-- - ID 25: Taxas de Cartão de Débito
-- - ID 26: Taxas PIX/Boleto
-- ============================================================================

DO $$
DECLARE
    v_tenant_id UUID;
    v_categoria_custos_diretos_id INT;
    v_count INT;
BEGIN
    -- Loop por cada tenant
    FOR v_tenant_id IN SELECT DISTINCT tenant_id FROM dre_categorias WHERE tenant_id IS NOT NULL
    LOOP
        RAISE NOTICE '🏢 Processando tenant: %', v_tenant_id;
        
        -- Buscar ID da categoria "Custos Diretos de Venda"
        SELECT id INTO v_categoria_custos_diretos_id
        FROM dre_categorias
        WHERE tenant_id = v_tenant_id
          AND nome = 'Custos Diretos de Venda'
        LIMIT 1;
        
        IF v_categoria_custos_diretos_id IS NULL THEN
            RAISE NOTICE '⚠️  Categoria "Custos Diretos de Venda" não encontrada para tenant %', v_tenant_id;
            CONTINUE;
        END IF;
        
        RAISE NOTICE '✅ Categoria encontrada: ID %', v_categoria_custos_diretos_id;
        
        -- ============================================================================
        -- CANAL: LOJA FÍSICA (inclui PDV - são a mesma coisa)
        -- ============================================================================
        
        -- 1. Taxas de Cartão de Crédito - Loja Física
        SELECT COUNT(*) INTO v_count
        FROM dre_subcategorias
        WHERE tenant_id = v_tenant_id
          AND nome = 'Taxas de Cartão de Crédito - Loja Física';
        
        IF v_count = 0 THEN
            INSERT INTO dre_subcategorias (
                tenant_id,
                categoria_id,
                nome,
                tipo_custo,
                base_rateio,
                escopo_rateio,
                ativo,
                created_at,
                updated_at
            ) VALUES (
                v_tenant_id,
                v_categoria_custos_diretos_id,
                'Taxas de Cartão de Crédito - PDV',
                'DIRETO',
                NULL,
                'AMBOS',
                TRUE,
                NOW(),
                NOW()
            );
            RAISE NOTICE '✅ Criada: Taxas de Cartão de Crédito - Loja Física';
        ELSE
            RAISE NOTICE '⏭️  Já existe: Taxas de Cartão de Crédito - Loja Física';
        END IF;
        
        -- 2. Taxas de Cartão de Débito - Loja Física
        SELECT COUNT(*) INTO v_count
        FROM dre_subcategorias
        WHERE tenant_id = v_tenant_id
          AND nome = 'Taxas de Cartão de Débito - Loja Física';
        
        IF v_count = 0 THEN
            INSERT INTO dre_subcategorias (
                tenant_id,
                categoria_id,
                nome,
                tipo_custo,
                base_rateio,
                escopo_rateio,
                ativo,
                created_at,
                updated_at
            ) VALUES (
                v_tenant_id,
                v_categoria_custos_diretos_id,
                'Taxas de Cartão de Débito - Loja Física',
                'DIRETO',
                NULL,
                'AMBOS',
                TRUE,
                NOW(),
                NOW()
            );
            RAISE NOTICE '✅ Criada: Taxas de Cartão de Débito - Loja Física';
        ELSE
            RAISE NOTICE '⏭️  Já existe: Taxas de Cartão de Débito - Loja Física';
        END IF;
        
        -- 3. Taxa de PIX - Loja Física
        SELECT COUNT(*) INTO v_count
        FROM dre_subcategorias
        WHERE tenant_id = v_tenant_id
          AND nome = 'Taxa de PIX - Loja Física';
        
        IF v_count = 0 THEN
            INSERT INTO dre_subcategorias (
                tenant_id,
                categoria_id,
                nome,
                tipo_custo,
                base_rateio,
                escopo_rateio,
                ativo,
                created_at,
                updated_at
            ) VALUES (
                v_tenant_id,
                v_categoria_custos_diretos_id,
                'Taxa de PIX - Loja Física',
                'DIRETO',
                NULL,
                'AMBOS',
                TRUE,
                NOW(),
                NOW()
            );
            RAISE NOTICE '✅ Criada: Taxa de PIX - Loja Física';
        ELSE
            RAISE NOTICE '⏭️  Já existe: Taxa de PIX - Loja Física';
        END IF;
        
        RAISE NOTICE '✅ Tenant % processado com sucesso!', v_tenant_id;
        RAISE NOTICE '──────────────────────────────────────────────────────────────';
        
    END LOOP;
    
    RAISE NOTICE '✅ ✅ ✅ SCRIPT CONCLUÍDO COM SUCESSO! ✅ ✅ ✅';
    
END $$;

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

SELECT 
    ds.id,
    ds.nome,
    ds.escopo_rateio,
    dc.nome AS categoria_pai
FROM dre_subcategorias ds
JOIN dre_categorias dc ON ds.categoria_id = dc.id
WHERE ds.nome LIKE '%Taxa%'
  AND (ds.nome LIKE '%PDV%' OR ds.nome LIKE '%Loja Física%')
ORDER BY ds.nome;
ds.nome LIKE '%Loja Física%'