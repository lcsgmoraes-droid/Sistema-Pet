# Perfis de acesso padrao

Novos tenants recebem seis perfis:

- `Administrador`: acesso total e gestao de usuarios/permissoes.
- `Gerente`: operacao e relatorios, sem administrar usuarios ou dados centrais da empresa.
- `Financeiro`: bancos, contas, conciliacoes, DRE, fluxo de caixa e relatorios financeiros.
- `Estoque e Compras`: produtos, entrada de XML e pedidos de compra, sem excluir produtos.
- `Caixa`: PDV, consulta de produtos e cadastro/edicao de clientes, sem excluir vendas,
  clientes ou produtos.
- `Cliente`: sem acesso ao painel administrativo; reservado para contas do app/e-commerce.

## Regras de seguranca

- Os perfis operacionais usam listas explicitas de permissoes.
- Uma permissao nova do sistema nao entra automaticamente nesses perfis.
- Apenas `Administrador` recebe automaticamente todas as permissoes disponiveis.
- O padrao roda somente no cadastro de um tenant novo.
- Perfis de tenants existentes nao sao sincronizados nem alterados por esta regra.
