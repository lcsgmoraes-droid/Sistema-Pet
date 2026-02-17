-- Inserir template Stone na tabela correta (adquirentes_templates)
DO $$
DECLARE
    v_tenant_id UUID;
BEGIN
    -- Pegar tenant_id do primeiro usuário (admin)
    SELECT tenant_id INTO v_tenant_id FROM users LIMIT 1;
    
    IF v_tenant_id IS NULL THEN
        RAISE EXCEPTION 'Nenhum tenant encontrado';
    END IF;
    
    -- Deletar template Stone existente (se houver)
    DELETE FROM adquirentes_templates 
    WHERE tenant_id = v_tenant_id AND nome = 'STONE';
    
    -- Inserir template Stone com mapeamento correto
    INSERT INTO adquirentes_templates (
        tenant_id,
        nome,
        tipo_arquivo,
        ativo,
        separador,
        encoding,
        tem_header,
        pular_linhas,
        mapeamento,
        transformacoes
    ) VALUES (
        v_tenant_id,
        'STONE',
        'vendas',
        true,
        ';',
        'utf-8',
        true,
        0,
        jsonb_build_object(
            'nsu', jsonb_build_object(
                'coluna', 'STONE ID',
                'transformacao', 'nsu',
                'obrigatorio', true
            ),
            'data_venda', jsonb_build_object(
                'coluna', 'DATA DA VENDA',
                'transformacao', 'data_br',
                'obrigatorio', true
            ),
            'valor_bruto', jsonb_build_object(
                'coluna', 'VALOR BRUTO',
                'transformacao', 'monetario_br',
                'obrigatorio', true
            ),
            'valor_liquido', jsonb_build_object(
                'coluna', 'VALOR LIQUIDO',
                'transformacao', 'monetario_br',
                'obrigatorio', true
            ),
            'numero_parcela', jsonb_build_object(
                'coluna', 'N DE PARCELAS',
                'transformacao', 'texto',
                'obrigatorio', false
            ),
            'produto', jsonb_build_object(
                'coluna', 'PRODUTO',
                'transformacao', 'texto',
                'obrigatorio', false
            ),
            'bandeira', jsonb_build_object(
                'coluna', 'BANDEIRA',
                'transformacao', 'texto',
                'obrigatorio', false
            )
        ),
        jsonb_build_object(
            'monetario_br', 'Converte R$ 1.234,56 ou 1234,56 para Decimal',
            'data_br', 'Converte DD/MM/YYYY HH:MM para datetime',
            'nsu', 'Remove espaços e caracteres especiais',
            'texto', 'Mantém texto como está'
        )
    );
    
    RAISE NOTICE '✅ Template STONE criado com sucesso na tabela adquirentes_templates!';
END $$;

-- Verificar
SELECT id, nome, tipo_arquivo, mapeamento->'nsu' as nsu_config 
FROM adquirentes_templates 
WHERE nome = 'STONE';
