# Ajustes de estoque, caixa, vendas e entregador — validação local

Data: 2026-10-09.
PR: não aberto; trabalho solicitado somente local.
Commit: esta ficha acompanha o commit da branch abaixo.
Branch: `codex/ajustes-estoque-caixa-vendas-entregador`.
Base: `origin/main` em `5cbd05c18`, conferida no início e no fechamento.
Ambiente: homologação local, `http://127.0.0.1:18080`, com dados fictícios.
Responsável: Codex / Lucas.
Resultado: implementação e testes locais concluídos.
Impacto: novos registros de recebimento passam a identificar o caixa recebedor;
identificações de lotes preservam saldo/custo; alterações de vendas recalculam benefícios.
Próxima ação: revisão de Lucas no ambiente local; publicação depende de pedido específico.

## Uso e comportamento

- **Produto → Movimentações → Lotes e validade:** informar a quantidade atual
  que pertence a um lote e sua validade. Repetir o lote substitui a quantidade,
  sem somar estoque. Quantidades identificadas não podem exceder o saldo, salvo
  correção para baixo de divergência preexistente. Reservas são preservadas.
- **Cadastro/edição do produto → Estoque/Lotes:** o botão
  “Salvar e abrir lançamentos de estoque e lotes” salva e leva às movimentações.
  Mantém as confirmações de alteração dos preços dos produtos compostos.
- **Recebimentos:** pagamentos de vendas anteriores entram no caixa que recebeu
  a parcela; o caixa original conserva o registro da venda. Dinheiro compõe o
  saldo físico; PIX e cartões aparecem no resumo por forma e na auditoria.
  A conclusão de uma baixa parcial não baixa o estoque novamente.
- **Meus Caixas → Auditar:** conferir vendas, pagamentos e lançamentos
  individualmente, filtrar por forma de pagamento e consultar o histórico.
  Alterar a venda invalida sua conferência anterior.
- **Meus Caixas → Reabrir:** informar motivo. O fechamento anterior permanece
  registrado no histórico e será necessário fechar novamente. A reabertura
  física exige que não exista outro caixa ativo no escopo do operador/empresa;
  a auditoria pode ser feita sem fechar o caixa atual.
- **Benefícios:** reabrir suspende cupons elegíveis e revoga o saldo disponível
  de cashback da venda. Ao finalizar novamente, recalcula com os itens/valores
  atuais e a regra original; não duplica o que já foi usado ou expirou.
  Excesso de benefício já consumido fica registrado para análise.
- **Pessoa/entregador → Acerto financeiro → Sem acerto:** permite salvar
  o entregador sem periodicidade e limpa dias anteriormente configurados.
  A opção não impede os lançamentos normais de entrega/comissão.

## Integridade e migrations

Head única: `zzzm20261009a1`.

- `zzzk20261009a1`: adiciona `venda_pagamentos.caixa_id`. O backfill associa
  somente recebimento em loja física cuja data identifica um único caixa do
  mesmo tenant. Intervalos ambíguos ficam sem associação; não se atribui o
  recebimento ao caixa original por suposição.
- `zzzl20261009a1`: adiciona `produto_lotes.apenas_identificacao`, padrão
  falso para lotes existentes. Novas identificações não acionam baixa automática
  por vencimento, não mudam custo e não ativam controle obrigatório de lotes.
  Lotes reais de entrada preservam sua regra anterior.
- `zzzm20261009a1`: adiciona `configuracoes_entrega.metodo_km_entrega` quando
  ausente, com padrão `auto_rota`. Preserva a configuração dos ambientes legados
  que já receberam a coluna pelo endpoint de configurações. A criação de uma
  rota passa a funcionar em banco migrado sem abrir antes essa tela.
- Escritores e fechamento compartilham bloqueio da linha do caixa. A devolução
  em dinheiro adota a mesma ordem Caixa → Venda.
- Auditoria do fechamento, reabertura e conferência é gravada na mesma transação
  da alteração, respeitando tenant e acesso individual/compartilhado.

## Diagnóstico da devolução da Loja 1

Inspeção via SSH autorizada no pedido, somente leitura, com transação SQL
explicitamente read-only. Produção estava em `5cbd05c18`.

Na venda `1364727`, os pagamentos registrados eram R$ 38,90 e R$ 56,90 em
cartão de débito. Havia R$ 38,90 recebido e somente R$ 18,00 pendente em contas
a receber. A nova finalização havia abatido o repasse anterior do cartão,
reduzindo indevidamente a nova conta. O bloqueio da devolução também confundia
o repasse pendente da operadora com dívida do cliente.

O código local separa repasse da operadora da baixa de dívida do cliente.
Para permitir devolução de cartão antes do repasse, exige pagamentos válidos
da mesma venda/tenant/forma cobrindo as contas registradas. Crediário pendente,
cartão insuficiente, forma desconhecida e pagamento estornado continuam bloqueados.
Cartões legados sem vínculo com forma de pagamento não são liberados por inferência.

**Os registros dessa venda em produção não foram alterados.** A divergência
histórica deve ser conciliada separadamente antes de considerar o caso encerrado
em produção. Não houve deploy, push ou alteração do banco remoto.

## Evidências de validação

Comandos executados:

- `FLUXO_UNICO.bat check` no início.
- `scripts/homologacao_local.ps1 -Acao subir`: imagens reconstruídas,
  migrations aplicadas e frontend/backend/PostgreSQL saudáveis.
- `python -m pytest` em 27 módulos de regressão relacionados aos ajustes:
  **252 testes distintos passaram**, incluindo migrations e disputas reais de
  recebimento/fechamento/finalização em PostgreSQL local descartável.
  Foram 250 no conjunto inicial e 2 novos após a correção da dupla baixa;
  os 37 testes afetados pela última correção passaram novamente.
- Jornada HTTP local:
  `tests/test_plano_basico_e2e.py`,
  `tests/test_caixa_auditoria_e2e.py` e
  `tests/test_estoque_entregador_local_e2e.py`: **4 passaram**.
  Confirmaram recebimento no novo caixa, preservação do anterior, reabertura,
  conferência invalidada após editar venda, saldo/custo/extrato preservados ao
  identificar lote e cadastro de entregador sem acerto.
- `node --test` nos testes de revisão/contagem/textos do caixa e
  `entregadorAcerto.test.mjs`: **8 passaram**.
- Ruff nos arquivos Python alterados; ESLint sem avisos e Prettier nos arquivos
  JavaScript/JSX alterados; `git diff --check`: passaram.
- `npm run build`, também executado no build Docker do frontend: passou.
  Avisos preexistentes de chunk grande do PDV e variável de Analytics ausente
  na homologação não impediram o build.

Os testes de lote incluem saldo 30 com identificação de 5, consumo clínico e
fracionamento de 8, publicação do produto e preservação do controle de lotes
preexistente. Os testes de benefícios cobrem aumento/redução/remoção, reaberturas
repetidas, devolução posterior, cashback usado/expirado e isolamento por tenant.

Falhas encontradas nas primeiras jornadas foram corrigidas: fixtures compartilhadas
dos testes, preparação de saldo pelo endpoint real de entrada e dupla baixa de
estoque na última parcela. A execução final das quatro jornadas passou.

## Aceite adicional pelo sistema — 09/10/2026, 11h04–11h24

Pedido adicional de Lucas: executar os testes no sistema e explicar a Loja 1.
Chrome conectado ao perfil existente, em uma aba exclusivamente local. A tela
identificou a empresa fictícia “CorePet Homologacao Local”.

Testes pela interface:

- **Caixa nº 6 / ID 7:** auditoria exibiu a venda de outro caixa recebida neste,
  seus produtos e o resumo por forma (PIX R$ 10 e dinheiro R$ 15). Conferência
  individual dos lançamentos persistiu no histórico. O caixa fechado foi
  reaberto com motivo pela tela, preservando o fechamento anterior.
- **Produto ID 68 / SKU UI-VALIDADE-1791554829320:** cadastro pela tela e atalho
  “Salvar e abrir lançamentos de estoque e lotes” funcionaram. Depois de uma
  entrada real de 5 unidades, informar e repetir `LOTE-UI-01`, quantidade 3,
  validade 09/10/2030 manteve saldo 5, custo R$ 6 e somente uma movimentação
  (a entrada real). A identificação permaneceu única.
- **Fornecedor/entregador ID 22:** salvo pela tela como pessoa física com “Sem
  acerto”. Reabrir o cadastro confirmou entregador ativo e opção persistida.
- **Devoluções de cartão:** vendas fictícias `202610090009` e `202610090018`
  aceitaram a devolução por crédito de R$ 56,90 com repasse da operadora ainda
  pendente. Na segunda, já com o ajuste adicional de interface, crédito,
  carimbos, cupom e status atualizaram imediatamente sem recarregar o navegador.
  O botão de recebimento ficou desabilitado na devolução total.

Jornadas HTTP adicionais:

- `tests/test_caixa_baixa_lote_e2e.py`: **1 passou**. Duas vendas fictícias
  datadas em 07/10 e 08/10, originadas no caixa 1, receberam PIX R$ 12 e dinheiro
  R$ 18 no caixa ID 7. Foram 3 pagamentos vinculados ao caixa atual e somente
  1 movimento físico de dinheiro. A auditoria não duplicou PIX, o caixa original
  não ganhou recebimento retroativo e o estoque não foi baixado novamente.
- `tests/test_beneficios_devolucao_local_e2e.py`: **2 passaram**. Venda alterada
  de R$ 40 → 60 → 20 → 10 → 10 acompanhou cashback R$ 4 → 6 → 2 → 1 → 1 e
  carimbos 4 → 6 → 2 → 1 → 1. Remoção de produto, redução abaixo do valor já pago
  e nova finalização sem pagamento não duplicaram benefícios. Cupom de recompra
  foi suspenso abaixo do mínimo e preservou identidade/validade. Devolução de
  cartão manteve o repasse pendente, recompôs estoque e gerou crédito uma vez,
  mesmo ao repetir a operação; não gerou movimento de caixa. Parâmetros
  temporários das campanhas foram restaurados e a campanha exclusiva arquivada.
- `tests/test_estoque_entregador_local_e2e.py::test_lancar_rota_com_entregador_sem_acerto`:
  **1 passou**. Uma venda de entrega e sua rota foram criadas, relidas e
  vinculadas ao entregador sem periodicidade, mantendo a opção “Sem acerto”.

Falhas adicionais encontradas e corrigidas:

- Finalizar novamente uma venda reduzida abaixo do valor já recebido rejeitava
  até `pagamentos=[]`. A comparação agora considera saldo mínimo zero, conserva
  pagamentos anteriores e continua rejeitando nova entrada numa venda já paga.
- O sucesso da devolução recarregava somente o caixa. Agora também atualiza a
  venda exibida e o crédito/contexto do cliente; devolução de outra venda
  preserva o carrinho atual. Devoluções parciais continuam permitindo recebimento.
- O lançamento de rota falhava com HTTP 500 porque faltava a coluna de método
  de KM em banco criado exclusivamente por migrations. A nova migration resolve
  a ausência e respeita configurações legadas.

Verificações finais desta etapa:

- **31 passaram**, sem skips: testes de pagamentos/finalização/atomicidade em
  PostgreSQL descartável, incluindo concorrência, e migration de método de KM.
  Incluem 4 novas instâncias de finalização e 2 cenários novos de migration.
- **10 testes Node passaram** nos fluxos de saldo/atualização/estados de devolução.
- Ruff, ESLint sem avisos, verificação de formato e `git diff --check`: passaram.
- Backend e frontend de homologação reconstruídos a partir do código local;
  migration `zzzm20261009a1` aplicada; build Vite e health checks passaram.
- Evidências visuais salvas nos arquivos `auditoria-caixa-local.png`,
  `lote-validade-local.png`, `entregador-sem-acerto-local.png` e
  `devolucao-atualizada-local.png` na pasta de visualizações desta conversa.

Somando as jornadas anteriores e adicionais, **9 testes HTTP distintos passaram**.
Nenhuma alteração foi enviada ao GitHub ou aplicada em produção. O PostgreSQL
descartável dos testes foi parado; o sistema de homologação local permanece disponível.

## Confirmação complementar de preços e descontos

Novo pedido de Lucas: confirmar recebimentos de saldos anteriores e ajuste dos
benefícios de venda já paga ao alterar quantidades e valores.

O aceite `test_reabrir_alterar_preco_e_desconto_ajusta_beneficios_sem_novo_recebimento`
foi acrescentado em `tests/test_beneficios_devolucao_local_e2e.py` e passou
em 80,50 segundos. Venda fictícia `202610090023`, ID 28, cliente 35, produto 85.
Sempre 2 unidades e saldo de estoque 18 durante a jornada de preço/desconto.

| Alteração | Total líquido | Cashback | Carimbos |
| --- | ---: | ---: | ---: |
| Preço unitário R$ 20 | R$ 40 | R$ 4 | 4 |
| Preço unitário R$ 30 | R$ 60 | R$ 6 | 6 |
| Preço unitário R$ 10 | R$ 20 | R$ 2 | 2 |
| Preço unitário R$ 5 | R$ 10 | R$ 1 | 1 |
| Repetir preço R$ 5 | R$ 10 | R$ 1 | 1 |
| Preço R$ 20, desconto R$ 25 | R$ 15 | R$ 1,50 | 1 |
| Preço R$ 20, desconto R$ 20 | R$ 20 | R$ 2 | 2 |
| Retirar desconto | R$ 40 | R$ 4 | 4 |

Cashback de 10% e valor de carimbo R$ 10 eram regras fictícias exclusivas desta
jornada. Não são parâmetros definidos para produção. Regras locais foram
restauradas e a campanha exclusiva foi arquivada ao final.

Em todas as reaberturas, cashback/carimbos disponíveis ficaram zerados e o
cupom suspenso. Ao refinalizar, foram recalculados pelos valores atuais e pela
regra original. Cupom preservou identidade/validade e voltou a ativo quando o
mínimo foi atendido. O histórico continuou com somente PIX R$ 40 + R$ 20;
redução, desconto e repetição não criaram novas entradas.

A confirmação de recebimentos anteriores usa a jornada de baixa em lote já
descrita acima: vendas de 07/10 e 08/10, recebidas em 09/10 no caixa ID 7,
total R$ 30, preservando caixa de origem e estoque.

No reteste pela interface, a mesma venda já paga foi reduzida de 2 para 1 unidade
(total R$ 20) e finalizada por “Confirmar Ajustes”, sem novo pagamento. O PDV
mostrou cashback R$ 2 e 2 carimbos. Depois, aumentou de 1 para 3 unidades
(total R$ 60), confirmou novamente sem pagamento e mostrou cashback R$ 6 e
6 carimbos. Os dois PIX anteriores permaneceram registrados.

O aumento após a redução revelou um bloqueio adicional de interface: o campo
`total_pago` da consulta estava limitado ao total salvo anterior de R$ 20,
embora existissem PIX R$ 40 + R$ 20. O modal mostrava R$ 40 a pagar e não
permitia confirmar. A API agora também expõe `total_recebido` sem esse limite,
preservando `total_pago` e o status para consumidores existentes. O PDV utiliza
o recebido real para comparar com o total editado. Crediário considera apenas
parcelas baixadas; pagamentos estornados/recusados/cancelados ficam excluídos.
Dinheiro considera o valor alocado, sem somar troco.

O reteste do modal atualizado exibiu total R$ 60, recebido R$ 60 e restante
zero; “Confirmar Ajustes” concluiu a venda. A redução não gerou crédito ou troco
automático sobre pagamentos históricos. Novos testes também verificam que
aumento para R$ 80 exige somente a diferença de R$ 20.

Verificações adicionais: **30 testes Python** focados em status financeiro,
finalização e resumo do cliente; **46 testes Node** de pagamento/cashback;
Ruff, ESLint, Prettier e build passaram. Imagens local de backend/frontend
foram reconstruídas; migrations permaneceram na head única `zzzm20261009a1`.
Evidências: `beneficios-venda-reduzida-local.png` e
`beneficios-venda-aumentada-local.png`, na pasta de visualizações desta conversa.

O resumo principal do PDV foi alinhado ao modal. Na repetição pela tela, a venda
foi reduzida para R$ 20 mantendo recebido R$ 60 e restante zero. Ao aumentar para
R$ 80, ambos mostraram somente R$ 20 a receber. Foi registrado um terceiro PIX
de R$ 20: banco local confirmou venda finalizada em R$ 80, pagamentos R$ 40 +
R$ 20 + R$ 20 no caixa ID 7 e estoque do produto 85 em 16 unidades.

A revisão também alinhou a finalização e o resumo para excluir pagamentos
estornados, recusados e cancelados do saldo. **46 testes Python focados passaram**,
incluindo complemento após estorno, normalização dos status e compatibilidade
da alocação de crediário; Ruff passou. O teste antigo de tamanho de arquivo
continua falhando no baseline: `finalizacao.py` já tem 663 linhas não vazias no
HEAD (664 em `origin/main`) e o contrato exige menos de 560. Esse arquivo não
foi alterado nesta rodada.

Limite fora do cenário de venda já paga: a refinalização de uma venda com
parcelas de crediário ainda pendentes mantém a política anterior de considerar
o plano como alocação, enquanto o resumo considera somente baixas efetivas.
O recebimento dessas parcelas continua pelo fluxo de contas a receber, testado
na jornada de caixa. A política de renegociação do plano não foi alterada aqui.

### Reaberturas repetidas e recuperação dos benefícios

O reteste sucessivo encontrou um segundo defeito: as observações de carimbos
automáticos acumulavam motivos de estorno/reativação até exceder `VARCHAR(500)`.
A falha abortava a transação das campanhas e impedia cashback e cupom de serem
recalculados. O motor tentava acessar atributos ORM antes do rollback, deixando
eventos presos em `processing`.

O resumo de observações agora fica limitado a 500 caracteres e guarda as ações
recentes; os motivos e as contagens integrais permanecem na auditoria de cada
sincronização. O handler de fidelidade propaga erros, e o motor faz rollback
antes de recarregar o evento por ID/tenant com trava e salvar o contador e estado
de tentativa. Eventos já concluídos permanecem concluídos.

**35 testes passaram, sem skips**, incluindo 11 novas instâncias de regressão:
limites Unicode, 25 ciclos de reabertura com 51 registros de auditoria, mudança
da regra atual preservando o snapshot original, falha SQL real com rollback de
carimbos/auditoria/log, recuperação sem duplicação, limite de tentativas,
isolamento entre tenants e commit confirmado com resposta perdida. Ruff e
revisão independente passaram; PostgreSQL temporário da porta 15440 foi removido.

Após reconstruir somente o backend local, os eventos fictícios 103 a 106 da
venda 28 foram reprocessados com guardas de staging, banco/tenant, cliente,
número da venda e marcador exclusivo. Todos ficaram `done`: cashback R$ 8,
oito carimbos e observação máxima de 469 caracteres, sem duplicar concessões.
Eventos de produção não foram consultados ou reprocessados nesta rodada.

Novo aumento pela tela para cinco unidades, total R$ 100, exigiu somente PIX
R$ 20. Banco confirmou quatro pagamentos R$ 40 + R$ 20 + R$ 20 + R$ 20 no
caixa ID 7, estoque 15, cashback R$ 10, dez carimbos brutos e eventos 107/108
concluídos sem retry. Pela configuração fictícia, os dez carimbos completam um
ciclo e são convertidos em cupom, deixando zero carimbos disponíveis.

### Saldo atualizado automaticamente no PDV

Foi corrigida uma corrida na consulta da interface: após finalizar, o PDV
buscava o saldo antes de as campanhas terminarem e mantinha o zero da reabertura.
A API agora informa eventos de compra pendentes por tenant/cliente antes de
calcular o saldo. O PDV mostra “Atualizando benefícios…” e acompanha a fila até
exibir cashback, carimbos e cupons finais. Consultas são limitadas a 40 tentativas
com intervalo de 1,5 s; troca de cliente/desmontagem cancela consulta e timer,
respostas antigas são ignoradas e erros não substituem o saldo por zero.

Aceite final pela tela, sem recarregar a página após os ajustes:

- Redução de cinco para quatro unidades, total R$ 80, mantendo R$ 100 já
  recebidos: “Confirmar Ajustes” não criou pagamento; apareceu cashback R$ 8,
  oito carimbos e somente o cupom de recompra válido.
- Aumento para seis unidades, total R$ 120: resumo e modal pediram apenas
  R$ 20. Após o PIX, a tela exibiu automaticamente cashback R$ 12, dois carimbos
  disponíveis e cupom de fidelidade R$ 20 pelos dez carimbos convertidos.
- Banco confirmou cinco pagamentos R$ 40 + quatro de R$ 20 no caixa ID 7,
  estoque 14, cashback R$ 12, doze carimbos brutos, observação máxima de 472
  caracteres e eventos 111/112 concluídos com zero retries.

Verificação conjunta final: **54 testes Python** de pagamentos/resumos/consulta
da fila e **52 testes Node** de pagamento/cashback/atualização assíncrona passaram.
Os novos casos cobrem fila por tenant/cliente, IDs JSON numéricos e textuais,
conclusão com cashback/cupons atualizados, resposta antiga, cancelamento,
limite de tentativas e erro sem saldo falso. ESLint, Prettier, Ruff, build e
`git diff --check` passaram. Backend e frontend locais reconstruídos e saudáveis.
Permanece somente a falha antiga de contrato de tamanho descrita acima.

Evidências finais: `beneficios-reabertura-reducao-local.png` e
`beneficios-reabertura-pagamento-local.png` na pasta de visualizações desta
conversa. Tudo permanece na branch local; não houve push ou deploy. As 184
alterações preexistentes no checkout original permaneceram intactas.

## Recuperação do Docker local

O Docker Desktop falhava ao renomear o socket antigo do Secrets Engine.
A pasta `%LOCALAPPDATA%/docker-secrets-engine` foi preservada como
`docker-secrets-engine.preservado-20261009-102730`, e uma pasta vazia foi criada
para o Docker iniciar. O Engine voltou a responder e os volumes existentes
foram reutilizados. Nenhum reset de fábrica ou exclusão de volumes foi feito.

A identidade fictícia “CorePet Homologacao Local” estava com trial expirado.
O trial foi renovado somente nesse tenant do banco local, com validação do
ambiente staging e da identidade, para permitir as jornadas de aceite.
