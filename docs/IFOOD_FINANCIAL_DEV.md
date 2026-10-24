# iFood Financial — validação em DEV

Data: 2026-10-23. Estágio 1: leitura de **Financial Events V3 em homologação**,
histórico de consultas e contribuição por pedido com custos informados pela loja.
Esta documentação registra a implementação inicial; não declara homologação
Financial concluída nem disponibilidade financeira em produção.

## Escopo desta entrega

- Consultar os lançamentos financeiros de homologação da loja vinculada ao tenant.
- Preservar a evidência técnica permitida, os sinais monetários e o impacto no repasse.
- Consultar uma janela completa e registrar revisões sem acumular a mesma carga duas vezes.
- Exibir taxas observadas e valores ainda não classificados, mantendo pendências visíveis.
- Informar receita, CMV, tributos e outros custos **do pedido inteiro**, com fonte e histórico.
- Manter a previsão por contrato separada das cobranças observadas por pedido.

Não há publicação de anúncios nesta jornada. Ela também não cria venda no PDV,
recebível, recebimento, movimento de caixa, baixa de estoque ou conciliação bancária.
Os custos ERP ainda não são vinculados automaticamente ao pedido financeiro.

## Como conferir pela interface

Pré-requisitos: estar no ambiente DEV, na empresa correta, com acesso aos relatórios
financeiros (`relatorios.financeiro`). Importar eventos e alterar custos exigem também
`configuracoes.editar`. A consulta externa depende da habilitação, das credenciais
protegidas do aplicativo no backend de DEV, do vínculo da loja e do acesso Financial
concedido pelo iFood. O botão informa quando a consulta não está liberada.

1. Abra **Central do iFood → Financeiro**. Confira o aviso de homologação e a empresa
   selecionada antes de interpretar qualquer valor.
2. Informe o período desejado, entre 1 e 33 dias incluindo início e fim. Uma consulta
   pode conter vários pedidos, eventos sem pedido e mais de uma página.
3. Use **Consultar eventos no iFood** somente em DEV. A consulta envia o cabeçalho de
   homologação e só registra o resultado quando todas as páginas forem obtidas e
   validadas. Falha, limite de processamento ou resposta incompleta não substituem
   a evidência completa anterior.
4. Use **Conferir venda** para abrir os detalhes de um pedido. Confira evento, valor com sinal, base de cálculo,
   percentual observado, recebedor do pagamento, impacto no repasse e previsão
   informada. Esses dados não comprovam crédito na conta bancária.
5. Selecione **Informar custos desta venda** e preencha os totais do pedido, quando
   conhecidos. Registre a fonte e a justificativa. Salvar cria uma versão local
   auditável; não altera o iFood nem os custos dos produtos.
6. Para simular vendas futuras, use as taxas e a referência de contrato nas regras
   da loja/calculadora. Essa previsão é distinta dos eventos financeiros recebidos;
   a leitura Financial não modifica automaticamente a regra contratual.

Os rótulos finais devem ser conferidos junto da validação visual da versão DEV.
Não converter este documento em uma promessa de acesso em produção antes do aceite.

### Como preencher receita e custos

| Campo | Significado nesta etapa |
| --- | --- |
| Receita da loja antes das taxas | Total devido à loja, incluindo créditos e subsídios cabíveis, já com descontos financiados pela própria loja descontados. Exclui taxas exclusivas do consumidor. Ainda não descontar as taxas da plataforma que o cálculo deduzirá. |
| CMV desta venda | Custo das mercadorias do pedido inteiro, confirmado pela loja. Não é o custo unitário de um único produto. |
| Tributos desta venda | Valor tributário do pedido informado pela loja. Não é importado automaticamente de um percentual Financial. |
| Outros custos desta venda | Custos adicionais confirmados para esse pedido. Não repetir despesas já incluídas no CMV ou nas taxas observadas. |
| Fonte e justificativa | Origem dos valores e explicação suficiente para revisão posterior. |

Receita da loja não é necessariamente o total pago pelo consumidor nem o repasse do
iFood. Recebimentos e subsídios exibidos no extrato não devem ser somados novamente à
receita manual. Não descontar a mesma promoção ou taxa duas vezes.

Desconhecido permanece nulo; zero significa confirmação explícita de que aquele custo
não se aplica. A tela usa **Contribuição com custos informados**. Dados incompletos,
eventos ainda sem classificação ou valores pendentes impedem tratar o resultado como
lucro final. Lançamentos de mensalidade ou ajustes sem pedido não devem ser rateados
automaticamente entre produtos nesta etapa.

A ausência de um evento de comissão ou de taxa de pagamento também é desconhecida,
não uma taxa zero. Um lançamento explícito de valor zero pode confirmar esse valor.
Se o mesmo pedido aparecer em mais de uma janela, a contribuição fica bloqueada até
conferir os lançamentos entre períodos; um ajuste tardio não pode ser ignorado.

## Contrato externo verificado

Fonte técnica principal: [API Reference oficial](https://developer.ifood.com.br/pt-BR/docs/references),
seção **Financial v.3.0**, consultada no navegador em 2026-10-23. O servidor selecionado
na Reference é `https://merchant-api.ifood.com.br/financial/v3.0`.

| Método | Caminho relativo ao servidor Financial V3 | Situação nesta entrega |
| --- | --- | --- |
| GET | `/merchants/{merchantId}/financial-events` | Único recurso externo implementado nesta etapa. |
| GET | `/merchants/{merchantId}/sales` | Caminho e schema consultados; implementação e semântica de faturamento pendentes. |
| GET | `/merchants/{merchantId}/settlements` | Caminho confirmado; integração e conciliação pendentes. |
| GET | `/merchants/{merchantId}/anticipations` | Caminho confirmado; integração pendente. |
| POST | `/merchants/{merchantId}/reconciliation/on-demand` | Caminho confirmado; geração e tratamento do arquivo pendentes. |
| GET | `/merchants/{merchantId}/reconciliation/on-demand/{requestId}` | Caminho confirmado; acompanhamento e arquivo pendentes. |

Não substituir esses caminhos por V2/V2.1, `financial-v3.0` ou um endpoint sem o hífen
em `financial-events`. A apresentação abreviada de um guia não basta para inventar
um endpoint HTTP diferente do publicado na Reference.

### Financial Events

Parâmetros da Reference: `merchantId` obrigatório no path; `beginDate` e `endDate`
no query em `yyyy-MM-dd`; `page` inteiro iniciando em **1**; `size` inteiro com
padrão **100**; `idSaldo` inteiro opcional para o período de apuração. A Reference
permite omitir as datas e adota o dia atual. O CorePet sempre envia a janela explícita.
O [guia Financial Events](https://developer.ifood.com.br/es-CO/docs/guides/modules/financial/api-financial-events)
orienta consultas por períodos completos de apuração e janela máxima de 33 dias.

O schema `FinancialEventsResponse` é um **objeto** com os campos obrigatórios
`page: integer`, `size: integer`, `hasNextPage: boolean`, `financialEvents: array`.
O `Example Value` da própria Reference envolve esse objeto em um array de um
elemento. O adaptador aceita somente essa variante documentada adicional e mantém
a validação da paginação. Não combinar envelopes múltiplos nem aceitar páginas
incompletas silenciosamente.

| Parte do evento | Campos e interpretação |
| --- | --- |
| Identificação técnica | `name`, `description`, `product`, `trigger`, `competence`. A Reference não fornece um ID único do lançamento. |
| Instantes | `dateTime` é o instante do evento; `reference.date` é o instante da referência. Preservá-los separadamente. |
| Apuração | `period.beginDate`, `period.endDate`. A competência e a apuração não substituem a data do pedido. |
| Referência | `reference.type`, `reference.id`. Quando o tipo é `ORDER`, o ID é do pedido; um pedido pode ter vários lançamentos. |
| Valor | `amount.value` é uma string decimal monetária com sinal. Valores são tratados em reais, sem dividir por 100 como em Virtual Bag. |
| Cobrança | `billing.baseValue`, `billing.feePercentage`, quando informados. Uma taxa observada não se torna uma condição contratual global. |
| Repasse | `hasTransferImpact` booleano; `settlement.expectedDate`, quando informada, é previsão. |
| Recebedor | `receiver.businessId`, `businessType`, `businessDocument` na Reference atual. A evidência local não conserva o documento. |
| Pagamento | `payment.method`, `brand`, `liability`, quando informados. Não são confirmação de recebimento bancário. |

Os campos internos do evento aparecem sem marca de obrigatoriedade no schema da
Reference. O CorePet adota verificações locais conservadoras para não atribuir
dados incompletos ou de outra loja. Essa escolha pode bloquear uma resposta que
exija análise; não autoriza completar dados ausentes com zero.

`businessType` é documentado como string, com exemplo `MERCHANT`; não há enum que
garanta que todos os recebedores sejam lojas. O guard local aceita a forma atual
somente com `businessType = MERCHANT` e `businessId` igual à loja vinculada; preserva
compatibilidade controlada com `receiver.merchantId` do guia anterior. Não assumir
que qualquer `businessId` seja o Merchant ID da sessão.

O valor de repasse é a soma dos lançamentos com `hasTransferImpact = true`, com
seus sinais originais. Pagamento recebido pela loja pode ter impacto falso e sua
comissão ter impacto verdadeiro. Repasse e contribuição são medidas diferentes.

### Sales: contrato conhecido, ainda não consumido

A Reference publica `beginSalesDate` e `endSalesDate` obrigatórios e `page`
iniciando em 1; não apresenta `size` como parâmetro da operação. O schema
`ListSalesResponse` é objeto com `page`, `size`, `beginSalesDate`, `endSalesDate`,
`sales`, `total`, `pageCount`; o exemplo também usa array com um envelope.

`Sale` inclui identificação, loja, valores brutos, benefícios, entrega, pagamentos,
histórico de status, eventos e `billingSummary`. Este último contém `saleBalance`
e `billingEntries[]` com `name` e `value`. Os valores monetários são strings no
schema e números nos exemplos. Antes de utilizar Sales em contribuições, validar
completude, sinais, cancelamentos e relação com os eventos; não somar as duas
fontes como se fossem cobranças independentes.

## Persistência e idempotência do CorePet

Estas são decisões locais, não garantias adicionais da API:

- Escopo por tenant, Merchant ID e modo `homologation`.
- Snapshot de uma **janela exata**, com revisão, fonte, instante, usuário e hash
  da evidência sanitizada. Só tornar a revisão atual depois da carga completa.
- Repetir a mesma carga não soma cobranças novamente. Atualização da janela
  cria uma revisão e preserva o histórico anterior.
- Preservar a posição e multiplicidade dos eventos dentro da resposta. Duas
  taxas com o mesmo conteúdo podem ser legítimas; não descartá-las pelo hash.
- Não usar o ID do pedido como chave única de lançamento. Consultas de janelas
  sobrepostas não podem produzir dupla contagem. É permitido atualizar a mesma
  janela exata ou importar uma janela sem sobreposição. Uma sobreposição diferente
  retorna 409 e pede atualizar a janela original.
- Custos manuais têm versões próprias e continuam identificados como informados
  pelo usuário; uma nova consulta externa não os converte em dados do provedor.

## Previsão por contrato

Nas regras da loja, registrar a referência e a vigência das taxas informadas.
O cálculo por produto continua sendo uma previsão com premissas da loja, separada
do extrato de cobranças por pedido. Não inferir automaticamente todo o contrato
a partir de uma taxa isolada, nem transformar dado desconhecido em custo zero.
Agendamento de contratos futuros e recuperação automática de condições contratuais
não fazem parte desta entrega.

## Liberação e pendências

O backend bloqueia esta superfície fora de DEV/homologação. A leitura externa
depende de `IFOOD_FINANCIAL_READ_ENABLED`, desabilitado por padrão (`false`), e usa obrigatoriamente
`x-request-homologation: true`. As travas de catálogo e pedidos são independentes;
não habilitá-las para executar este roteiro. Não inserir tokens ou segredos em
capturas, documentos, exemplos ou commits.

Nenhuma credencial real foi configurada em DEV durante esta implementação. A consulta
real ainda depende da configuração protegida e do acesso Financial; os testes locais
não declaram essa integração homologada nem acesso real validado.

Antes de apresentar Financial como integração completa:

- Validar as respostas reais de homologação e compará-las às fixtures de teste.
- Implementar e validar Sales, arquivo Reconciliation, acompanhamento On-demand,
  Settlements e Anticipation conforme os recursos exigidos na homologação.
- Tratar 409 de On-demand reutilizando `requestId`, além de expiração do arquivo,
  paginação, limites e falhas transitórias. Não há isso implementado no estágio 1.
- Conciliar créditos/débitos e títulos; separar despesas sem pedido e diferenças
  ainda sem explicação. Não marcar movimentações como quitadas pela consulta.
- Fechar o vínculo com venda/PDV e custos históricos do ERP em escopo próprio.
- Concluir a homologação Financial, obter a permissão correspondente e receber
  autorização específica antes de qualquer liberação em produção.

A [homologação Financial oficial](https://developer.ifood.com.br/en-US/docs/food/guides/modules/financial/homologation)
é separada dos módulos operacionais; aprovação de catálogo/pedidos não a substitui.
A [categoria Groceries](https://developer.ifood.com.br/en-US/docs/getting-started/homologation/categories)
inclui Financial entre os módulos elegíveis. O
[guia Reconciliation V3](https://developer.ifood.com.br/es-CO/docs/guides/modules/financial/api-reconciliation/)
explica os lançamentos do arquivo e o filtro de impacto; a soma de títulos não
deve repetir `valor_transacao` em cada linha de um mesmo título.

Os exemplos da documentação são evidência de contrato para testes locais, não
comprovantes de vendas da loja. Nenhuma collection Postman foi declarada como
oficial neste documento sem link verificado no portal.
