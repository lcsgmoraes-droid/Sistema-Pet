-- =====================================================
-- MIGRATION: Tabela de Segmentação Automática de Clientes
-- Data: 26/01/2026
-- Descrição: Cria tabela para armazenar segmentos calculados (PostgreSQL)
-- =====================================================

-- 1) Criar tabela principal
CREATE TABLE IF NOT EXISTS cliente_segmentos (
    id SERIAL PRIMARY KEY,
    
    -- Relacionamento
    cliente_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    
    -- Segmento principal
    segmento VARCHAR(50) NOT NULL,  -- VIP, Recorrente, Novo, Inativo, Endividado, Risco
    
    -- Métricas calculadas (JSON para flexibilidade)
    metricas JSONB NOT NULL,  -- JSON: {total_compras_90d, ticket_medio, compras_90d, etc}
    
    -- Detalhes adicionais
    tags JSONB,  -- JSON array com múltiplos segmentos se aplicável: ["VIP", "Recorrente"]
    observacoes TEXT,
    
    -- Auditoria
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Índice único: um cliente tem apenas um registro de segmentação
    UNIQUE(cliente_id, user_id)
);

-- 2) Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_cliente_id 
    ON cliente_segmentos(cliente_id);

CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_user_id 
    ON cliente_segmentos(user_id);

CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_segmento 
    ON cliente_segmentos(segmento);

CREATE INDEX IF NOT EXISTS idx_cliente_segmentos_updated_at 
    ON cliente_segmentos(updated_at);

-- 3) Comentários das colunas
COMMENT ON TABLE cliente_segmentos IS 'Segmentação automática de clientes baseada em comportamento de compras';
COMMENT ON COLUMN cliente_segmentos.segmento IS 'Segmento principal do cliente (VIP, Recorrente, Novo, Inativo, Endividado, Risco)';
COMMENT ON COLUMN cliente_segmentos.metricas IS 'JSON com métricas calculadas para transparência e debug';
COMMENT ON COLUMN cliente_segmentos.tags IS 'Array JSON com múltiplos segmentos simultâneos (ex: cliente pode ser VIP + Recorrente)';

-- =====================================================
-- FIM DA MIGRATION
-- =====================================================
