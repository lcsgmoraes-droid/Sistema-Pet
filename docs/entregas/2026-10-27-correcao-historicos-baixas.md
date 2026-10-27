# Correção dos históricos de compras e baixas

## 1. Identificação e estado

Correção solicitada por Lucas em 27/10/2026, após novos prints dos históricos do
PDV e do financeiro. Reabre o aceite dos itens **08 e 13** do
[checklist operacional](../TAREFAS_MELHORIAS_OPERACIONAIS_2026-10-26.md).

**Implementação e aceites HTTP/UI em DEV aprovados; gate, CI e publicação ainda
pendentes.** Os registros das entregas anteriores permanecem como histórico.
Esta correção não refaz baixas, não funde pessoas e não altera o acompanhamento
separado do celular da Michele.

## 2. Problemas relatados

- Dois ícones de fechar na mesma ação do histórico do PDV.
- Data e observação da baixa ausentes nesse histórico, inclusive na baixa em lote.
- Detalhes financeiros apresentam IDs como moeda, datas ISO cruas e informação
  redundante de "registrado em".
- Status financeiros pouco claros na leitura dos movimentos.

Os prints são evidência do relato do usuário. A revisão de código abaixo registra
o diagnóstico inicial; a implementação e os aceites DEV estão discriminados em
seguida, sem equivaler à publicação.

## 3. Critérios de aceite

O botão de fechar no cabeçalho do histórico do PDV deve ter um único ícone,
conservando os caminhos de fechamento e a venda em andamento. Abrir, expandir, paginar,
filtrar, tentar novamente e fechar devem continuar funcionando.

Cada recebimento deve apresentar forma, valor, data da baixa e observação da
operação correspondente. Conferir baixa em lote, recebimento parcial e, quando
existente na massa escolhida, estorno. A observação da venda é outro dado e não
substitui a observação da baixa. Não duplicar movimentos ou valores ao enriquecer
as respostas.

As duas apresentações financeiras devem usar campos e tipos explícitos. IDs de
conta, venda, caixa ou banco são referências técnicas, não valores em reais.
Somente quantias monetárias recebem o formato brasileiro de moeda. Exibir
códigos públicos de pessoas/produtos quando disponíveis; não usar IDs como código.

Datas devem ser legíveis em português e manter o dia de negócio. Datas sem hora
não podem mudar de dia por conversão UTC. Diferenciar data da baixa de horário
técnico de criação; omitir o segundo quando for redundante para a operação.
Status e filtros devem refletir o tipo do movimento e o saldo efetivo, com
distinção entre venda finalizada e recebimento confirmado quando aplicável.

## 4. Diagnóstico inicial por leitura de código

O botão de cabeçalho de `HistoricoCliente.jsx` combina `BotaoCancelar` com um
filho `X`, enquanto o componente já oferece seu ícone. O resumo de pagamentos de
`clientes/financeiro_routes.py` apresenta forma e valor; os detalhes do PDV também
consultam `/vendas/{id}/pagamentos`. Data/observação da baixa precisam atravessar
esses contratos e chegar à apresentação.

A baixa em lote normaliza a observação da requisição, preserva-a em
`VendaBaixaLote` e grava `Recebimento.observacoes` com o prefixo da operação e o
texto informado. A data de negócio está em `Recebimento.data_recebimento`; o lote
também guarda seu instante. `created_at` é registro técnico e não deve substituir
a data da baixa.

`ClienteFinanceiroView.jsx` e `HistoricoVendasClienteTab.jsx` percorrem detalhes
genericamente e formatam qualquer número como moeda. Isso explica IDs com
prefixo monetário e strings de datas sem tratamento específico. A correção deve
usar uma apresentação com tipos e rótulos definidos.

## 5. Implementação e preservação

A rota paginada `GET /vendas/{id}/recebimentos-historico?page=1&per_page=20`
retorna recibos e estornos sem repetir seus espelhos em pagamentos. O vínculo
explícito registrado no manifesto do lote recupera a observação original; não se
associam movimentos por semelhança de texto, valor ou data. O histórico financeiro
reutiliza essa projeção e separa status de pagamento do estado operacional da
venda.

O PDV apresenta os recebimentos em um painel próprio, com data da baixa, forma,
valor, situação, origem e observação. O botão de fechar do cabeçalho usa somente
o ícone do componente V2. As duas apresentações financeiras compartilham os
formatadores de campo, data e status e o componente de detalhes, evitando a
conversão de toda referência numérica em moeda. A aba de consulta de vendas usa
os filtros V2 e conserva proteção contra respostas antigas e opção de tentar
novamente.

Frentes: histórico do PDV; apresentação financeira; projeção de pagamentos e
recebimentos no backend. Esta ficha e o checklist registram o andamento e o
aceite, sem substituir os contratos de cada frente.

Preservar permissões, isolamento entre empresas, paginação, formas de pagamento,
valores, parcelas, estornos e vínculos de auditoria. O título de Osvaldo que já
foi conferido como recebido não deve ser baixado novamente para testar a tela.
Não inferir nova divergência de saldo apenas pela ambiguidade de um rótulo.

## 6. Validação em DEV

O inventário usou a identidade QA DEV disponível, com renovação de sessão
autorizada, sem expor credenciais. A massa fictícia existente já atendia ao caso:
pessoa de código **10035**, lote **13**, duas vendas e dois recebimentos. Não foi
criada pessoa, venda ou movimentação financeira. Scripts, capturas e respostas
sanitizadas ficam em
`runtime/correcao-historicos-baixas-20261027/`, ignorado pelo Git.

Após reiniciar o backend DEV para carregar a rota nova, o aceite HTTP confirmou
um recibo por venda, os mesmos dois movimentos no financeiro, observação original
integral, data de negócio **26-10-2026**, forma e valores preservados. Os estados
de pagamento `pago` e operacional `finalizada` vieram separados.

Os **3/3 fluxos de navegador headless** passaram:

| Entrada                                         | Evidência conferida                                                                                                                                     |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Histórico no PDV                                | Um SVG no botão superior de fechar; recibo com data, observação completa, forma e situação Recebido; cliente, produto e subtotal preservados ao fechar. |
| Financeiro principal da pessoa                  | Dois recebimentos, referências `#68`/`#129` sem moeda, data local, observação integral e ausência de ISO cru/"Registrado em".                           |
| Aba Histórico por Cliente na consulta de vendas | Mesma apresentação de detalhes e status Recebido; filtro "Pago / recebido" encontrou os dois movimentos.                                                |

IDs, valores, datas e observações dos dois recibos permaneceram iguais nos
snapshots antes/depois; contagem de pessoas **41 → 41** e nenhum POST de venda ou
financeiro durante a navegação. Capturas das três entradas foram inspecionadas.

Evidências: `aceite-http.json`, `aceite-ui.json`, `aceite-ui-clone.json`,
`pdv-historico-recibo.png`, `pdv-observacao-baixa.png`,
`financeiro-recibo-detalhes.png` e `financeiro-aba-recibo-detalhes.png`, no diretório
de runtime indicado acima. `inventario-dev.json` registra a seleção da massa.

O aceite visual usa um lote confirmado. Pagamentos parciais, estornos,
paginação com várias páginas, isolamento e falhas/retry têm regressões
automatizadas nas frentes; não foram criadas baixas extras para gerar novos
casos visuais. Os testes focados informados pelas frentes foram aprovados; a
execução integrada final e os filtros normalizados de contas ainda precisam
fechamento no gate.

Os scripts antigos de baixa são referência de contrato, não devem ser executados
sem revisão: criam vendas/recebimentos e podem conter telefones fixos agora
bloqueados pela proteção de duplicidade.

## 7. Segurança e limites

Não usar produção, SSH, dados reais ou a sessão autenticada do James neste
aceite. Não imprimir tokens, senhas ou cabeçalhos de autenticação. Consultas de
teste não autorizam corrigir saldos, lançar pagamentos ou carimbos.

Os aceites anteriores de performance, recebimento e publicação continuam
registrados. O novo aceite visual é obrigatório para os defeitos relatados;
aprovar só a presença de um campo no JSON não conclui a correção.

## 8. Publicação e reversão

Implementação e aceites DEV concluídos. Publicação pendente do gate completo e
checks do PR/commit integrado. Seguir o fluxo oficial e a autorização de produção do
projeto. Registrar SHA, data, health e evidências somente após confirmação real.

Uma reversão deve preservar todos os recebimentos, vínculos e histórico já
gravados. Não repetir baixas nem executar correções financeiras para contornar
um problema de exibição.

## 9. Estado do aceite

- [x] Contratos de data/observação/status definidos e implementados pelas frentes.
- [x] Um único ícone no botão superior de fechar do histórico no PDV.
- [x] Recebimentos completos visíveis no PDV e no financeiro.
- [x] Referências, moeda, datas e status legíveis nas apresentações financeiras.
- [x] Aceites HTTP e das três entradas de interface com massa existente em DEV.
- [x] Consolidação final dos filtros de contas e regressões focadas: 80 testes
      operacionais de frontend, 38 de histórico e um de cancelamento no backend.
- [ ] Regressões e gate completo aprovados.
- [ ] PR integrado e publicação técnica confirmada.

## 10. Decisão

**Aceites DEV aprovados; correção ainda não publicada.** Os itens 08 e 13
permanecem abertos até o fechamento das validações e da publicação. A conferência
humana do cartão da Michele no aparelho físico permanece como acompanhamento
anterior, separado desta correção.
