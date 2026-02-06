-- Adicionar coluna entregador_padrao se não existir
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clientes' 
        AND column_name = 'entregador_padrao'
    ) THEN
        ALTER TABLE clientes 
        ADD COLUMN entregador_padrao BOOLEAN NOT NULL DEFAULT FALSE;
        
        RAISE NOTICE 'Coluna entregador_padrao adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna entregador_padrao já existe';
    END IF;
END $$;

-- Verificar se precisa adicionar gera_conta_pagar_custo_entrega
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clientes' 
        AND column_name = 'gera_conta_pagar_custo_entrega'
    ) THEN
        ALTER TABLE clientes 
        ADD COLUMN gera_conta_pagar_custo_entrega BOOLEAN NOT NULL DEFAULT FALSE;
        
        RAISE NOTICE 'Coluna gera_conta_pagar_custo_entrega adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna gera_conta_pagar_custo_entrega já existe';
    END IF;
END $$;

-- Exibir colunas de entregador
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'clientes' 
AND column_name LIKE '%entregador%'
ORDER BY column_name;
