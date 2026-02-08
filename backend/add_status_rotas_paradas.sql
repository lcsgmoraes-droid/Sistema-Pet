-- Migration: Adicionar colunas status e data_entrega em rotas_entrega_paradas
-- Data: 2026-02-07
-- Descrição: Adiciona controle de status de entrega para cada parada de rota

-- Adicionar coluna status
ALTER TABLE rotas_entrega_paradas 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pendente';

-- Adicionar índice para otimizar consultas por status
CREATE INDEX IF NOT EXISTS idx_rotas_entrega_paradas_status 
ON rotas_entrega_paradas(status);

-- Adicionar coluna data_entrega
ALTER TABLE rotas_entrega_paradas 
ADD COLUMN IF NOT EXISTS data_entrega TIMESTAMP;

-- Atualizar registros existentes para garantir status padrão
UPDATE rotas_entrega_paradas 
SET status = 'pendente' 
WHERE status IS NULL;
