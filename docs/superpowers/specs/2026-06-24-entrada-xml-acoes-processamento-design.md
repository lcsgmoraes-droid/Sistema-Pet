# Entrada XML com acoes de processamento selecionaveis

## Contexto

Hoje o fluxo de entrada de nota por XML/PDF processa a nota como uma acao unica:
entrada de estoque/lotes, atualizacao de custo, revisao de preco, criacao de
contas a pagar e sincronizacao de estoque com o Bling. Esse padrao e rapido para
notas comuns, mas e perigoso para bonificacao, brinde, amostra, remessa sem
cobranca ou notas com custo fiscal fora da realidade operacional.

O objetivo e manter o fluxo rapido, mas permitir que o sistema sugira e o usuario
confirme exatamente quais efeitos a nota tera antes do processamento.

## Decisao Aprovada

Usar a opcao incremental no fluxo atual: manter o preview/revisao antes de
processar a nota e adicionar um bloco de acoes com checkboxes inteligentes,
preenchidos conforme o contexto da NF e editaveis manualmente.

## Acoes Disponiveis

- Lancar estoque, lotes e validade.
- Atualizar custo dos produtos.
- Atualizar preco de venda revisado.
- Gerar contas a pagar.

As acoes devem ser enviadas explicitamente ao backend no endpoint de
processamento. O backend nao deve inferir silenciosamente um efeito colateral
quando a flag correspondente estiver desmarcada.

## Sugestao Automatica

O sistema deve analisar o XML para sugerir as checkboxes iniciais. Os sinais
principais sao CFOP, natureza da operacao, existencia de duplicatas/cobranca,
valor dos itens e termos como bonificacao, brinde, amostra ou remessa.

Padrao para nota comum:

- Lancar estoque, lotes e validade: marcado.
- Atualizar custo dos produtos: marcado.
- Atualizar preco de venda revisado: marcado somente quando houver revisao de
  preco aplicada.
- Gerar contas a pagar: marcado.

Padrao para bonificacao, brinde, amostra ou remessa sem cobranca:

- Lancar estoque, lotes e validade: marcado.
- Atualizar custo dos produtos: desmarcado.
- Atualizar preco de venda revisado: desmarcado.
- Gerar contas a pagar: desmarcado.

O usuario pode alterar qualquer opcao antes de confirmar. A tela deve mostrar um
aviso curto explicando a sugestao, por exemplo: "Bonificacao detectada: estoque
sera lancado usando o custo atual do sistema; custo, preco e financeiro ficaram
desmarcados."

## Regra de Custo para Bonificacao

Quando a nota for processada com estoque marcado e atualizacao de custo
desmarcada, a entrada fisica deve ocorrer sem contaminar o cadastro de custo do
produto.

Nessa situacao:

- o lote e a movimentacao de estoque usam o custo atual do produto no sistema;
- se o produto nao tiver custo atual valido, o custo calculado da NF pode ser
  usado como fallback somente para valorizar a movimentacao/lote;
- o campo de custo do produto nao deve ser alterado;
- o custo do vinculo com fornecedor nao deve ser alterado;
- deve haver observacao/historico indicando que a nota foi processada sem
  atualizacao de custo por opcao da entrada.

## Validade e Lotes

Validade sempre acompanha a acao de lancar estoque. Se o XML trouxer rastros,
lotes, fabricacao ou validade, esses dados devem ser usados automaticamente nos
lotes criados.

Se um produto que controla validade nao tiver validade detectada, a tela deve
avisar antes de processar e permitir preenchimento manual quando possivel. Produto
sem controle de validade pode seguir sem bloqueio.

## Backend

O endpoint `POST /notas-entrada/{nota_id}/processar` deve aceitar flags explicitas
no payload:

- `lancar_estoque`
- `atualizar_custo`
- `atualizar_preco_venda`
- `gerar_contas_pagar`

O comportamento esperado e:

- `lancar_estoque=false`: nao cria lotes, nao movimenta estoque e nao agenda sync
  Bling por entrada de NF.
- `atualizar_custo=false`: nao altera `Produto.preco_custo` nem
  `ProdutoFornecedor.preco_custo`.
- `atualizar_preco_venda=false`: nao aplica alteracoes de preco de venda no
  processamento.
- `gerar_contas_pagar=false`: nao cria contas a pagar da NF.

A nota deve registrar quais acoes foram aplicadas para auditoria e para a reversao
agir somente sobre o que de fato foi criado/alterado.

## Reversao

A reversao deve respeitar as acoes registradas na nota:

- se nao houve contas a pagar, nao ha contas a excluir;
- se nao houve atualizacao de custo/preco, nao ha restauracao de custo/preco;
- se houve estoque/lotes, a reversao remove estoque/lotes/movimentacoes como
  hoje;
- a sincronizacao com Bling so deve ser agendada se houve alteracao real de
  estoque.

## Frontend

Na revisao da nota, antes do botao final de confirmacao, deve existir um bloco
compacto "Acoes ao processar" com as quatro checkboxes. Abaixo, a tela deve
mostrar um resumo operacional:

- quantidade de itens que entram no estoque;
- quantidade de produtos com custo atualizado;
- quantidade de precos de venda atualizados;
- quantidade de contas a pagar que serao criadas;
- quantidade de itens com validade detectada e sem validade.

As sugestoes devem vir do preview do backend para evitar duplicar regra fiscal no
frontend. O frontend apenas apresenta e permite ajuste manual.

## Fora de Escopo Nesta Etapa

- Criar um motor configuravel de regras por fornecedor/CFOP.
- Separar o processamento em botoes independentes apos a nota.
- Automatizar saneamento retroativo de notas ja processadas.
- Alterar o fluxo de importacao de pedido Bling ou reserva de estoque.

## Validacao Esperada

- Nota comum processa com comportamento equivalente ao atual quando todas as
  acoes aplicaveis estiverem marcadas.
- Bonificacao sugerida processa estoque/lote/validade sem alterar custo, preco ou
  financeiro.
- Payload manual com custo desmarcado usa custo atual do sistema no lote e na
  movimentacao.
- Reversao desfaz somente efeitos realmente aplicados.
- Testes cobrem sugestao automatica, flags do processamento, regra de custo atual
  para bonificacao e reversao parcial.
