-- Script para resetar todas as sequences do banco de dados
-- Útil quando sequences ficam dessincronizadas após inserções manuais
-- Execute: Get-Content backend\scripts\reset_sequences.sql | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev

-- Users
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM users), false);

-- Roles
SELECT setval('roles_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM roles), false);

-- UserTenants
SELECT setval('user_tenants_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM user_tenants), false);

-- Permissions
SELECT setval('permissions_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM permissions), false);

-- RolePermissions
SELECT setval('role_permissions_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM role_permissions), false);

-- Produtos
SELECT setval('produtos_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM produtos), false);

-- Clientes
SELECT setval('clientes_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM clientes), false);

-- Vendas
SELECT setval('vendas_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM vendas), false);

-- Categorias
SELECT setval('categorias_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM categorias), false);

-- DRE Subcategorias
SELECT setval('dre_subcategorias_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM dre_subcategorias), false);

-- Contas a Pagar
SELECT setval('contas_pagar_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM contas_pagar), false);

-- Contas a Receber
SELECT setval('contas_receber_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM contas_receber), false);

-- Pets
SELECT setval('pets_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM pets), false);

-- Especies
SELECT setval('especies_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM especies), false);

-- Racas
SELECT setval('racas_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM racas), false);

-- Formas de Pagamento
SELECT setval('formas_pagamento_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM formas_pagamento), false);

-- Comissões
SELECT setval('comissoes_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM comissoes), false);

-- Comissões Itens
SELECT setval('comissoes_itens_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM comissoes_itens), false);

-- Acertos
SELECT setval('acertos_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM acertos), false);

-- Acertos Itens
SELECT setval('acertos_itens_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM acertos_itens), false);

VACUUM ANALYZE;

-- Mostrar resultado
SELECT 
    schemaname,
    sequencename,
    last_value
FROM pg_sequences
WHERE schemaname = 'public'
ORDER BY sequencename;
