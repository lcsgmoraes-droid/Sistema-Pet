# Base Demo para Gravacao - Sistema Pet

Uso: preparar um ambiente ficticio e consistente para gravar videos do Sistema
Pet sem expor dados reais de clientes.

Arquivos executaveis da base demo:

- Seed operacional local: `backend/app/scripts/seed_demo_operacional.py`
- Dados estruturados: `docs/marketing/base-demo/dados_base_demo_sistema_pet.json`
- Validador/checklist: `scripts/validar_base_demo_marketing.py`
- Contrato: `scripts/test_marketing_demo_package.py`
- Manifesto de seed: `scripts/gerar_seed_base_demo_marketing.py`
- Contrato do manifesto: `scripts/test_marketing_demo_seed_plan.py`
- Aplicador dry-run/apply DEV: `scripts/aplicar_seed_base_demo_marketing.py`
- Contrato do aplicador: `scripts/test_marketing_demo_seed_apply.py`

## Base operacional validada em 2026-08-13

Tenant local de gravacao:

| Campo | Valor |
|---|---|
| Email | `corepeterp@gmail.com` |
| Senha local | `12345678` |
| URL local | `http://127.0.0.1:5173/login` |
| Tenant id local | `569aa16d-f13c-422f-b23e-a15fa9bbfd68` |
| Fonte de catalogo | Snapshot reduzido da loja `atacadaopetpp@gmail.com` |

Comando usado para recriar a base operacional em DEV/local:

```powershell
$env:DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5433/petshop_dev'
$env:ENVIRONMENT='development'
python backend/app/scripts/seed_demo_operacional.py --target-email corepeterp@gmail.com --source-email atacadaopetpp@gmail.com --base-date 2026-06-28 --apply
```

Resultado validado:

- Catalogo-base com produtos reais para as demais demonstracoes.
- 10 produtos ficticios `DEMO-VP-*` exclusivos do fluxo seguro de compras.
- Custos e precos variados e artificiais no catalogo ficticio.
- 54 vendas demo com canais ERP/PDV, ecommerce e app, usadas tambem no historico da sugestao inteligente.
- 17 contas a pagar, 6 contas a receber e 5 recebimentos.
- 3 rotas de entrega com entregador cadastrado.
- 17 movimentacoes de estoque.
- 11 movimentacoes financeiras.
- 8 itens de comissao para Beatriz Vendedora Demo.
- Imposto demo de 6,25% e comissao demo de 4%.

Telas ja conferidas para gravacao:

- `/financeiro/vendas`: lista de vendas com margem, CMV, imposto, desconto, taxa de pagamento, campanha e comissao.
- `/produtos`: catalogo-base e linha ficticia `VivaPata Demo` para gravacoes publicas.
- `/compras/pedidos`: sugestao inteligente com 10 itens ficticios do mesmo fornecedor, incluindo prioridades critica, alerta e normal.
- `/calculadora-racao`: comparativo de racoes funcionando com 10 opcoes e custo por dia.
- `/comissoes`: Beatriz Vendedora Demo aparece com 1 regra geral.
- `/comissoes/abertas`: 8 comissoes pendentes, total R$ 60,13.
- `/entregas/rotas`: rotas pendente e em rota com Carlos Entregador Demo.
- `/financeiro`: dashboard executivo com leitura automatica, alertas e contas vencidas.

## Objetivo

A base demo precisa permitir gravar:

- configuracao inicial;
- venda no PDV;
- estoque e produto;
- financeiro e recebimentos;
- compras e entrada XML;
- banho e tosa;
- veterinario;
- ecommerce/app;
- relatorios gerenciais.

## Regras de seguranca

- Nao usar dados reais de cliente, pet, fornecedor, funcionario ou empresa.
- Nao gravar CPF, CNPJ, telefone, email ou endereco real.
- Nao gravar chaves de API, tokens, webhooks ou configuracoes sensiveis.
- Nao gravar ambiente de producao.
- Nao misturar base demo com operacao real.
- Rodar `--apply` somente em tenant DEV/demo confirmado.
- Nao usar tenant/e-mail ja utilizado por operacao real.
- E-mail sugerido para criar o tenant demo desta leva:
  `corepeterp@gmail.com`.
- A seed operacional atual cria a historia principal de vendas, financeiro,
  estoque, entregas, RH e comissoes para gravacao local.
- Banho e tosa, veterinario, XML real e integracoes externas continuam em
  conferencia manual antes de entrarem nos videos.

## Identidade da empresa demo

| Campo | Valor sugerido |
|---|---|
| Nome fantasia | Pet Feliz Demo |
| Razao social | Pet Feliz Demonstracao Ltda |
| CNPJ | 00.000.000/0001-00 |
| Cidade | Sao Paulo |
| UF | SP |
| Segmento | Pet shop com banho e tosa, veterinario e ecommerce |
| Usuario principal | Lucas Demo |
| Email demo | demo@sistemapet.local |

## Cadastros obrigatorios

| Ordem | Cadastro | Exemplo | Por que precisa existir |
|---|---|---|---|
| 1 | Empresa | Pet Feliz Demo | Identifica o tenant e aparece em telas administrativas |
| 2 | Usuario admin | Lucas Demo | Permite gravar configuracao e operacao |
| 3 | Banco/conta | Conta Banco Demo | Ajuda a demonstrar recebimentos e caixa |
| 4 | Forma de pagamento | PIX, Dinheiro, Cartao credito | Permite vender no PDV e gerar recebimento |
| 5 | Categoria financeira | Venda de produtos | Classifica vendas e relatorios |
| 6 | Imposto/config fiscal | Tributacao demo | Permite explicar custo, venda e margem |
| 7 | Cliente | Maria Oliveira | Usado em venda, pet, agendamento e atendimento |
| 8 | Pet | Thor | Usado em banho e tosa e veterinario |
| 9 | Fornecedor | Distribuidora Horizonte Pet Demo | Usado em compras e XML |
| 10 | Produto | Racao VivaPata Essencial Caes Adultos Frango 10 kg | Usado em estoque, PDV, ecommerce e relatorios |

## Produtos demo

Para gravacoes publicas do fluxo de compras, use somente a linha ficticia
`VivaPata Demo`. A seed cria dez itens vinculados ao mesmo fornecedor, com
estoques, custos, precos e historicos variados para alimentar a sugestao
inteligente. Entre eles ha racoes, petiscos, tapetes, areia, shampoo,
condicionador e brinquedos.

Os codigos internos seguem `DEMO-VP-001` a `DEMO-VP-010`; os codigos do
fornecedor seguem `HORIZONTE-001` a `HORIZONTE-010`. Todos os nomes, codigos,
EANs e valores desta linha sao demonstrativos.

O catalogo-base ainda pode conter nomes comerciais publicos para outras
demonstracoes. Nao o use quando a narrativa atribuir precos, custos ou uma
relacao comercial a uma marca real.

## Clientes e pets demo

| Cliente | Pet | Uso principal |
|---|---|---|
| Maria Oliveira | Thor | Venda, banho e tosa, veterinario |
| Joao Santos | Luna | Agenda cheia e historico |
| Ana Costa | Mel | Ecommerce/app |

## Servicos demo

| Servico | Duracao | Preco | Uso |
|---|---:|---:|---|
| Banho medio completo | 60 min | 79,90 | Agenda e fila |
| Tosa higienica | 45 min | 59,90 | Agenda e servicos |
| Avaliacao preventiva | 30 min | 120,00 | Veterinario |
| Vacinacao demo | 20 min | 95,00 | Veterinario |

## Compras e XML

Use fornecedor e marca ficticios:

- Fornecedor: Distribuidora Horizonte Pet Demo.
- Marca: VivaPata Demo.
- Pedido de compra: os dez produtos `DEMO-VP-*`.
- Nota/XML: usar arquivo demonstrativo sem CNPJ real ou mascarado.

Fluxo para deixar pronto:

1. Criar fornecedor.
2. Criar produtos.
3. Criar pedido de compra demo.
4. Importar ou simular entrada XML.
5. Conferir custo e estoque.
6. Separar uma compra pendente para gravar antes/depois.

## Financeiro

Cadastros minimos:

- Banco: Conta Banco Demo.
- Formas de pagamento: PIX, Dinheiro, Cartao credito, Cartao debito.
- Operadora de cartao: Operadora Demo.
- Categorias: Venda de produtos, Venda de servicos, Compra de mercadorias.
- Conta a receber demo: venda no PDV.
- Conta a pagar demo: compra com fornecedor.

## Ecommerce/app

Preparar:

- Loja demo ativa.
- Catalogo com 4 produtos.
- Produto com imagem demonstrativa.
- Pedido online pendente.
- Pedido online finalizado.
- Configuracao de entrega ou retirada.

Evitar:

- Dados reais de pagamento.
- Link real de checkout.
- Chaves de integracao.

## Roteiro de preparacao

1. Abrir a Introducao Guiada e conferir pendencias.
2. Completar empresa e usuarios.
3. Cadastrar financeiro obrigatorio.
4. Cadastrar impostos/configuracao fiscal demo.
5. Cadastrar cliente, pet, fornecedor e produtos.
6. Conferir estoque inicial.
7. Criar uma venda PDV simples.
8. Conferir contas a receber.
9. Criar compra e entrada XML demo.
10. Criar servicos e agendamentos de banho e tosa.
11. Criar agenda veterinaria demo.
12. Configurar ecommerce/app demo.
13. Conferir relatorios com dados suficientes.

Para a base `corepeterp@gmail.com`, a gravacao deve comecar por telas ja
populadas: vendas, produtos, calculadora de racao, comissoes, entregas,
contas a pagar/receber, fluxo de caixa, DRE e dashboard financeiro. Evitar
comecar pelo dashboard financeiro se o objetivo do criativo for venda; ele
mostra um cenario de alerta, melhor para falar de controle e risco.

## Checklist antes de gravar

- Rodar `python scripts/test_marketing_demo_package.py`.
- Rodar `python scripts/test_marketing_demo_seed_plan.py`.
- Rodar `python scripts/test_marketing_demo_seed_apply.py`.
- Rodar `python -m pytest backend/tests/unit/test_seed_demo_operacional.py`.
- Rodar `python scripts/validar_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --markdown`.
- Gerar o manifesto com `python scripts/gerar_seed_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --tenant-slug tenant_demo --format markdown`.
- Simular a aplicacao com `python scripts/aplicar_seed_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --tenant-slug corepeterp_demo --tenant-email corepeterp@gmail.com --dry-run`.
- Aplicar em DEV/demo, somente apos conferir o dry-run, com `python scripts/aplicar_seed_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --tenant-slug corepeterp_demo --tenant-email corepeterp@gmail.com --environment development --apply`.
- Separar a fila de takes em `docs/marketing/PLANO_CAPTURA_TELAS_DEMO.md`.
- A base abre sem erros.
- Todas as telas dos roteiros carregam.
- Os dados ficticios aparecem com nomes consistentes.
- Existem vendas suficientes para relatorios.
- Existem produtos reais com imagem, estoque, custo e preco.
- Existem contas a pagar, contas a receber, recebimentos e movimentacoes financeiras.
- Existem rotas de entrega e custos de entrega.
- Existem funcionarios/RH e vendedor comissionado.
- Existe pedido ecommerce/app demo.
- Compra/XML, banho e tosa e veterinario ainda precisam de conferencia manual antes de gravar.
- Nenhuma tela exibe dado sensivel real.

## Evidencias da base demo

Registrar em uma nota interna:

- Data da preparacao.
- Ambiente usado.
- Usuario demo usado.
- Modulos habilitados.
- Videos gravados com essa base.
- Pendencias encontradas.
