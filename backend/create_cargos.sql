-- Criar tabela cargos
CREATE TABLE IF NOT EXISTS cargos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id UUID NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    salario_base NUMERIC NOT NULL,
    inss_patronal_percentual NUMERIC NOT NULL DEFAULT 20,
    fgts_percentual NUMERIC NOT NULL DEFAULT 8,
    gera_ferias BOOLEAN NOT NULL DEFAULT true,
    gera_decimo_terceiro BOOLEAN NOT NULL DEFAULT true,
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT
);

-- Criar índices
CREATE INDEX IF NOT EXISTS ix_cargos_tenant_id ON cargos(tenant_id);
CREATE INDEX IF NOT EXISTS ix_cargos_nome ON cargos(nome);
CREATE INDEX IF NOT EXISTS ix_cargos_ativo ON cargos(ativo);
