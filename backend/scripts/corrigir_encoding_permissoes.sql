-- Corrigir encoding das descrições das permissões
-- Executar: Get-Content "caminho\corrigir_encoding_permissoes.sql" | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev

-- Financeiro
UPDATE permissions SET description = 'Visualizar Dashboard Financeiro' WHERE code = 'financeiro.dashboard';
UPDATE permissions SET description = 'Visualizar Relatório de Vendas' WHERE code = 'financeiro.vendas';
UPDATE permissions SET description = 'Visualizar Fluxo de Caixa' WHERE code = 'financeiro.fluxo_caixa';
UPDATE permissions SET description = 'Visualizar DRE (Demonstrativo de Resultados)' WHERE code = 'financeiro.dre';
UPDATE permissions SET description = 'Gerenciar Contas a Pagar' WHERE code = 'financeiro.contas_pagar';
UPDATE permissions SET description = 'Gerenciar Contas a Receber' WHERE code = 'financeiro.contas_receber';
UPDATE permissions SET description = 'Gerenciar Contas Bancárias' WHERE code = 'financeiro.contas_bancarias';
UPDATE permissions SET description = 'Gerenciar Formas de Pagamento' WHERE code = 'financeiro.formas_pagamento';
UPDATE permissions SET description = 'Visualizar Relatório de Taxas' WHERE code = 'financeiro.relatorio_taxas';
UPDATE permissions SET description = 'Realizar Conciliação de Cartão' WHERE code = 'financeiro.conciliacao_cartao';

-- Comissões
UPDATE permissions SET description = 'Configurar Sistema de Comissões' WHERE code = 'comissoes.configurar';
UPDATE permissions SET description = 'Visualizar Demonstrativo de Comissões' WHERE code = 'comissoes.demonstrativo';
UPDATE permissions SET description = 'Visualizar Comissões em Aberto' WHERE code = 'comissoes.abertas';
UPDATE permissions SET description = 'Gerenciar Fechamentos de Comissões' WHERE code = 'comissoes.fechamentos';
UPDATE permissions SET description = 'Visualizar Relatórios Analíticos de Comissões' WHERE code = 'comissoes.relatorios';

-- Entregas
UPDATE permissions SET description = 'Visualizar Entregas em Aberto' WHERE code = 'entregas.abertas';
UPDATE permissions SET description = 'Gerenciar Rotas de Entrega' WHERE code = 'entregas.rotas';
UPDATE permissions SET description = 'Visualizar Histórico de Entregas' WHERE code = 'entregas.historico';
UPDATE permissions SET description = 'Visualizar Dashboard Financeiro de Entregas' WHERE code = 'entregas.dashboard';

-- RH
UPDATE permissions SET description = 'Gerenciar Funcionários' WHERE code = 'rh.funcionarios';

-- Compras
UPDATE permissions SET description = 'Gerenciar Pedidos de Compra' WHERE code = 'compras.pedidos';
UPDATE permissions SET description = 'Processar Entrada de Notas por XML' WHERE code = 'compras.entrada_xml';
UPDATE permissions SET description = 'Sincronizar com Bling' WHERE code = 'compras.sincronizacao_bling';

-- Cadastros
UPDATE permissions SET description = 'Gerenciar Cargos' WHERE code = 'cadastros.cargos';
UPDATE permissions SET description = 'Gerenciar Categorias de Produtos' WHERE code = 'cadastros.categorias_produtos';
UPDATE permissions SET description = 'Gerenciar Categorias Financeiras' WHERE code = 'cadastros.categorias_financeiras';
UPDATE permissions SET description = 'Gerenciar Espécies e Raças' WHERE code = 'cadastros.especies_racas';

-- Configurações
UPDATE permissions SET description = 'Configurar Dados da Empresa' WHERE code = 'configuracoes.empresa';
UPDATE permissions SET description = 'Configurar Parâmetros de Entregas' WHERE code = 'configuracoes.entregas';
UPDATE permissions SET description = 'Configurar Custos da Moto' WHERE code = 'configuracoes.custos_moto';
UPDATE permissions SET description = 'Realizar Fechamento Mensal' WHERE code = 'configuracoes.fechamento_mensal';

\echo 'Descrições das permissões corrigidas com sucesso!'
