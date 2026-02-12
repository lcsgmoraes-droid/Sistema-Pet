-- Inserir template Stone com colunas corretas
-- Primeiro, pegar o tenant_id do usuário admin
DO $$
DECLARE
    v_tenant_id uuid;
BEGIN
    -- Pegar tenant_id do primeiro usuário (admin)
    SELECT tenant_id INTO v_tenant_id FROM users LIMIT 1;
    
    -- Verificar se já existe template Stone
    IF NOT EXISTS (SELECT 1 FROM templates_adquirentes WHERE nome_adquirente ILIKE '%stone%' AND tenant_id = v_tenant_id) THEN
        -- Inserir template Stone
        INSERT INTO templates_adquirentes (
            tenant_id,
            nome_adquirente,
            tipo_relatorio,
            mapeamento,
            palavras_chave,
            colunas_obrigatorias,
            vezes_usado,
            ultima_utilizacao,
            auto_aplicar,
            created_at,
            updated_at
        ) VALUES (
            v_tenant_id,
            'STONE',
            'Extrato de Vendas',
            '{
                "nsu": {"coluna": "STONE ID", "transformacao": "nsu", "obrigatorio": true},
                "data_venda": {"coluna": "DATA DA VENDA", "transformacao": "data_br", "obrigatorio": true},
                "data_pagamento": {"coluna": "DATA DO ULTIMO STATUS", "transformacao": "data_br", "obrigatorio": false},
                "valor_bruto": {"coluna": "VALOR BRUTO", "transformacao": "monetario_br", "obrigatorio": true},
                "taxa_mdr": {"coluna": "DESCONTO DE MDR", "transformacao": "monetario_br", "obrigatorio": false},
                "valor_taxa": {"coluna": "DESCONTO UNIFICADO", "transformacao": "monetario_br", "obrigatorio": false},
                "valor_liquido": {"coluna": "VALOR LIQUIDO", "transformacao": "monetario_br", "obrigatorio": true},
                "parcela": {"coluna": "N DE PARCELAS", "transformacao": "texto", "obrigatorio": false},
                "tipo_transacao": {"coluna": "PRODUTO", "transformacao": "texto", "obrigatorio": false},
                "bandeira": {"coluna": "BANDEIRA", "transformacao": "texto", "obrigatorio": false}
            }'::json,
            '["STONE", "Stone", "stone"]'::json,
            '["STONE ID", "DATA DA VENDA", "VALOR BRUTO"]'::json,
            0,
            NULL,
            true,
            NOW(),
            NOW()
        );
        
        RAISE NOTICE '✅ Template Stone criado com sucesso!';
    ELSE
        -- Atualizar template existente
        UPDATE templates_adquirentes 
        SET mapeamento = '{
                "nsu": {"coluna": "STONE ID", "transformacao": "nsu", "obrigatorio": true},
                "data_venda": {"coluna": "DATA DA VENDA", "transformacao": "data_br", "obrigatorio": true},
                "data_pagamento": {"coluna": "DATA DO ULTIMO STATUS", "transformacao": "data_br", "obrigatorio": false},
                "valor_bruto": {"coluna": "VALOR BRUTO", "transformacao": "monetario_br", "obrigatorio": true},
                "taxa_mdr": {"coluna": "DESCONTO DE MDR", "transformacao": "monetario_br", "obrigatorio": false},
                "valor_taxa": {"coluna": "DESCONTO UNIFICADO", "transformacao": "monetario_br", "obrigatorio": false},
                "valor_liquido": {"coluna": "VALOR LIQUIDO", "transformacao": "monetario_br", "obrigatorio": true},
                "parcela": {"coluna": "N DE PARCELAS", "transformacao": "texto", "obrigatorio": false},
                "tipo_transacao": {"coluna": "PRODUTO", "transformacao": "texto", "obrigatorio": false},
                "bandeira": {"coluna": "BANDEIRA", "transformacao": "texto", "obrigatorio": false}
            }'::json,
            updated_at = NOW()
        WHERE nome_adquirente ILIKE '%stone%' AND tenant_id = v_tenant_id;
        
        RAISE NOTICE '✅ Template Stone atualizado com sucesso!';
    END IF;
END $$;

-- Verificar o template criado/atualizado
SELECT 
    id, 
    nome_adquirente,
    mapeamento->>'nsu' as nsu_config,
    created_at,
    updated_at
FROM templates_adquirentes 
WHERE nome_adquirente ILIKE '%stone%';
