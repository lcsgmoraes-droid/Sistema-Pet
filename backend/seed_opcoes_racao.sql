-- Seed de Opções de Ração - Tenant 1
-- Executar: docker exec -i petshop-dev-banco psql -U postgres -d petshop_producao < seed_opcoes_racao.sql

-- Linhas de Ração
INSERT INTO linhas_racao (tenant_id, nome, descricao, ordem, ativo, created_at)
VALUES 
    (1, 'Super Premium', 'Linha superior com ingredientes premium', 1, true, NOW()),
    (1, 'Premium Special', 'Linha especial intermediária', 2, true, NOW()),
    (1, 'Premium', 'Linha premium padrão', 3, true, NOW()),
    (1, 'Standard', 'Linha tradicional', 4, true, NOW())
ON CONFLICT DO NOTHING;

-- Portes de Animal
INSERT INTO portes_animal (tenant_id, nome, descricao, ordem, ativo, created_at)
VALUES 
    (1, 'Pequeno', 'Até 10kg', 1, true, NOW()),
    (1, 'Médio', 'De 10kg a 25kg', 2, true, NOW()),
    (1, 'Médio e Grande', 'De 10kg a 45kg', 3, true, NOW()),
    (1, 'Grande', 'De 25kg a 45kg', 4, true, NOW()),
    (1, 'Gigante', 'Acima de 45kg', 5, true, NOW()),
    (1, 'Todos', 'Todas as raças', 6, true, NOW())
ON CONFLICT DO NOTHING;

-- Fases/Público
INSERT INTO fases_publico (tenant_id, nome, descricao, ordem, ativo, created_at)
VALUES 
    (1, 'Filhote', 'Até 12 meses', 1, true, NOW()),
    (1, 'Adulto', 'De 1 a 7 anos', 2, true, NOW()),
    (1, 'Senior', 'Acima de 7 anos', 3, true, NOW()),
    (1, 'Gestante', 'Fêmeas gestantes ou lactantes', 4, true, NOW())
ON CONFLICT DO NOTHING;

-- Tipos de Tratamento
INSERT INTO tipos_tratamento (tenant_id, nome, descricao, ordem, ativo, created_at)
VALUES 
    (1, 'Obesidade', 'Para controle de peso', 1, true, NOW()),
    (1, 'Light', 'Redução calórica', 2, true, NOW()),
    (1, 'Hipoalergênico', 'Para animais com alergias', 3, true, NOW()),
    (1, 'Sensível', 'Para estômagos sensíveis', 4, true, NOW()),
    (1, 'Digestivo', 'Facilita digestão', 5, true, NOW()),
    (1, 'Urinário', 'Saúde do trato urinário', 6, true, NOW()),
    (1, 'Renal', 'Para problemas renais', 7, true, NOW()),
    (1, 'Articular', 'Saúde das articulações', 8, true, NOW()),
    (1, 'Dermatológico', 'Para problemas de pele', 9, true, NOW())
ON CONFLICT DO NOTHING;

-- Sabores/Proteínas
INSERT INTO sabores_proteina (tenant_id, nome, descricao, ordem, ativo, created_at)
VALUES 
    (1, 'Frango', 'Proteína de frango', 1, true, NOW()),
    (1, 'Carne', 'Proteína bovina', 2, true, NOW()),
    (1, 'Peixe', 'Proteína de peixe', 3, true, NOW()),
    (1, 'Salmão', 'Proteína de salmão', 4, true, NOW()),
    (1, 'Cordeiro', 'Proteína de cordeiro', 5, true, NOW()),
    (1, 'Peru', 'Proteína de peru', 6, true, NOW()),
    (1, 'Porco', 'Proteína suína', 7, true, NOW()),
    (1, 'Vegetariano', 'Sem proteína animal', 8, true, NOW()),
    (1, 'Soja', 'Proteína de soja', 9, true, NOW()),
    (1, 'Mix', 'Mistura de proteínas', 10, true, NOW())
ON CONFLICT DO NOTHING;

-- Apresentações (Peso)
INSERT INTO apresentacoes_peso (tenant_id, peso_kg, descricao, ordem, ativo, created_at)
VALUES 
    (1, 0.5, '500g', 1, true, NOW()),
    (1, 1.0, '1kg', 2, true, NOW()),
    (1, 2.0, '2kg', 3, true, NOW()),
    (1, 3.0, '3kg', 4, true, NOW()),
    (1, 5.0, '5kg', 5, true, NOW()),
    (1, 7.0, '7kg', 6, true, NOW()),
    (1, 10.0, '10kg', 7, true, NOW()),
    (1, 10.1, '10.1kg', 8, true, NOW()),
    (1, 15.0, '15kg', 9, true, NOW()),
    (1, 20.0, '20kg', 10, true, NOW()),
    (1, 25.0, '25kg', 11, true, NOW())
ON CONFLICT DO NOTHING;

-- Verificar resultados
SELECT 'Linhas de Ração' as tabela, COUNT(*) as total FROM linhas_racao WHERE tenant_id = 1
UNION ALL
SELECT 'Portes de Animal', COUNT(*) FROM portes_animal WHERE tenant_id = 1
UNION ALL
SELECT 'Fases/Público', COUNT(*) FROM fases_publico WHERE tenant_id = 1
UNION ALL
SELECT 'Tipos de Tratamento', COUNT(*) FROM tipos_tratamento WHERE tenant_id = 1
UNION ALL
SELECT 'Sabores/Proteínas', COUNT(*) FROM sabores_proteina WHERE tenant_id = 1
UNION ALL
SELECT 'Apresentações de Peso', COUNT(*) FROM apresentacoes_peso WHERE tenant_id = 1;
