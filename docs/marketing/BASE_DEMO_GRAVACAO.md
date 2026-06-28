# Base Demo para Gravacao - Sistema Pet

Uso: preparar um ambiente ficticio e consistente para gravar videos do Sistema
Pet sem expor dados reais de clientes.

Arquivos executaveis da base demo:

- Dados estruturados: `docs/marketing/base-demo/dados_base_demo_sistema_pet.json`
- Validador/checklist: `scripts/validar_base_demo_marketing.py`
- Contrato: `scripts/test_marketing_demo_package.py`

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
| 9 | Fornecedor | Distribuidora Pet Brasil | Usado em compras e XML |
| 10 | Produto | Racao Adulto 10kg | Usado em estoque, PDV, ecommerce e relatorios |

## Produtos demo

| Produto | Categoria | Preco venda | Custo sugerido | Estoque inicial |
|---|---|---:|---:|---:|
| Racao Adulto 10kg | Racoes | 189,90 | 128,00 | 20 |
| Shampoo Neutro Pet 500ml | Higiene | 39,90 | 18,00 | 15 |
| Coleira Ajustavel M | Acessorios | 49,90 | 22,00 | 12 |
| Petisco Natural 120g | Petiscos | 24,90 | 10,00 | 30 |

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

Use fornecedor ficticio:

- Distribuidora Pet Brasil.
- Pedido de compra: produtos de racao, shampoo e petisco.
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

## Checklist antes de gravar

- Rodar `python scripts/test_marketing_demo_package.py`.
- Rodar `python scripts/validar_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --markdown`.
- A base abre sem erros.
- Todas as telas dos roteiros carregam.
- Os dados ficticios aparecem com nomes consistentes.
- Existem vendas suficientes para relatorios.
- Existem produtos com estoque.
- Existe ao menos uma compra/entrada XML.
- Existem agendamentos de banho e tosa.
- Existe um atendimento veterinario demo.
- Existe um pedido ecommerce/app demo.
- Nenhuma tela exibe dado sensivel real.

## Evidencias da base demo

Registrar em uma nota interna:

- Data da preparacao.
- Ambiente usado.
- Usuario demo usado.
- Modulos habilitados.
- Videos gravados com essa base.
- Pendencias encontradas.
