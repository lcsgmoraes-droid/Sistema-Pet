# Protecao de Estoque por Validade - Design

## Objetivo

Criar um fluxo parametrizavel para proteger produtos perto do vencimento, removendo-os do estoque vendavel sem perder o rastreio fisico, operacional e financeiro. A meta e evitar venda indevida no PDV, ecommerce e canais online, enquanto o sistema registra o que foi conferido, descartado, trocado com fornecedor ou mantido bloqueado.

## Principios

- O sistema nao deve apagar estoque nem transformar alerta preventivo em perda definitiva automaticamente.
- Estoque fisico, estoque vendavel e estoque bloqueado por validade devem ser conceitos separados.
- Toda retirada de venda precisa deixar auditoria: produto, lote, validade, quantidade, usuario/rotina, data, motivo e acao posterior.
- Produto descartado por vencimento vira perda rastreavel para relatorios.
- Produto trocado com fornecedor deve sair do risco operacional sem contar como prejuizo definitivo.
- O usuario precisa decidir o destino operacional do lote, mas o sistema deve proteger a venda enquanto a decisao nao acontece.

## Configuracao

Adicionar parametros por tenant na configuracao de estoque:

- `protecao_validade_ativa`: liga/desliga a rotina.
- `dias_alerta_validade`: quantidade de dias antes do vencimento para bloquear, com padrao 15.
- `bloquear_pdv`: controla alerta/bloqueio no PDV.
- `bloquear_ecommerce`: remove saldo vendavel do ecommerce interno.
- `bloquear_integracoes_online`: prepara o saldo seguro para integracoes como Bling/marketplaces quando o produto sincroniza estoque.

## Estados Operacionais do Lote

O lote continua existindo, mas passa por estados operacionais:

- `ativo`: disponivel para venda.
- `bloqueado_validade`: retirado do estoque vendavel por estar dentro da janela configurada.
- `vencido_bloqueado`: vencido e retirado do estoque vendavel.
- `descartado`: baixa definitiva por perda/vencimento.
- `trocado_fornecedor`: resolvido por troca/devolucao com fornecedor.
- `liberado_manual`: usuario retornou o lote ao vendavel antes do vencimento.

O estado `liberado_manual` nao impede nova protecao no vencimento. Se o lote voltar ao vendavel e depois vencer, a rotina deve bloquear de novo.

## Fluxo Automatico

Uma rotina diaria por tenant deve:

1. Ler a configuracao de validade.
2. Buscar lotes com saldo positivo, data de validade e produto ativo.
3. Identificar lotes dentro da janela configurada ou ja vencidos.
4. Criar um bloqueio idempotente por lote e data de referencia.
5. Reduzir o estoque vendavel do produto pela quantidade bloqueada, sem apagar o saldo fisico.
6. Registrar movimentacao/auditoria com referencia ao bloqueio.
7. Criar lembrete operacional para o tenant.

Se a rotina rodar mais de uma vez no dia, nao deve duplicar bloqueios, lembretes ou movimentacoes para o mesmo lote.

## Lembretes e Acoes

A tela de Lembretes deve mostrar uma secao de validade com itens como:

`Produto X - lote Y - validade dd/mm/aaaa - Q unidades retiradas da venda`

Acoes disponiveis:

- `Descartado`: confirma perda definitiva. O sistema registra baixa por vencimento, valor de custo estimado, usuario e observacao opcional.
- `Trocado com fornecedor`: marca o lote como resolvido por troca/devolucao, sem entrar no relatorio de prejuizo como descarte.
- `Retornar ao vendavel`: libera o saldo para venda novamente, mantendo historico de que houve risco e decisao manual.
- `Ver produto/lote`: abre o cadastro ou movimentacoes do produto.

Se o lote ja estava bloqueado, `Descartado` deve baixar o saldo fisico e encerrar o bloqueio sem reduzir o estoque vendavel duas vezes. O mesmo cuidado vale para `Trocado com fornecedor`: resolve a pendencia e registra a saida/devolucao operacional sem classificar como perda por descarte.

Enquanto o lembrete estiver sem decisao, o PDV deve alertar ao tentar vender produto relacionado:

`Conferir produtos com validade em risco. Existe lote retirado da venda aguardando decisao.`

Depois de `Descartado`, `Trocado com fornecedor` ou `Retornar ao vendavel`, o alerta de pendencia deixa de aparecer para aquele lote. Se o lote retornado vencer depois, uma nova pendencia pode ser criada.

## PDV, Ecommerce e Integracoes

O PDV deve usar estoque vendavel, nao apenas estoque fisico. Para produtos com lote bloqueado e pendencia aberta, deve exibir alerta claro antes de adicionar/finalizar a venda.

O ecommerce interno deve consultar o saldo vendavel para nao vender quantidade bloqueada por validade.

Para integracoes online, o sistema deve preparar o saldo seguro como `estoque fisico - bloqueios ativos`. O envio efetivo para Bling/marketplaces deve respeitar a configuracao do tenant e os produtos que ja sincronizam estoque.

## Relatorios

Criar relatorio de validade/perdas com filtros por periodo, produto, categoria, fornecedor, status e lote.

Colunas sugeridas:

- Produto
- Codigo/SKU
- Lote
- Validade
- Quantidade bloqueada
- Quantidade descartada
- Custo unitario
- Custo total perdido
- Status final
- Fornecedor
- Usuario responsavel
- Data do bloqueio
- Data da decisao
- Observacao

O relatorio deve separar:

- perdas por descarte;
- trocas/devolucoes com fornecedor;
- lotes ainda pendentes;
- lotes retornados ao vendavel.

## Escopo do MVP

- Configuracao por tenant com ativacao e dias de alerta.
- Rotina manual/endpoint administrativo para processar lotes em risco, preparando depois agendamento automatico.
- Modelo persistente de bloqueio por validade.
- Lembretes com acoes de descartar, trocar com fornecedor e retornar ao vendavel.
- Ajuste de saldo vendavel usado por PDV/ecommerce.
- Alerta no PDV quando existir pendencia de validade para o produto.
- Relatorio inicial de perdas por validade em JSON e tela simples.

## Fora do MVP

- Integracao automatica direta com fornecedores.
- Campanha promocional automatica para liquidar produtos perto do vencimento.
- Workflow fiscal de devolucao ao fornecedor.
- Automacao completa de marketplace por canal especifico, exceto preparacao do saldo seguro.

## Criterios de Aceite

- Tenant com protecao desligada nao sofre bloqueio automatico.
- Tenant com protecao ligada e `dias_alerta_validade = 15` bloqueia lote com saldo positivo que vence em ate 15 dias.
- O bloqueio reduz estoque vendavel, mas preserva rastreio do estoque fisico/lote.
- A rotina e idempotente para o mesmo lote.
- Lembrete aparece com produto, lote, validade e quantidade bloqueada.
- Acao `Descartado` registra perda e aparece no relatorio de prejuizo.
- Acao `Trocado com fornecedor` resolve a pendencia sem classificar como perda por descarte.
- Acao `Retornar ao vendavel` libera o saldo, mas permite novo bloqueio quando o lote vencer.
- PDV alerta enquanto houver pendencia aberta para produto/lote em risco.
- Relatorio permite ver total de custo perdido por vencimento no periodo.
