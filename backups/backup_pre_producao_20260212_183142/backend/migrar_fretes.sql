-- ========================================
-- MIGRATION: Criar categorias DRE e atualizar fretes
-- ========================================

-- Tenant ID (ajustar conforme necessário)
DO $$
DECLARE
    v_tenant_id UUID := '9df51a66-72bb-495f-a4a6-8a4953b20eae';
    v_categoria_id INTEGER;
    v_subcategoria_id INTEGER;
    v_contas_atualizadas INTEGER := 0;
BEGIN
    -- 1. Criar categoria "Custos" se não existir
    INSERT INTO dre_categorias (tenant_id, nome, natureza, ordem, ativo)
    SELECT v_tenant_id, 'Custos', 'CUSTO', 2, true
    WHERE NOT EXISTS (SELECT 1 FROM dre_categorias WHERE tenant_id = v_tenant_id AND nome = 'Custos');
    
    -- Obter ID da categoria
    SELECT id INTO v_categoria_id FROM dre_categorias WHERE tenant_id = v_tenant_id AND nome = 'Custos' LIMIT 1;
    RAISE NOTICE '✅ Categoria Custos: ID %', v_categoria_id;
    
    -- 2. Criar subcategoria "Fretes sobre Vendas"
    INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, base_rateio, escopo_rateio, ativo)
    SELECT v_tenant_id, v_categoria_id, 'Fretes sobre Vendas', 'DIRETO', NULL, 'AMBOS', true
    WHERE NOT EXISTS (SELECT 1 FROM dre_subcategorias WHERE tenant_id = v_tenant_id AND nome = 'Fretes sobre Vendas');
    
    -- Obter ID da subcategoria
    SELECT id INTO v_subcategoria_id FROM dre_subcategorias WHERE tenant_id = v_tenant_id AND nome = 'Fretes sobre Vendas' LIMIT 1;
    RAISE NOTICE '✅ Subcategoria Fretes sobre Vendas: ID %', v_subcategoria_id;
    
    -- 3. Buscar quantas contas serão atualizadas
    SELECT COUNT(*) INTO v_contas_atualizadas
    FROM contas_pagar
    WHERE tenant_id = v_tenant_id
    AND dre_subcategoria_id IS NULL
    AND (
        LOWER(descricao) LIKE '%frete%'
        OR LOWER(descricao) LIKE '%entrega%'
        OR LOWER(descricao) LIKE '%entregador%'
        OR LOWER(descricao) LIKE '%taxa de entrega%'
        OR LOWER(descricao) LIKE '%custo operacional%entrega%'
    );
    
    RAISE NOTICE '🔍 Total de contas para atualizar: %', v_contas_atualizadas;
    
    -- 4. Atualizar contas a pagar com a subcategoria DRE correta
    UPDATE contas_pagar
    SET dre_subcategoria_id = v_subcategoria_id
    WHERE tenant_id = v_tenant_id
    AND dre_subcategoria_id IS NULL
    AND (
        LOWER(descricao) LIKE '%frete%'
        OR LOWER(descricao) LIKE '%entrega%'
        OR LOWER(descricao) LIKE '%entregador%'
        OR LOWER(descricao) LIKE '%taxa de entrega%'
        OR LOWER(descricao) LIKE '%custo operacional%entrega%'
    );
    
    GET DIAGNOSTICS v_contas_atualizadas = ROW_COUNT;
    RAISE NOTICE '✅ Contas atualizadas: %', v_contas_atualizadas;
END $$;

-- 5. Verificar resultado final
SELECT 
    '✅ RESULTADO' AS status,
    COUNT(*) AS total_contas_com_dre
FROM contas_pagar cp
JOIN dre_subcategorias ds ON cp.dre_subcategoria_id = ds.id
WHERE ds.nome = 'Fretes sobre Vendas';

-- 6. Listar algumas contas atualizadas (primeiras 10)
SELECT 
    '📋 Exemplos de contas atualizadas:' AS info,
    cp.id, 
    cp.descricao, 
    cp.valor_original, 
    COALESCE(cp.data_vencimento::text, cp.data_emissao::text) AS data
FROM contas_pagar cp
JOIN dre_subcategorias ds ON cp.dre_subcategoria_id = ds.id
WHERE ds.nome = 'Fretes sobre Vendas'
ORDER BY cp.id DESC
LIMIT 10;
