-- Criação da tabela dre_detalhe_canais para armazenar DRE detalhado por canal
-- Tabela criada em: 2026-02-09
-- Referente ao modelo DREDetalheCanal em aba7_dre_detalhada_models.py

CREATE TABLE IF NOT EXISTS dre_detalhe_canais (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL DEFAULT '9df51a66-72bb-495f-a4a6-8a4953b20eae',
    usuario_id INTEGER,
    
    -- Período
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    mes INTEGER,
    ano INTEGER,
    
    -- Canal (uma linha para cada canal)
    canal VARCHAR(50) NOT NULL,
    
    -- ===== RECEITAS =====
    receita_bruta FLOAT DEFAULT 0,
    deducoes_receita FLOAT DEFAULT 0,
    receita_liquida FLOAT DEFAULT 0,
    
    -- ===== CUSTOS =====
    custo_produtos_vendidos FLOAT DEFAULT 0,
    lucro_bruto FLOAT DEFAULT 0,
    margem_bruta_percent FLOAT DEFAULT 0,
    
    -- ===== DESPESAS (SEM RATEIO - ALOCAÇÃO ESPECÍFICA DO CANAL) =====
    despesas_vendas FLOAT DEFAULT 0,
    despesas_pessoal FLOAT DEFAULT 0,
    despesas_administrativas FLOAT DEFAULT 0,
    despesas_financeiras FLOAT DEFAULT 0,
    outras_despesas FLOAT DEFAULT 0,
    total_despesas_operacionais FLOAT DEFAULT 0,
    
    -- ===== RESULTADO =====
    lucro_operacional FLOAT DEFAULT 0,
    margem_operacional_percent FLOAT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_dre_detalhe_canais_id ON dre_detalhe_canais(id);
CREATE INDEX IF NOT EXISTS idx_dre_detalhe_canais_usuario_id ON dre_detalhe_canais(usuario_id);
CREATE INDEX IF NOT EXISTS idx_dre_detalhe_canais_canal ON dre_detalhe_canais(canal);
CREATE INDEX IF NOT EXISTS idx_dre_detalhe_canais_tenant_id ON dre_detalhe_canais(tenant_id);
CREATE INDEX IF NOT EXISTS idx_dre_detalhe_canais_periodo ON dre_detalhe_canais(ano, mes);

-- Constraint de unicidade (um registro por período + canal + tenant)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dre_detalhe_canais_unico 
    ON dre_detalhe_canais(tenant_id, data_inicio, data_fim, canal);

COMMENT ON TABLE dre_detalhe_canais IS 'Armazena detalhes do DRE de CADA CANAL separadamente';
