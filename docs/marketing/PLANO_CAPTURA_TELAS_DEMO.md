# Plano de Captura de Telas Demo - Sistema Pet

Uso: transformar os roteiros de marketing em uma fila pratica de gravacao de
telas reais do Sistema Pet.

Este documento deve ser usado depois de preparar a base demo em
`docs/marketing/BASE_DEMO_GRAVACAO.md` e validar os dados estruturados com
`scripts/test_marketing_demo_package.py`.

## Saida esperada

Ao final da captura, deve existir material bruto suficiente para montar:

- criativos de venda sobre estoque, recebimentos, lucro, agenda e ecommerce;
- demos curtas das principais funcionalidades;
- video de onboarding/configuracao inicial;
- apresentacao consultiva horizontal do Sistema Pet.

## Padrao de captura

| Item | Padrao |
|---|---|
| Ambiente | Tenant/base de demonstracao, sem dados reais |
| Empresa | Pet Feliz Demo |
| Navegador | Zoom entre 90% e 100% |
| Formato bruto | 16:9 quando a tela tiver tabela; 9:16 apenas para cortes curtos |
| Movimento | Mouse lento, uma acao por take |
| Narracao | Preferir gravar tela limpa e narrar depois |
| Corte | Cada take deve ter inicio e fim claros |

## Conferencia antes de gravar

Regra central: Nao gravar dados reais.

1. Rodar `python scripts/test_marketing_demo_package.py`.
2. Rodar `python scripts/test_marketing_demo_seed_plan.py`.
3. Rodar `python scripts/test_marketing_demo_seed_apply.py`.
4. Rodar `python scripts/validar_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --markdown`.
5. Gerar o manifesto com `python scripts/gerar_seed_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --tenant-slug tenant_demo --format markdown`.
6. Simular a aplicacao com `python scripts/aplicar_seed_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --tenant-slug atacadaopetpp --tenant-email atacadaopetpp@gmail.com --dry-run`.
7. Se o tenant for DEV/demo confirmado, aplicar os cadastros-base seguros com `python scripts/aplicar_seed_base_demo_marketing.py --json docs/marketing/base-demo/dados_base_demo_sistema_pet.json --tenant-slug atacadaopetpp --tenant-email atacadaopetpp@gmail.com --environment development --apply`.
8. Conferir manualmente empresa, usuarios, impostos, compras, ecommerce e servicos veterinarios, pois a aplicacao automatica ainda pula essas secoes.
9. Confirmar que a tela nao exibe CPF, CNPJ real, telefone real, email real, token ou webhook.
10. Fechar notificacoes, abas pessoais e extensoes visiveis.
11. Abrir somente a tela inicial do take.
12. Conferir se o dado demo aparece com nome consistente.

## Fila de takes prioritarios

| Take | Video principal | Formato | Tela inicial | Dado demo | Acao gravada | Foco visual | Criterio de aceite |
|---|---|---|---|---|---|---|---|
| 01 | Configuracao inicial | 16:9 | `/ajuda` | Pet Feliz Demo | Abrir Introducao Guiada e mostrar resumo | Etapas obrigatorias e condicionais | Usuario entende por onde comecar |
| 02 | Configuracao inicial | 16:9 | Introducao Guiada | Financeiro obrigatorio | Abrir etapa de financeiro | Bancos, formas de pagamento e categorias | Fica claro que financeiro vem antes da venda |
| 03 | Financeiro antes da primeira venda | 16:9 | `/cadastros/financeiro/formas-pagamento` | PIX, Dinheiro, Cartao credito | Mostrar formas de pagamento cadastradas | Lista simples, sem valores reais | Formas estao legiveis |
| 04 | Financeiro antes da primeira venda | 16:9 | Bancos/contas | Conta Banco Demo | Mostrar banco e categoria financeira | Conta e classificacao do recebimento | Explica destino e classificacao do dinheiro |
| 05 | Recebimentos baguncados | 16:9 e 9:16 | `/pdv` | Maria Oliveira, Racao Adulto 10kg | Finalizar venda com PIX/cartao demo | Pagamento no caixa | Venda nasce com forma de pagamento clara |
| 06 | Recebimentos baguncados | 16:9 | Contas a receber | Venda demo | Abrir recebimento gerado pela venda | Status, vencimento e forma | Mostra reflexo financeiro da venda |
| 07 | Produto, PDV e estoque | 16:9 | `/produtos` | Racao Adulto 10kg | Abrir produto e mostrar preco/custo/estoque | Produto antes da venda | Produto tem cadastro suficiente para vender |
| 08 | Estoque que some | 16:9 e 9:16 | `/pdv` | Racao Adulto 10kg | Vender uma unidade | Produto saindo no PDV | Acao fica clara em poucos segundos |
| 09 | Estoque que some | 16:9 | Produtos/estoque | Racao Adulto 10kg | Conferir estoque ou movimentacao apos venda | Baixa/conferencia de estoque | Fica claro que venda e estoque se conectam |
| 10 | Compras e XML | 16:9 | `/compras/entrada-xml` | Distribuidora Pet Brasil | Abrir entrada XML demo | Itens, fornecedor e conferencia | Nao expor CNPJ real |
| 11 | Compras e XML | 16:9 | Produtos/estoque | Shampoo/Petisco demo | Mostrar custo/estoque apos compra | Custo e quantidade | Compra ajuda a explicar custo e estoque |
| 12 | Banho e tosa | 16:9 e 9:16 | `/banho-tosa/servicos` | Banho medio completo | Mostrar servico cadastrado | Duracao e preco | Servico esta pronto para agenda |
| 13 | Banho e tosa | 16:9 | `/banho-tosa/agenda` | Thor | Abrir/criar agendamento demo | Pet, tutor, horario e status | Agenda parece real, sem excesso de itens |
| 14 | Banho e tosa | 16:9 | `/banho-tosa/fila` | Thor/Luna | Mostrar fila do dia | Status da rotina | Equipe entende o que esta em andamento |
| 15 | Veterinario | 16:9 | `/veterinario/agenda` | Dra. Ana Martins, Thor | Abrir atendimento demo | Agenda, tutor e pet | Sem diagnostico real ou dado sensivel |
| 16 | Veterinario | 16:9 | Consulta/pet | Thor | Mostrar historico ou ficha demo | Contexto do atendimento | Mostra organizacao sem expor saude real |
| 17 | Ecommerce e app | 16:9 | `/ecommerce/configuracoes` | Pet Feliz Demo Online | Mostrar configuracao/canal online | Loja demo ativa | Nao exibir chave ou link sensivel |
| 18 | Ecommerce e app | 16:9 e 9:16 | Pedidos online | Ana Costa | Abrir pedido pendente demo | Pedido conectado a operacao | Pedido online fica conectado ao sistema |
| 19 | Relatorios gerenciais | 16:9 | Dashboard/relatorios | Periodo demo | Filtrar periodo curto | Vendas, financeiro ou estoque | Um indicador por vez fica legivel |
| 20 | Visao geral Sistema Pet | 16:9 | Menu principal | Modulos ativos | Passeio curto pelos modulos | PDV, estoque, financeiro, servicos | Serve como cola para apresentacao consultiva |

## Ordem recomendada de gravacao

1. Gravar primeiro os takes horizontais de configuracao e financeiro.
2. Gravar PDV, produto e estoque no mesmo bloco para preservar continuidade.
3. Gravar compras/XML antes de relatorios, para gerar contexto de custo.
4. Gravar banho e tosa e veterinario em blocos separados.
5. Gravar ecommerce/app por ultimo, depois de conferir catalogo e pedidos demo.
6. Regravar em 9:16 apenas os trechos que viram criativos curtos.

## Pacote por video

### Estoque que some

Takes minimos: 07, 08 e 09.

Fala guia:

```text
Seu estoque nao pode depender de memoria. O produto entra no cadastro, sai pela
venda e precisa deixar rastro para conferencia.
```

Texto de tela:

```text
Produto cadastrado
Venda no PDV
Conferencia de estoque
```

### Recebimentos baguncados

Takes minimos: 03, 05 e 06.

Fala guia:

```text
PIX, dinheiro e cartao precisam nascer organizados desde o caixa para facilitar
a conferencia depois.
```

Texto de tela:

```text
Formas de pagamento
Venda registrada
Recebimento para conferir
```

### Lucro real

Takes minimos: 04, 07, 11 e 19.

Fala guia:

```text
Vender muito nao basta. O gestor precisa olhar custo, venda, financeiro e
resultado no mesmo raciocinio.
```

Texto de tela:

```text
Custo
Venda
Financeiro
Resultado
```

### Configuracao inicial

Takes minimos: 01 e 02.

Fala guia:

```text
O usuario novo nao precisa adivinhar a ordem. O Sistema Pet mostra o que vem
primeiro e o que depende dos modulos ativos.
```

Texto de tela:

```text
Comece pelo essencial
Financeiro antes da venda
Modulos por etapa
```

### Produto, PDV e estoque

Takes minimos: 07, 08 e 09.

Fala guia:

```text
O cadastro do produto alimenta a venda, e a venda cria uma rotina de conferencia
para o estoque e o financeiro.
```

Texto de tela:

```text
Produto
Venda
Estoque
```

### Financeiro antes da primeira venda

Takes minimos: 03, 04, 05 e 06.

Fala guia:

```text
Antes da primeira venda, cadastre formas de pagamento, banco e categorias. Assim
o recebimento ja nasce com contexto para conferencia.
```

Texto de tela:

```text
Formas de pagamento
Banco
Categoria
Recebimento
```

## Checklist de take aprovado

- Tela existe no sistema atual.
- Dado demo usado aparece em `dados_base_demo_sistema_pet.json`.
- Nenhum dado real aparece no video.
- O take dura entre 5s e 20s, salvo demonstracao longa.
- Uma unica acao principal acontece no take.
- A informacao importante fica legivel em tela cheia.
- O mouse nao cobre botoes, valores ou status.
- O take pode ser reutilizado em pelo menos um video.

## Controle de captura

| Take | Gravado | Revisado | Observacao |
|---|---|---|---|
| 01 | Pendente | Pendente |  |
| 02 | Pendente | Pendente |  |
| 03 | Pendente | Pendente |  |
| 04 | Pendente | Pendente |  |
| 05 | Pendente | Pendente |  |
| 06 | Pendente | Pendente |  |
| 07 | Pendente | Pendente |  |
| 08 | Pendente | Pendente |  |
| 09 | Pendente | Pendente |  |
| 10 | Pendente | Pendente |  |
| 11 | Pendente | Pendente |  |
| 12 | Pendente | Pendente |  |
| 13 | Pendente | Pendente |  |
| 14 | Pendente | Pendente |  |
| 15 | Pendente | Pendente |  |
| 16 | Pendente | Pendente |  |
| 17 | Pendente | Pendente |  |
| 18 | Pendente | Pendente |  |
| 19 | Pendente | Pendente |  |
| 20 | Pendente | Pendente |  |

## Prompt para editar um take com IA

```text
Transforme este take gravado do Sistema Pet em um corte curto.

Contexto:
- Video: [nome do video]
- Take: [numero e descricao]
- Publico: dono ou gestor de pet shop, banho e tosa ou clinica veterinaria
- Objetivo: mostrar uma acao real do sistema sem inventar tela

Regras:
- Preservar a tela real.
- Cortar pausas e movimentos longos.
- Aplicar zoom apenas quando ajudar a leitura.
- Legenda curta, sem cobrir botoes ou valores.
- Nao prometer resultado garantido.
- Encerrar com CTA simples.
```
