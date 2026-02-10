-- ================================================
-- CRIAR SUBCATEGORIAS: COMISSÃO ENTREGADOR POR CANAL
-- ================================================
-- Data: 2026-02-09
-- Descrição: Cria subcategorias específicas de "Comissão Entregador" 
--            para cada canal de venda nas Despesas Operacionais
-- ================================================

-- Buscar ID da categoria "Despesas Operacionais"
DO $$
DECLARE
    v_categoria_pessoal_id INTEGER;
    v_tenant_id UUID := '9df51a66-72bb-495f-a4a6-8a4953b20eae';
BEGIN
    -- Buscar categoria Despesas com Pessoal
    SELECT id INTO v_categoria_pessoal_id
    FROM dre_categorias
    WHERE tenant_id = v_tenant_id
      AND nome = 'Despesas com Pessoal'
    LIMIT 1;

    IF v_categoria_pessoal_id IS NULL THEN
        RAISE EXCEPTION 'Categoria Despesas com Pessoal não encontrada';
    END IF;

    -- Criar subcategorias de Comissão Entregador por canal
    INSERT INTO dre_subcategorias (tenant_id, categoria_id, nome, tipo_custo, escopo_rateio, ativo, created_at)
    VALUES
        (v_tenant_id, v_categoria_pessoal_id, 'Comissão Entregador - Loja Física', 'DIRETO', 'AMBOS', true, NOW()),
        (v_tenant_id, v_categoria_pessoal_id, 'Comissão Entregador - Mercado Livre', 'DIRETO', 'AMBOS', true, NOW()),
        (v_tenant_id, v_categoria_pessoal_id, 'Comissão Entregador - Shopee', 'DIRETO', 'AMBOS', true, NOW()),
        (v_tenant_id, v_categoria_pessoal_id, 'Comissão Entregador - Amazon', 'DIRETO', 'AMBOS', true, NOW())
    ON CONFLICT DO NOTHING;

    RAISE NOTICE '✅ 4 subcategorias de Comissão Entregador criadas';
END $$;
