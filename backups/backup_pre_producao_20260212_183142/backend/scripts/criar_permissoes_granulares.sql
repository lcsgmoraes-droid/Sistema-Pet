-- Script para criar permissões mais granulares
-- Permite controlar cada submenu individualmente

-- ==================================================
-- PERMISSÕES FINANCEIRO (granulares)
-- ==================================================
INSERT INTO permissions (code, description, created_at)
VALUES 
    ('financeiro.dashboard', 'Visualizar Dashboard Financeiro', NOW()),
    ('financeiro.vendas', 'Visualizar Relatório de Vendas', NOW()),
    ('financeiro.fluxo_caixa', 'Visualizar Fluxo de Caixa', NOW()),
    ('financeiro.dre', 'Visualizar DRE (Demonstrativo de Resultados)', NOW()),
    ('financeiro.contas_pagar', 'Gerenciar Contas a Pagar', NOW()),
    ('financeiro.contas_receber', 'Gerenciar Contas a Receber', NOW()),
    ('financeiro.contas_bancarias', 'Gerenciar Contas Bancárias', NOW()),
    ('financeiro.formas_pagamento', 'Gerenciar Formas de Pagamento', NOW()),
    ('financeiro.relatorio_taxas', 'Visualizar Relatório de Taxas', NOW()),
    ('financeiro.conciliacao_cartao', 'Realizar Conciliação de Cartão', NOW())
ON CONFLICT (code) DO NOTHING;

-- ==================================================
-- PERMISSÕES COMISSÕES (granulares)
-- ==================================================
INSERT INTO permissions (code, description, created_at)
VALUES 
    ('comissoes.configurar', 'Configurar Sistema de Comissões', NOW()),
    ('comissoes.demonstrativo', 'Visualizar Demonstrativo de Comissões', NOW()),
    ('comissoes.abertas', 'Visualizar Comissões em Aberto', NOW()),
    ('comissoes.fechamentos', 'Gerenciar Fechamentos de Comissões', NOW()),
    ('comissoes.relatorios', 'Visualizar Relatórios Analíticos de Comissões', NOW())
ON CONFLICT (code) DO NOTHING;

-- ==================================================
-- PERMISSÕES ENTREGAS (granulares)
-- ==================================================
INSERT INTO permissions (code, description, created_at)
VALUES 
    ('entregas.abertas', 'Visualizar Entregas em Aberto', NOW()),
    ('entregas.rotas', 'Gerenciar Rotas de Entrega', NOW()),
    ('entregas.historico', 'Visualizar Histórico de Entregas', NOW()),
    ('entregas.dashboard', 'Visualizar Dashboard Financeiro de Entregas', NOW())
ON CONFLICT (code) DO NOTHING;

-- ==================================================
-- PERMISSÕES RH (granulares)
-- ==================================================
INSERT INTO permissions (code, description, created_at)
VALUES 
    ('rh.funcionarios', 'Gerenciar Funcionários', NOW())
ON CONFLICT (code) DO NOTHING;

-- ==================================================
-- PERMISSÕES COMPRAS (granulares)
-- ==================================================
INSERT INTO permissions (code, description, created_at)
VALUES 
    ('compras.pedidos', 'Gerenciar Pedidos de Compra', NOW()),
    ('compras.entrada_xml', 'Realizar Entrada de Notas por XML', NOW()),
    ('compras.sincronizacao_bling', 'Sincronizar com Bling', NOW())
ON CONFLICT (code) DO NOTHING;

-- ==================================================
-- PERMISSÕES CADASTROS (granulares)
-- ==================================================
INSERT INTO permissions (code, description, created_at)
VALUES 
    ('cadastros.cargos', 'Gerenciar Cargos', NOW()),
    ('cadastros.categorias_produtos', 'Gerenciar Categorias de Produtos', NOW()),
    ('cadastros.categorias_financeiras', 'Gerenciar Categorias Financeiras', NOW()),
    ('cadastros.especies_racas', 'Gerenciar Espécies e Raças', NOW())
ON CONFLICT (code) DO NOTHING;

-- ==================================================
-- PERMISSÕES CONFIGURAÇÕES (granulares)
-- ==================================================
INSERT INTO permissions (code, description, created_at)
VALUES 
    ('configuracoes.empresa', 'Configurar Dados da Empresa', NOW()),
    ('configuracoes.entregas', 'Configurar Entregas', NOW()),
    ('configuracoes.custos_moto', 'Configurar Custos da Moto', NOW()),
    ('configuracoes.fechamento_mensal', 'Realizar Fechamento Mensal', NOW())
ON CONFLICT (code) DO NOTHING;

-- ==================================================
-- ATUALIZAR ROLE ADMIN COM TODAS AS NOVAS PERMISSÕES
-- ==================================================
DO $$
DECLARE
    admin_role_id INT;
    perm_record RECORD;
BEGIN
    -- Buscar role admin
    SELECT id INTO admin_role_id FROM roles WHERE name = 'admin' LIMIT 1;
    
    IF admin_role_id IS NOT NULL THEN
        -- Inserir todas as novas permissões para a role admin em todos os tenants
        FOR perm_record IN 
            SELECT id FROM permissions 
            WHERE code LIKE 'financeiro.%' 
               OR code LIKE 'comissoes.%' 
               OR code LIKE 'entregas.%' 
               OR code LIKE 'rh.%' 
               OR code LIKE 'compras.%'
               OR code LIKE 'cadastros.%'
               OR code LIKE 'configuracoes.%'
        LOOP
            INSERT INTO role_permissions (role_id, permission_id, tenant_id)
            SELECT admin_role_id, perm_record.id, t.id
            FROM tenants t
            ON CONFLICT (role_id, permission_id, tenant_id) DO NOTHING;
        END LOOP;
        
        RAISE NOTICE 'Permissões granulares adicionadas à role admin com sucesso!';
    ELSE
        RAISE NOTICE 'Role admin não encontrada.';
    END IF;
END $$;
