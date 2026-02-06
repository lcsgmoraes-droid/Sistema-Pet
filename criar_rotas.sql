-- Criar rotas retroativamente para vendas abertas com entrega

-- Primeiro, pegar o tenant_id e entregador_id padrão
DO $$
DECLARE
    v_tenant_id UUID;
    v_entregador_id INT;
    v_ponto_inicial TEXT;
    v_numero INT := 0;
    venda_record RECORD;
BEGIN
    -- Buscar tenant e entregador padrão
    SELECT tenant_id, id 
    INTO v_tenant_id, v_entregador_id
    FROM clientes 
    WHERE entregador_padrao = true 
    AND entregador_ativo = true 
    LIMIT 1;
    
    RAISE NOTICE 'Tenant: %, Entregador: %', v_tenant_id, v_entregador_id;
    
    -- Buscar ponto inicial
    SELECT ponto_inicial_rota 
    INTO v_ponto_inicial
    FROM configuracoes_entrega 
    WHERE tenant_id = v_tenant_id 
    LIMIT 1;
    
    RAISE NOTICE 'Ponto inicial: %', v_ponto_inicial;
    
    -- Para cada venda sem rota
    FOR venda_record IN
        SELECT v.id, v.numero_venda, v.tenant_id, v.endereco_entrega, v.taxa_entrega
        FROM vendas v
        LEFT JOIN rotas_entrega r ON r.venda_id = v.id
        WHERE v.tem_entrega = true 
        AND v.status = 'aberta'
        AND r.id IS NULL
        ORDER BY v.id
    LOOP
        v_numero := v_numero + 1;
        
        INSERT INTO rotas_entrega (
            tenant_id,
            venda_id,
            entregador_id,
            endereco_destino,
            status,
            taxa_entrega_cliente,
            ponto_inicial_rota,
            numero,
            created_at,
            updated_at
        ) VALUES (
            venda_record.tenant_id,
            venda_record.id,
            v_entregador_id,
            venda_record.endereco_entrega,
            'pendente',
            COALESCE(venda_record.taxa_entrega, 0),
            v_ponto_inicial,
            v_numero,
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'Rota % criada para venda % (%)', 
            v_numero, venda_record.numero_venda, venda_record.id;
    END LOOP;
    
    RAISE NOTICE 'Total: % rotas criadas', v_numero;
END $$;
