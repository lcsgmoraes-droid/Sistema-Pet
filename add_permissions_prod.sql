-- Script SQL para adicionar as 35 permissões faltantes
-- Total: 51 permissões (16 existentes + 35 novas)

INSERT INTO permissions (code, description) VALUES
-- Financeiro (10 novas)
('financeiro.dashboard', 'Visualizar Dashboard Financeiro'),
('financeiro.vendas', 'Visualizar Relatório de Vendas'),
('financeiro.fluxo_caixa', 'Visualizar Fluxo de Caixa'),
('financeiro.dre', 'Visualizar DRE (Demonstrativo de Resultados)'),
('financeiro.contas_pagar', 'Gerenciar Contas a Pagar'),
('financeiro.contas_receber', 'Gerenciar Contas a Receber'),
('financeiro.contas_bancarias', 'Gerenciar Contas Bancárias'),
('financeiro.formas_pagamento', 'Gerenciar Formas de Pagamento'),
('financeiro.relatorio_taxas', 'Visualizar Relatório de Taxas'),
('financeiro.conciliacao_cartao', 'Realizar Conciliação de Cartão'),

-- Comissões (5)
('comissoes.configurar', 'Configurar Sistema de Comissões'),
('comissoes.demonstrativo', 'Visualizar Demonstrativo de Comissões'),
('comissoes.abertas', 'Visualizar Comissões em Aberto'),
('comissoes.fechamentos', 'Gerenciar Fechamentos de Comissões'),
('comissoes.relatorios', 'Visualizar Relatórios Analíticos de Comissões'),

-- Entregas (4)
('entregas.abertas', 'Visualizar Entregas em Aberto'),
('entregas.rotas', 'Gerenciar Rotas de Entrega'),
('entregas.historico', 'Visualizar Histórico de Entregas'),
('entregas.dashboard', 'Visualizar Dashboard Financeiro de Entregas'),

-- RH (1)
('rh.funcionarios', 'Gerenciar Funcionários'),

-- Compras (4)
('compras.gerenciar', 'Gerenciar compras e pedidos'),
('compras.pedidos', 'Gerenciar Pedidos de Compra'),
('compras.entrada_xml', 'Processar Entrada de Notas por XML'),
('compras.sincronizacao_bling', 'Sincronizar com Bling'),

-- Cadastros (4)
('cadastros.cargos', 'Gerenciar Cargos'),
('cadastros.categorias_produtos', 'Gerenciar Categorias de Produtos'),
('cadastros.categorias_financeiras', 'Gerenciar Categorias Financeiras'),
('cadastros.especies_racas', 'Gerenciar Espécies e Raças'),

-- Configurações extras (4)
('configuracoes.empresa', 'Configurar Dados da Empresa'),
('configuracoes.entregas', 'Configurar Parâmetros de Entregas'),
('configuracoes.custos_moto', 'Configurar Custos da Moto'),
('configuracoes.fechamento_mensal', 'Realizar Fechamento Mensal'),

-- IA (2)
('ia.whatsapp', 'Acessar Bot WhatsApp'),
('ia.fluxo_caixa', 'Acessar IA de Fluxo de Caixa'),

-- Usuários frontend (1)
('usuarios.manage', 'Gerenciar usuários e permissões (frontend)')

ON CONFLICT (code) DO NOTHING;
