-- Adicionar colunas faltantes à tabela rotas_entrega
ALTER TABLE rotas_entrega 
ADD COLUMN IF NOT EXISTS ponto_inicial_rota TEXT,
ADD COLUMN IF NOT EXISTS ponto_final_rota TEXT,
ADD COLUMN IF NOT EXISTS retorna_origem BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS custo_moto NUMERIC(10, 2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS taxa_entrega_cliente NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS valor_repasse_entregador NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS data_inicio TIMESTAMP;
