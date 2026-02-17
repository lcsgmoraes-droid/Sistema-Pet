-- Migration: Adicionar campos de deduções detalhadas em comissoes_itens
-- Data: 09/02/2026
-- Objetivo: Armazenar breakdown completo das deduções na base de cálculo

ALTER TABLE comissoes_itens 
ADD COLUMN IF NOT EXISTS taxa_cartao_item NUMERIC(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS impostos_item NUMERIC(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS taxa_entregador_item NUMERIC(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS custo_operacional_item NUMERIC(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS receita_taxa_entrega_item NUMERIC(10,2) DEFAULT 0;

COMMENT ON COLUMN comissoes_itens.taxa_cartao_item IS 'Dedução proporcional da taxa de cartão (snapshot)';
COMMENT ON COLUMN comissoes_itens.impostos_item IS 'Dedução proporcional de impostos (snapshot)';
COMMENT ON COLUMN comissoes_itens.taxa_entregador_item IS 'Dedução proporcional da taxa paga ao entregador (snapshot)';
COMMENT ON COLUMN comissoes_itens.custo_operacional_item IS 'Dedução proporcional do custo operacional de entrega (snapshot)';
COMMENT ON COLUMN comissoes_itens.receita_taxa_entrega_item IS 'Receita proporcional da taxa de entrega cobrada do cliente (snapshot)';
