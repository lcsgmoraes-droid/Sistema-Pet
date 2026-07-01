# Transferencia Parceiro: baixa por valor

Data: 2026-06-30

## Objetivo

Permitir baixar varias transferencias de um parceiro informando um valor total,
sem transformar a operacao em venda PDV. O fluxo deve manter o historico de
estoque e gerar o efeito financeiro correto conforme o tipo de baixa.

## Escopo desta fase

Esta fase entrega uma baixa assistida por pessoa/parceiro:

- o usuario informa pessoa, valor da baixa, data e tipo de baixa;
- o sistema lista transferencias em aberto da pessoa;
- se houver filtro de periodo ativo, a lista respeita esse periodo;
- o sistema sugere a distribuicao automaticamente, com checkbox por transferencia;
- a sugestao padrao usa a mais antiga primeiro, mas a tela pode permitir trocar
  para mais nova primeiro;
- o usuario pode revisar valores antes de confirmar;
- a ultima transferencia pode receber baixa parcial.

Fica fora desta fase:

- campo "valor lancado" diferente do custo;
- relatorio de ganho/perda em transferencia parceiro;
- entrada completa de "transferencia recebida de parceiro" para gerar contas a
  pagar e entrada de estoque. Essa melhoria fica para uma fase posterior.

## Tipos de baixa

### Recebimento financeiro

Usado quando o parceiro pagou em dinheiro, Pix, transferencia, cartao ou outra
forma financeira.

Regras:

- baixa as contas a receber de transferencia selecionadas;
- cria registros de recebimento;
- respeita a forma de pagamento escolhida;
- para cartao, deve seguir a mesma regra ja configurada no sistema para prazo,
  taxas e recebimento da operadora;
- aparece no financeiro/fluxo de caixa/DRE como entrada de transferencia
  parceiro, separado de vendas PDV.

### Acerto / compensacao

Usado quando o parceiro tambem tem valor a receber da empresa.

Regras:

- baixa as transferencias selecionadas;
- permite selecionar contas a pagar existentes da mesma pessoa;
- permite, nesta fase se for simples e seguro, criar uma nova conta a pagar de
  acerto/compra de mercadoria diretamente no modal;
- registra a baixa do contas a receber e a baixa/compensacao do contas a pagar;
- nao entra como dinheiro recebido.

### Produto devolvido

Usado quando a pessoa devolveu o produto que tinha pegado.

Regras:

- baixa as transferencias selecionadas sem gerar financeiro;
- pergunta se o produto deve voltar para o estoque;
- se voltar, registra entrada de estoque vinculada a transferencia;
- se nao voltar, exige observacao para auditoria;
- mantem rastro de quais transferencias foram baixadas pela devolucao.

## Experiencia de tela

A baixa por valor deve aparecer no historico de Transferencia Parceiro como uma
acao de baixa por pessoa. O fluxo sugerido:

1. selecionar pessoa ou usar pessoa filtrada;
2. informar valor total da baixa;
3. escolher tipo de baixa;
4. revisar a lista de transferencias abertas com checkbox e valor aplicado;
5. confirmar.

A tela deve deixar claro:

- saldo total em aberto da pessoa;
- valor informado para baixa;
- valor distribuido nas transferencias marcadas;
- diferenca ainda nao aplicada;
- saldo remanescente apos confirmar.

## Backend

Criar uma rota dedicada para a baixa em lote por pessoa, sem inflar os arquivos
atuais de transferencia parceiro.

Arquivos sugeridos:

- `backend/app/estoque/transferencia_parceiro_baixa_lote_routes.py`
- `backend/app/estoque/transferencia_parceiro_baixa_lote_service.py`
- `backend/app/estoque/transferencia_parceiro_devolucao_service.py`

A rota principal deve apenas registrar o subrouter novo.

O service deve:

- buscar transferencias abertas da pessoa no tenant atual;
- aplicar filtro de periodo quando informado;
- validar que as transferencias selecionadas pertencem a pessoa e ao tenant;
- impedir valor maior que o saldo selecionado;
- distribuir valores com duas casas decimais;
- criar um recebimento/acerto/devolucao por transferencia afetada;
- atualizar `valor_recebido`, `status`, `data_recebimento` e observacoes;
- fazer rollback se qualquer item falhar.

## Frontend

Criar componentes pequenos na pasta existente:

- `BaixaLoteTransferenciaPanel.jsx`
- `BaixaLoteTransferenciaLista.jsx`
- `BaixaLoteTransferenciaResumo.jsx`

O controller atual pode expor handlers, mas a logica pura de distribuicao deve
ficar em `transferenciaParceiroUtils.js` ou em um novo helper dedicado, com
teste unitario.

## Arquivos pequenos

Nenhum arquivo novo deve nascer grande. Meta:

- componentes React abaixo de 300 linhas;
- services/backend abaixo de 400 linhas;
- arquivos existentes nao devem ultrapassar os limites de refatoracao ja usados
  no projeto.

Se alguma parte ameacar crescer demais, dividir antes de implementar.

## Testes

Backend:

- distribuicao de R$ 1.000 em tres transferencias de R$ 400 gera 400, 400 e
  200, deixando 200 em aberto;
- filtro de periodo limita a lista considerada;
- transferencia de outra pessoa ou tenant nao pode ser baixada;
- recebimento financeiro cria recebimentos e atualiza status;
- produto devolvido nao cria recebimento financeiro;
- acerto nao entra como dinheiro recebido e compensa contas a pagar.

Frontend:

- helper distribui valor mais antigo primeiro;
- helper distribui valor mais novo primeiro;
- checkbox remove transferencia da distribuicao;
- diferenca e saldo remanescente sao calculados corretamente.

## Criterio de aceite

Lucas consegue abrir Transferencia Parceiro, escolher uma pessoa com varias
transferencias em aberto, informar um valor total e confirmar uma baixa que:

- quita as transferencias mais antigas selecionadas;
- deixa parcial a ultima quando o valor acabar;
- registra o financeiro correto quando houver dinheiro;
- permite acerto sem entrada de dinheiro;
- permite devolucao sem gerar financeiro;
- nao mistura essa operacao com vendas PDV.
