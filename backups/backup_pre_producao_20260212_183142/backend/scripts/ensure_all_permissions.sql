-- Script para garantir que TODAS as permissões necessárias existem no sistema
-- Execute: Get-Content backend\scripts\ensure_all_permissions.sql | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev

-- Lista completa de todas as permissões do sistema (20 total)
INSERT INTO permissions (code, description) VALUES 
  -- VENDAS (4 permissões)
  ('vendas.criar', 'Criar vendas'),
  ('vendas.editar', 'Editar vendas'),
  ('vendas.excluir', 'Excluir vendas'),
  ('vendas.visualizar', 'Visualizar vendas'),
  
  -- PRODUTOS (4 permissões)
  ('produtos.criar', 'Criar produtos'),
  ('produtos.editar', 'Editar produtos'),
  ('produtos.excluir', 'Excluir produtos'),
  ('produtos.visualizar', 'Visualizar produtos'),
  
  -- CLIENTES (4 permissões)
  ('clientes.criar', 'Criar clientes'),
  ('clientes.editar', 'Editar clientes'),
  ('clientes.excluir', 'Excluir clientes'),
  ('clientes.visualizar', 'Visualizar clientes'),
  
  -- COMPRAS (1 permissão)
  ('compras.gerenciar', 'Gerenciar compras e pedidos'),
  
  -- RELATÓRIOS (2 permissões)
  ('relatorios.financeiro', 'Acessar relatórios financeiros'),
  ('relatorios.gerencial', 'Acessar relatórios gerenciais'),
  
  -- CONFIGURAÇÕES (1 permissão)
  ('configuracoes.editar', 'Editar configurações do sistema'),
  
  -- USUÁRIOS (2 permissões)
  ('usuarios.gerenciar', 'Gerenciar usuários e permissões'),
  ('usuarios.manage', 'Gerenciar usuários e permissões (frontend)'),
  
  -- INTELIGÊNCIA ARTIFICIAL (2 permissões)
  ('ia.fluxo_caixa', 'Acessar IA de Fluxo de Caixa'),
  ('ia.whatsapp', 'Acessar Bot WhatsApp')
ON CONFLICT (code) DO NOTHING;

-- Mostrar total de permissões
SELECT COUNT(*) as total_permissions FROM permissions;

-- Listar todas as permissões
SELECT 
  id,
  code,
  description,
  CASE 
    WHEN code LIKE 'vendas.%' THEN '📊 Vendas'
    WHEN code LIKE 'produtos.%' THEN '📦 Produtos'
    WHEN code LIKE 'clientes.%' THEN '👥 Clientes'
    WHEN code LIKE 'compras.%' THEN '🛒 Compras'
    WHEN code LIKE 'relatorios.%' THEN '📈 Relatórios'
    WHEN code LIKE 'configuracoes.%' THEN '⚙️  Configurações'
    WHEN code LIKE 'usuarios.%' THEN '👤 Usuários'
    WHEN code LIKE 'ia.%' THEN '🤖 IA'
    ELSE '❓ Outros'
  END as categoria
FROM permissions
ORDER BY categoria, code;
