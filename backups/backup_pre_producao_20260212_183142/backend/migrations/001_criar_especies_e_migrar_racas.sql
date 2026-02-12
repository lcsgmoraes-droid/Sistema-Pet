-- ============================================================================
-- MIGRATION: Criar tabela Especies e migrar Racas
-- Data: 2026-02-07
-- Descrição: 
--   1. Cria tabela especies para armazenar tipos de animais
--   2. Popula especies a partir dos dados existentes em racas
--   3. Adiciona coluna especie_id em racas
--   4. Migra os dados existentes
--   5. Remove coluna antiga especie (string)
-- ============================================================================

-- PASSO 1: Criar tabela especies
CREATE TABLE IF NOT EXISTS especies (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    nome VARCHAR(100) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_especies_tenant_id ON especies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_especies_nome ON especies(nome);
CREATE INDEX IF NOT EXISTS idx_especies_ativo ON especies(ativo);

-- PASSO 2: Inserir espécies padrão (extraídas das raças existentes)
-- Primeiro, vamos coletar todas as espécies únicas da tabela racas
INSERT INTO especies (tenant_id, nome, ativo)
SELECT DISTINCT 
    tenant_id,
    especie as nome,
    TRUE as ativo
FROM racas
WHERE especie IS NOT NULL
ON CONFLICT DO NOTHING;

-- Adicionar espécies padrão caso não existam ainda (para novos tenants)
INSERT INTO especies (tenant_id, nome, ativo)
SELECT DISTINCT 
    tenant_id,
    'Cão' as nome,
    TRUE as ativo
FROM racas
WHERE tenant_id NOT IN (SELECT tenant_id FROM especies WHERE nome = 'Cão')
ON CONFLICT DO NOTHING;

INSERT INTO especies (tenant_id, nome, ativo)
SELECT DISTINCT 
    tenant_id,
    'Gato' as nome,
    TRUE as ativo
FROM racas
WHERE tenant_id NOT IN (SELECT tenant_id FROM especies WHERE nome = 'Gato')
ON CONFLICT DO NOTHING;

-- PASSO 3: Adicionar coluna especie_id em racas (temporariamente nullable)
ALTER TABLE racas ADD COLUMN IF NOT EXISTS especie_id INTEGER;

-- PASSO 4: Preencher especie_id com base na string especie
UPDATE racas r
SET especie_id = e.id
FROM especies e
WHERE r.tenant_id = e.tenant_id 
  AND r.especie = e.nome;

-- PASSO 5: Tornar especie_id obrigatória e adicionar foreign key
ALTER TABLE racas ALTER COLUMN especie_id SET NOT NULL;

ALTER TABLE racas 
ADD CONSTRAINT fk_racas_especie 
FOREIGN KEY (especie_id) 
REFERENCES especies(id) 
ON DELETE RESTRICT;

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_racas_especie_id ON racas(especie_id);

-- PASSO 6: Remover coluna antiga especie (comentado por segurança)
-- Descomente após confirmar que tudo está funcionando:
-- ALTER TABLE racas DROP COLUMN IF EXISTS especie;

-- ============================================================================
-- DADOS PADRÃO: Raças comuns (caso a tabela esteja vazia)
-- ============================================================================

-- Inserir raças padrão para Cães (se não existirem)
INSERT INTO racas (tenant_id, nome, especie_id, ativo)
SELECT DISTINCT
    r.tenant_id,
    dados.nome,
    e.id as especie_id,
    TRUE as ativo
FROM racas r
CROSS JOIN (
    VALUES 
        ('SRD (Sem Raça Definida)'),
        ('Labrador'),
        ('Golden Retriever'),
        ('Bulldog'),
        ('Poodle'),
        ('Pastor Alemão'),
        ('Beagle'),
        ('Yorkshire'),
        ('Shih Tzu'),
        ('Pit Bull'),
        ('Chihuahua'),
        ('Rottweiler'),
        ('Boxer'),
        ('Dachshund (Salsicha)'),
        ('Husky Siberiano'),
        ('Border Collie'),
        ('Maltês'),
        ('Dálmata'),
        ('Pug'),
        ('Cocker Spaniel')
) AS dados(nome)
JOIN especies e ON e.tenant_id = r.tenant_id AND e.nome = 'Cão'
WHERE NOT EXISTS (
    SELECT 1 FROM racas r2 
    WHERE r2.tenant_id = r.tenant_id 
      AND r2.nome = dados.nome
)
LIMIT 1;  -- Apenas um tenant por vez

-- Inserir raças padrão para Gatos (se não existirem)
INSERT INTO racas (tenant_id, nome, especie_id, ativo)
SELECT DISTINCT
    r.tenant_id,
    dados.nome,
    e.id as especie_id,
    TRUE as ativo
FROM racas r
CROSS JOIN (
    VALUES 
        ('SRD (Sem Raça Definida)'),
        ('Siamês'),
        ('Persa'),
        ('Maine Coon'),
        ('Bengal'),
        ('Sphynx'),
        ('Ragdoll'),
        ('British Shorthair'),
        ('Scottish Fold'),
        ('Angora'),
        ('Sagrado da Birmânia'),
        ('Abissínio'),
        ('Exótico')
) AS dados(nome)
JOIN especies e ON e.tenant_id = r.tenant_id AND e.nome = 'Gato'
WHERE NOT EXISTS (
    SELECT 1 FROM racas r2 
    WHERE r2.tenant_id = r.tenant_id 
      AND r2.nome = dados.nome
)
LIMIT 1;  -- Apenas um tenant por vez

-- ============================================================================
-- FIM DA MIGRATION
-- ============================================================================

-- Verificação (executar após a migration):
-- SELECT e.nome as especie, COUNT(r.id) as total_racas
-- FROM especies e
-- LEFT JOIN racas r ON r.especie_id = e.id
-- GROUP BY e.id, e.nome
-- ORDER BY e.nome;
