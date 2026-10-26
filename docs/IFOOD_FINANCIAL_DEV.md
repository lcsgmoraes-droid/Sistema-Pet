# iFood Financial — validação em DEV

Atualização: 2026-10-24. DEV: **Financial Events V3 em homologação**, taxas por
venda, CMV histórico ERP por ponte canônica ou vínculo confirmado, títulos de
repasse e arquivo de conciliação On-demand.
Esta documentação registra a implementação em DEV; não declara homologação
Financial concluída nem disponibilidade financeira em produção.

## Escopo desta entrega

- Consultar os lançamentos financeiros de homologação da loja vinculada ao tenant.
- Preservar a evidência técnica permitida, os sinais monetários e o impacto no repasse.
- Consultar uma janela completa e registrar revisões sem acumular a mesma carga duas vezes.
- Exibir taxas observadas e valores ainda não classificados, mantendo pendências visíveis.
- Informar receita, CMV, tributos e outros custos **do pedido inteiro**, com fonte e histórico.
- Manter a previsão por contrato separada das cobranças observadas por pedido.
- Usar a ponte exata entre pedido e venda criada pelo piloto do PDV ou um vínculo
  manual explicitamente confirmado, sem associar por valor, data ou cliente.
- Mostrar cada cobrança conhecida com nome, sinal, valor e origem, mantendo
  pendente somente o componente ou a conferência que ainda faltar.
- Reaplicar a revisão Financial ativa nas leituras da venda e dos relatórios,
  preservando o CMV original e sem repetir a operação da venda.
- Guardar versões dos títulos de Settlements e do arquivo mensal Reconciliation.
- Conferir os valores do provedor por identificação documentada, mantendo as
  diferenças e as relações ainda não comprovadas como pendências.

Não há publicação de anúncios nesta jornada. Ela também não cria venda no PDV,
recebível, recebimento, movimento de caixa, baixa de estoque ou conciliação bancária.
Pedidos importados pelo piloto possuem associação canônica em `IfoodPdvBridge`.
Essa ponte exata já pode fornecer o vínculo para taxas e CMV; não exige criar uma
confirmação humana fictícia. Para vendas sem ponte, continua disponível o vínculo
manual explícito em `IfoodFinancialSaleLink`. Ambas as leituras respeitam empresa,
loja e modo de homologação; conflito entre associações gera pendência.

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
5. Para usar o custo original ERP, siga **Vincular a venda ERP** abaixo. Selecione
   **Informar custos desta venda** e preencha os totais conhecidos do pedido, quando
   conhecidos. Registre a fonte e a justificativa. Salvar cria uma versão local
   auditável; não altera o iFood nem os custos dos produtos.
6. Para simular vendas futuras, use as taxas e a referência de contrato nas regras
   da loja/calculadora. Essa previsão é distinta dos eventos financeiros recebidos;
   a leitura Financial não modifica automaticamente a regra contratual.

Os rótulos finais devem ser conferidos junto da validação visual da versão DEV.
Não converter este documento em uma promessa de acesso em produção antes do aceite.

### Vincular a venda ERP e usar o CMV histórico

1. Abra **Conferir venda** no pedido correto. Se ele veio do piloto do PDV, confira
   o vínculo identificado como ponte do PDV e o CMV original disponível. A leitura
   valida o estado finalizado, a baixa e o produto, quantidade e preço exatos da ponte.
   Nesse caso, não é necessário confirmar outro vínculo manual.
2. Para um pedido sem ponte, no bloco de custos históricos procure pelo **Número
   ou ID da venda ERP**. A busca lista candidatos e não escolhe uma venda.
3. Confira o número no ERP. A venda precisa pertencer à mesma empresa e ao canal
   `ifood`, estar finalizada e não ter cancelamento ou devolução. Todos os itens
   precisam ter comprovante original de baixa compatível com seus IDs e quantidades.
4. Selecione a venda encontrada, informe **Fonte e justificativa do vínculo** e marque
   **Conferi que o pedido e a venda ERP correspondem à mesma venda**. Só então use
   **Confirmar vínculo com venda ERP**. Essa ação grava uma associação local auditada;
   não cria nem finaliza venda, não baixa estoque e não envia anúncio.
5. Confira o CMV total e os comprovantes de cada linha. O custo exibido por item é o
   **total daquela linha**, com a quantidade já considerada. O custo atual do produto
   e o snapshot reprocessável de rentabilidade não são usados como substitutos.
6. Se o CMV manual estiver **Não informado**, a contribuição usa o CMV histórico
   comprovado. Um CMV manual explicitamente informado, inclusive zero, tem prioridade
   e permanece identificado como manual. Alterar essa escolha cria uma nova versão
   dos custos informados; o histórico e os comprovantes originais são preservados.

O vínculo não é reatribuído silenciosamente e uma mesma venda não prova dois pedidos.
O manifesto do vínculo manual permite detectar inclusão, remoção ou alteração de
itens e de suas provas depois da confirmação. A ponte usa sua própria evidência e
o conjunto exato de itens, sem fabricar um manifesto de confirmação humana.
Inconsistência, cancelamento ou devolução deixa
o custo automático e a contribuição pendentes de conferência, mesmo havendo um CMV
manual. Vendas antigas sem comprovante original permanecem pendentes; não completar
essas provas com o custo atual. A confirmação inicial não recupera itens que já
tenham sido removidos antes dela: o operador precisa conferir a venda correspondente.

As provas originais exigem versão, origem de baixa, IDs da empresa/venda/item/produto,
quantidade e valor compatíveis. O horário histórico sem offset emitido pelo writer
do ERP é interpretado como Brasília; o JSON original não é reescrito. Datas inválidas
ou provas adulteradas continuam recusadas. O custo atual do cadastro não substitui
o custo original da saída.

### Taxas por venda e atualização dos relatórios

A leitura local apresenta **Comissão iFood** (`ORDER_COMMISSION`) e **Taxa de
pagamento iFood** (`PAYMENT_TRANSACTION_FEE`) separadamente. Cada linha conserva
valor com sinal, fonte, revisão e, quando recebidos, base e percentual. Comissão
conhecida permanece visível enquanto a taxa de pagamento está pendente, e vice-versa.
Zero só é conhecido quando há lançamento explícito de zero; ausência não vira zero.

Frete cobrado do consumidor e serviço exclusivo do iFood no checkout são mostrados
separados das despesas da loja. Uma entrega operada pelo iFood exige identificar
sua cobrança de logística no extrato: não usar o frete do cliente como esse custo.
Tipos sem classificação confirmada preservam descrição e valor e continuam
pendentes, assim como ajustes, lançamentos sem pedido, cancelamentos, conflitos de
vínculo ou lançamentos em mais de uma janela ativa. Uma previsão contratual ou uma
taxa avulsa não elimina essas pendências.

As consultas GET do ERP resolvem a revisão ativa dos eventos locais, inclusive
quando a rentabilidade-base da venda já está em cache. A chegada tardia completa
os componentes que puderem ser comprovados; revisão substitui o valor anterior,
sem somá-lo novamente. A sobreposição Financial é aplicada apenas à apresentação:
não regrava o snapshot-base, não refaz CMV, reserva, baixa, pagamento, recebível ou
caixa. Remover a evidência válida devolve o componente à pendência.

As telas conectadas releem o ERP a cada 30 segundos enquanto visíveis, ao voltar à
aba e após uma importação local concluída. Isso não consulta o iFood por GET nem
repete a importação do pedido. Valores conhecidos aparecem mesmo com outras
parcelas pendentes; lucro e margem continuam desconhecidos até haver evidência
suportada e custos necessários completos. A confirmação bancária do repasse é
outra conferência e não é exigida para mostrar uma despesa já comprovada.

Massa de fonte `synthetic` só pode ser exibida com
`IFOOD_FINANCIAL_SHOW_SYNTHETIC=true`, desabilitado por padrão e restrito a DEV/teste.
Ela aparece como **Simulação Financial em DEV**. Mesmo com comissão e pagamento
simulados completos, não libera lucro ou margem real nem comprova cobrança oficial.

### Repasses e arquivo de conciliação

1. No bloco **Repasses**, escolha o período e a base da consulta: **Apuração** ou
   **Data prevista de pagamento**. A janela local aceita de 1 a 90 dias. Use
   **Consultar repasses no iFood** somente com leitura externa habilitada em DEV.
2. Abra **Conferir repasse** e confira tipo, situação no iFood, valor com sinal,
   apuração e previsão de pagamento. Repasse, boleto e retenção são apresentados
   por tipo; não somar esses títulos como se todos fossem receita ou crédito bancário.
3. Informe separadamente a **Competência da conciliação (AAAA-MM)** e use
   **Consultar arquivo de conciliação**. A competência do arquivo não é o período
   do pedido nem a data de pagamento. A preparação assíncrona mantém o request ID
   original e acompanha o estado sem criar uma nova solicitação a cada clique.
4. Após a importação completa, confira títulos pendentes, divergentes e valores
   conferidos entre as fontes do provedor. Conferir o provedor não marca recebimento
   bancário, recebível, caixa ou contabilidade como conciliados.

A conciliação do título usa somente o `titulo` legado quando o arquivo o fornece.
O campo `id_saldo` substitui uma coluna descontinuada, mas não é o ID de título.
Sem relação documentada entre saldo e título, o saldo continua separado e pendente,
mesmo que datas ou valores coincidam. Não inventar esse vínculo. A soma do arquivo
considera `valor` apenas nas linhas com impacto no repasse, com seus sinais; o
`valor_transacao` repetido não é somado em cada linha.

Para uma conferência completa, são necessários o mesmo título, totais consistentes,
arquivo fechado, competências que cubram a apuração e eventos da janela exata. Todos
os eventos do snapshot entram na soma; subperíodos, datas incompatíveis, arquivos
incompletos ou diferença de centavos impedem marcar como conferido. A evidência
sintética nunca comprova título de fonte oficial.

Consultar o estado local ou abrir a tela não chama o iFood. O acompanhamento externo
respeita o intervalo persistido no backend, de 5 segundos até 5 minutos; falhas mantêm
a evidência anterior e também gravam intervalo de nova tentativa. Após 429, o mínimo
é 60 segundos. Arquivo importado usa cache, sem novo download automático. Conflito
409 sem request ID conhecido e erro terminal ficam pendentes de intervenção; não
há tentativa de inventar ID nem um ciclo de novas solicitações. O endereço assinado
do arquivo não é persistido, exibido ou enviado aos logs; o download usa somente
o host de homologação verificado, com limites de tamanho e expansão.

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
| GET | `/merchants/{merchantId}/financial-events` | Cliente e importação por janela completa implementados em homologação. |
| GET | `/merchants/{merchantId}/sales` | Caminho e schema consultados; implementação e semântica de faturamento pendentes. |
| GET | `/merchants/{merchantId}/settlements` | Cliente, snapshots por janela e conferência do provedor implementados em DEV. |
| GET | `/merchants/{merchantId}/anticipations` | Caminho confirmado; integração pendente. |
| POST | `/merchants/{merchantId}/reconciliation/on-demand` | Solicitação persistida por empresa/loja/competência em DEV. |
| GET | `/merchants/{merchantId}/reconciliation/on-demand/{requestId}` | Acompanhamento com backoff/cache, download limitado e parser CSV/gzip em DEV. |

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
- Vínculo de venda é único por empresa/loja/modo/pedido e por empresa/modo/venda,
  com FK composta por empresa e venda. Ator, justificativa e manifesto ficam
  preservados. A leitura histórica usa lotes de até 1000 pedidos, até 10000 por
  relatório, evitando uma consulta ERP para cada pedido.
- Repasses de janelas sobrepostas são evidências independentes: não há total
  acumulado entre elas. Atualizar a mesma janela preserva suas revisões.

### Consulta automática limitada ao piloto DEV

O worker usa o scheduler e o processo líder existentes. É opt-in:
`IFOOD_FINANCIAL_POLLING_ENABLED=false` e
`IFOOD_FINANCIAL_READ_ENABLED=false` são os padrões. Para operar, exige também
credenciais de teste, guardas DEV do piloto e allowlist exata de empresa, loja,
pedido técnico e SKU `018631.1`, com ponte finalizada e baixa comprovada. Não é
um sincronizador geral da loja e não habilita catálogo ou operações de pedidos.

A consulta reutiliza uma janela exata já existente e compatível; na ausência
dela, usa a competência mensal completa do pedido. Mantém a mesma janela nas
revisões para evitar sobreposição crescente. O limite é 33 dias inclusivos;
o pedido precisa estar entre hoje e os 32 dias anteriores. Outras competências,
ajustes tardios fora desse alcance ou janelas conflitantes ficam pendentes de
consulta e conferência próprias, sem serem declarados conciliados pelo worker.

O intervalo mínimo é 15 minutos. Há exclusão entre execuções, backoff de falhas
de até seis horas e preservação da evidência anterior em erro. Resposta idêntica
não cria nova revisão; uma carga completa diferente pode criar a revisão ativa.
O worker não faz ACK, Picking, publicação, recebimento, pagamento, caixa ou estoque.
Uma leitura GET de relatório continua sem acesso ao provedor.

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

Na etapa de 2026-10-23, as credenciais do aplicativo **Teste (C)** foram usadas em
uma consulta controlada ao Financial oficial com o cabeçalho de homologação. Nenhuma credencial de produção foi
copiada para DEV. Naquela etapa, o backend isolado estava sem credenciais e com
a leitura externa desabilitada. A ligação de 2026-10-24 mantém as flags desligadas
por padrão; uma janela assistida precisa configurar explicitamente o escopo de testes.

### Resposta oficial de homologação observada

Em 2026-10-23, a autenticação do aplicativo de teste e a consulta retornaram 28 eventos.
O provedor entregou uma massa fixa de **01 a 03/08/2025**, com recebedor próprio,
mesmo quando a requisição usava a loja de teste acessível ao aplicativo. A validação
normal recusou associar esses lançamentos à loja solicitada. Não foi criada exceção
para aceitar eventos de outra loja ou trocar as datas do provedor.

A resposta foi sanitizada e importada localmente na empresa **DEV iFood Homologacao
Oficial**, com a identidade e o período do próprio conjunto de homologação. A fonte
permanece `ifood_financial_events`, modo `homologation`; essa importação é uma captura
controlada da resposta oficial, não uma sincronização da loja real pelo botão da tela.
Os três lançamentos sem pedido e os tipos ainda não classificados permanecem visíveis
e impedem a contribuição de parecer concluída. A massa sintética da outra empresa
DEV continua separada.

A resposta também confirmou nomes humanos de lançamento e o gatilho
`ORDER_CONCLUDED`. O parser preserva o nome do lançamento ainda não classificado,
mantém a descrição restrita aos códigos permitidos e não copia documentos do
recebedor. A compatibilidade de enum não elimina as pendências de conciliação.

Esses testes validam o cliente e a importação de homologação. A consulta das cobranças
efetivas do Atacadão ainda exige o módulo Financial no aplicativo de produção,
homologação própria e autorização correspondente da loja; não está liberada por esta
entrega.

Uma consulta controlada adicional ao GET do job On-demand do aplicativo **Teste (C)**
retornou HTTP 200 com estado `error`, com loja, competência e request ID conferidos.
Não houve download nem validação ao vivo de host de arquivo nessa tentativa. Esse
resultado é erro terminal do job, não arquivo vazio, saldo zero ou ciclo completo
de conciliação homologado. A evidência técnica sanitizada permanece fora do Git;
nenhuma URL privada, resposta bruta protegida ou credencial foi copiada para este guia.

### Diagnóstico da geração sem lançamentos (2026-10-23)

A consulta original foi aceita com HTTP 202; uma nova leitura do mesmo request ID
confirmou HTTP 200, `status: error` e a causa documentada de ausência de lançamentos
para a loja e competência solicitadas (08/2025). A identidade da loja de testes é
diferente do recebedor da massa fixa de 28 Financial Events. Esses eventos não
comprovam que existam lançamentos na loja que solicitou o arquivo. Settlements
também retornou sem títulos para 09/2026 e 01–22/10/2026. Não foram criadas novas
solicitações para contornar o erro nem modificados IDs, datas ou regras de escopo.

A [FAQ oficial, questão sobre pedidos de teste](https://developer.ifood.com.br/pt-BR/support/faq/#concilia%C3%A7%C3%A3o---%C3%A9-poss%C3%ADvel-testar-a-api-de-financial-com-pedidos-de-teste)
informa que esse uso do Financial ainda não é suportado. Isso não equivale a
afirmar que toda massa estática inexiste: a homologação usa exemplos, mas as fontes
consultadas não fornecem uma competência/loja específica com CSV atual baixável.
O único endereço do exemplo `processed` na Reference foi assinado em 07/08/2025
por 86400 segundos e está vencido; ele não foi alterado nem tratado como arquivo válido.

O cliente agora reconhece apenas as mensagens exatas documentadas de falta de
lançamentos e devolve `error_code: no_financial_entries`. Textos desconhecidos
ficam como `provider_job_error`; HTTP 429 e demais falhas de consulta têm códigos
locais separados e mantêm o backoff. O motivo apresentado e persistido usa texto
estático em português, sem ecoar mensagens livres, IDs, URLs privadas ou dados
pessoais do provedor. Erros antigos sem causa preservada recebem explicação
genérica; não se inventa uma razão retroativa.

A interface mostra o motivo, informa que o acompanhamento automático terminou e
preserva os repasses, custos e contribuições anteriores. A falha continua sem
arquivo importado e não comprova saldo zero nem recebimento no banco.

Um extrato obtido no Portal do Parceiro é uma origem distinta da geração On-demand
da API. A validação de um arquivo do Portal deve manter o original, o hash, a loja,
a cobertura declarada e a origem explícita; não comprova um job `processed` nem
autoriza misturar os valores com a massa de homologação de outra loja.

### Validação controlada de um extrato oficial do Portal

Foi obtido, pela interface autenticada do Portal, um extrato V2 em CSV. A Central
de Downloads declarou cobertura de 07 a 13/09/2026, embora o filtro de exportação
tenha sido preparado para setembro. A conferência usou somente a cobertura
declarada no relatório disponível, sem ampliar sua abrangência por suposição.
O navegador salvou o download com nome UUID, e não com o nome descritivo exibido
no Portal. As duas cópias geradas pelos cliques foram identificadas por metadados
recentes e tinham o mesmo SHA256; o original foi preservado em pasta protegida,
fora do repositório. Não foi necessário acessar históricos, caches ou banco do
navegador para encontrar o arquivo.

O arquivo usa vírgula, UTF-8, 38 colunas e nomes como `merchant_id`,
`data_do_faturamento` e `valor_total_do_repasse`. Isso difere do CSV V3 do
On-demand, que usa outro delimitador e contrato. A validação é feita por
`app.integrations.ifood.portal_statement.validate_portal_statement`, sem alterar
o parser V3 nem permitir a importação do Portal como se fosse um job da API.

Na execução real no container DEV isolado, todas as 15 linhas corresponderam à
loja, competência e cobertura verificadas. Os dois totais por título fecharam
com diferença zero, somando apenas as 13 linhas com impacto no repasse. As duas
linhas sem impacto permaneceram separadas. O relatório contém SHA256 dos bytes
originais, fonte `ifood_partner_portal_v2`, cobertura declarada, contagens e
totais; não inclui nomes de loja/clientes, CNPJ ou dados bancários livres.

Foram testadas, em memória e sem modificar o original, loja/competência/cobertura
incorretas, repetição de lançamento, diferença de um centavo, célula vazia acima
do limite e linha em branco com quantidade incorreta de colunas. Todas foram
recusadas ou marcadas para revisão, conforme o caso. A execução não fez chamadas
externas nem gravou em tabelas do ERP. O arquivo real e a prova detalhada continuam
protegidos e fora do Git; os testes versionados usam somente dados sintéticos.

O resultado é **consistência interna do arquivo**. Continuam pendentes o cruzamento
com Financial Events/Settlements da mesma loja e apuração, a confirmação bancária
e os custos necessários à margem. Datas de pagamento presentes no Portal não
quitam recebíveis ou caixa. O extrato não fornece `id_saldo` ou datas explícitas
de apuração Financial; a cobertura de exportação não substitui esses dados.

### Solicitação técnica ao iFood

Com autorização explícita do responsável, foi enviado o chamado **35302661** em
23/10/2026, às 22:46. O detalhe confirmou o status **Em análise** e a classificação
**Dúvidas ou Informações → Dúvida Técnica - API → Dúvida sobre API - Financial**.
O acompanhamento fica em [Minhas solicitações](https://developer.ifood.com.br/pt-BR/developer/tickets).

A solicitação pede uma loja/competência de testes com lançamentos disponíveis,
um fluxo válido de geração/download e esclarecimento da relação de `id_saldo`
com os títulos. Foram enviados somente identificadores técnicos de homologação
e o erro necessário ao diagnóstico, sem anexos, credenciais ou o extrato real.
Esse chamado técnico não inicia nem comprova a homologação Financial.

Antes de apresentar Financial como integração completa:

- Ampliar a validação oficial de homologação além da captura Financial Events já
  conferida, cobrindo paginação, atualizações, erros e os demais módulos financeiros.
- Concluir e validar Sales e Anticipation conforme os recursos exigidos na homologação.
- Validar o ciclo real completo de Settlements e On-demand com o provedor, incluindo
  erros, limites, expiração, arquivos de várias competências e diferenças reais.
  Cliente, persistência e testes locais não substituem essa validação oficial.
- Conciliar créditos/débitos e títulos; separar despesas sem pedido e diferenças
  ainda sem explicação. Não marcar movimentações como quitadas pela consulta.
- Concluir a validação da ponte canônica do PDV e do vínculo manual explícito,
  incluindo CMV original, chegada tardia, revisão e pendências por componente.
  A ligação local está implementada em DEV e não usa heurística; isso não
  substitui a evidência Financial oficial do pedido nem o aceite de produção.
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

## Validação registrada em DEV

- Antes da ampliação de CMV/repasses: 180 testes backend e 78 testes frontend
  aprovados; lint, formatação e build aprovados. Esses totais registram a etapa anterior.
- Migrações aplicadas em PostgreSQL novo. Prova de RLS com role temporária
  `NOLOGIN NOSUPERUSER NOBYPASSRLS`: nas quatro tabelas novas, leitura isolada
  por empresa, zero linhas sem contexto e inserção cruzada recusada. A FK
  tenant/snapshot também recusou associação cruzada; a transação da prova foi revertida.
- Na interface, o cenário sintético com receita 100, CMV 60, tributos 4, outros 1,
  comissão 6 e pagamento 3 resultou em contribuição 26 e 26%, com custos versão 1.
- Pagamento direto à loja ficou separado do impacto no repasse. Falhas de consulta
  e gravação preservaram os dados e os rascunhos; trocar de aba preservou a edição
  não salva das regras contratuais.
- A captura oficial de homologação foi importada em empresa DEV própria: 28 eventos,
  5 pedidos, 3 lançamentos sem pedido. Nenhuma contribuição foi inventada com custo
  desconhecido; nenhuma tabela operacional foi modificada pela importação financeira.
- O link `?aba=financeiro&inicio=2025-08-01&fim=2025-08-03` apenas abre a consulta
  local na janela oficial. A URL não concede permissão nem dispara sincronização.
- Ampliação atual: regressões de CMV histórico/manual, manifesto, escopo e chunks
  passaram junto às suites de Financial e custos originais. Os casos novos de
  repasse cobrem subperíodos, consolidação indevida, apuração fora da consulta,
  divergência de data, 429, falha de download/parser e cache do arquivo completo.
  A prova PostgreSQL citada acima cobre as quatro tabelas da etapa anterior.
- As três tabelas adicionais também passaram em PostgreSQL real no DEV isolado:
  `ifood_financial_sale_links`, `ifood_payout_snapshots` e `ifood_reconciliation_jobs`.
  Com role temporária sem superuser, login ou bypass de RLS, ENABLE/FORCE foram
  confirmados, cada empresa viu só suas linhas, não houve leitura sem contexto e
  a inserção cruzada foi recusada (`42501`). Unicidade (`23505`), modo somente
  homologação (`23514`), FK tenant/venda (`23503`) e imutabilidade de UPDATE/DELETE
  do vínculo (`P0001`) foram comprovados. Toda a prova sofreu rollback; role,
  grants e linhas temporárias removidos, contagens e sequências preservadas.
- A jornada atual também foi conferida na interface V2 do DEV isolado: dois títulos
  sintéticos conciliados no provedor (repasse 91 e boleto -7,20), com banco não
  conferido. A venda fictícia `DEV-CMV-HIST-001`, vinculada explicitamente pela tela,
  trouxe CMV histórico 48 e contribuição 20,60 / 25,75%; o CMV manual permaneceu
  nulo e sua versão foi preservada. Trata-se de fixture de teste, sem venda real
  do Atacadão e sem comprovar o ciclo oficial de repasses do iFood.
- Gate da ampliação anterior: 369 testes iFood aprovados; smoke raiz 203 aprovados / 2 ignorados,
  hardening multitenant 769 aprovados / 22 ignorados. Lint, formatação, build,
  importação do backend e auditorias de dependências backend/frontend passaram.
  O gate completo foi interrompido na auditoria mobile por
  `GHSA-86W9-CPQP-85RV` (node-forge/cadeia Expo). O `app-mobile/package-lock.json`
  é idêntico ao de `origin/main` (`36949c33f6e6bc2a9e62722cf21319bf47aaacf0`);
  nenhuma dependência mobile foi alterada nesta entrega. Portanto o gate completo
  não deve ser apresentado como aprovado nem como autorização para produção.
- Após o diagnóstico do job e o validador separado do Portal: **435 testes backend
  iFood** e **103 testes frontend iFood/produto** aprovados. Ruff, ESLint, Prettier
  e build passaram. A validação do extrato oficial no container DEV isolado e
  sete verificações negativas em memória passaram, preservando o hash original.
  Os novos testes do Portal integram os gates de CI e release. Não houve nova
  migração, importação do arquivo real no ERP ou alteração de produção.

### Ligação de taxas e CMV por venda (2026-10-24)

A implementação em DEV passou a cruzar Financial com a venda pela ponte exata do
PDV ou pelo vínculo manual explícito. Relatório de vendas, composição de resultado,
PDV/Central, dashboard, DRE, ponto de equilíbrio, rankings/IA e exportações recebem
os componentes conhecidos e suas pendências, preservando a base histórica de custos.

O pedido **oficial de testes #1420** continua sem eventos Financial próprios
recebidos do iFood. Sua venda `202610240002` (ID 2) possui CMV original de
**R$ 43,94**, reconhecido pela ponte. A posição de referência após a baixa oficial
é físico **29**, reservado **3**, disponível **26**. Ler e atualizar as taxas não
deve modificar esses valores, o pagamento externo ou o caixa.

O ensaio local dessa ligação usou temporariamente fonte **`synthetic`**, rotulada
como simulação DEV: comissão de **R$ 6,50**, taxa de pagamento explícita de
**R$ 0,00** e uma revisão de comissão para **R$ 7,50**, que substitui a anterior.
Serve para conferir chegada, revisão e atualização das telas; não são cobranças
reais do pedido #1420. As telas atualizaram sem recarga, preservando seleção e
expansão da venda; o PDV também releu somente a apresentação financeira. As três
revisões e seus cinco eventos sintéticos foram removidos e a configuração privada
foi restaurada. Comissão e pagamento voltaram automaticamente à pendência real.
Os dados operacionais dos dois tenants e os hashes das 12 tabelas financeiras de
controle ficaram idênticos ao início. CMV, posição 29/3/26, lotes e caixa foram
preservados. Leitura externa, polling e exibição sintética terminaram desligados.
Nenhuma consulta ao provedor, anúncio ou alteração de produção ocorreu no ensaio.

Na fonte `cbd97462f`, o `FLUXO_UNICO.bat release-check` completo passou com Git
limpo: 718 testes backend iFood, 135 de relatórios/consumidores, 318 frontend
iFood/produto, smoke raiz 203 aprovados/2 ignorados e hardening multitenant 769
aprovados/22 ignorados. Lint, formatação, build, auditorias de dependências e 104
testes mobile passaram. Os 32 cenários PostgreSQL dedicados também passaram em
execução separada. O CI remoto do commit final permanece registrado no PR #1561;
esse aceite local não conclui a homologação oficial Financial nem autoriza produção.

### Preparação para publicação do código (2026-10-23)

Após a autorização do responsável para deploy, foi identificado que o bloqueio
mobile acima vinha da ausência de `app-mobile/node_modules` neste worktree. A
correção de node-forge e sua verificação por hash já estavam versionadas. A
instalação canônica com `npm ci` executou o `postinstall`, sem alterar o lockfile,
Expo, runtime ou binários. O backport foi comprovado, os seis testes específicos
passaram e a auditoria mobile aprovou a instalação.

O `FLUXO_UNICO.bat release-check` completo passou após essa preparação, incluindo
104 testes mobile. O contrato OpenAPI também passou a documentar os conflitos
409 e os demais erros comuns em todas as dez operações Financial; o comportamento
das consultas e seus bloqueios de ambiente foram preservados.

Publicar este código não habilita Financial real. A leitura continua restrita a
DEV/homologação e depende da validação e permissão do iFood antes de uma entrega
operacional em produção. Nenhuma massa sintética ou arquivo real de teste deve
ser transportado ao banco de produção durante o deploy.
