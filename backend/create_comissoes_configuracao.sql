-- Criar tabela comissoes_configuracao
-- Esta tabela armazena as configurações de comissão por funcionário

CREATE TABLE IF NOT EXISTS comissoes_configuracao (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- 'categoria', 'subcategoria', 'produto'
    referencia_id INTEGER NOT NULL, -- ID da categoria/subcategoria/produto
    tipo_calculo VARCHAR(50) DEFAULT 'percentual', -- 'percentual' ou 'lucro'
    percentual DECIMAL(10, 2) DEFAULT 0.00,
    percentual_loja DECIMAL(10, 2),
    desconta_taxa_cartao BOOLEAN DEFAULT true,
    desconta_impostos BOOLEAN DEFAULT true,
    desconta_custo_entrega BOOLEAN DEFAULT false,
    comissao_venda_parcial BOOLEAN DEFAULT true,
    permite_edicao_venda BOOLEAN DEFAULT false,
    ativo BOOLEAN DEFAULT true,
    observacoes TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID,
    FOREIGN KEY (funcionario_id) REFERENCES clientes(id) ON DELETE CASCADE
);

-- Criar índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_comissoes_configuracao_funcionario ON comissoes_configuracao(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_comissoes_configuracao_tipo ON comissoes_configuracao(tipo);
CREATE INDEX IF NOT EXISTS idx_comissoes_configuracao_ativo ON comissoes_configuracao(ativo);
CREATE INDEX IF NOT EXISTS idx_comissoes_configuracao_tenant ON comissoes_configuracao(tenant_id);

-- Criar índice composto para garantir unicidade
CREATE UNIQUE INDEX IF NOT EXISTS idx_comissoes_configuracao_unique 
ON comissoes_configuracao(funcionario_id, tipo, referencia_id) 
WHERE ativo = true;
