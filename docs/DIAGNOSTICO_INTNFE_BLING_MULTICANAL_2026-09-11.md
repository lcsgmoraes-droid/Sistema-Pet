# IntNFe e Bling — diagnóstico multicanal em homologação

Data: 11/09/2026. Escopo: emissão de documentos de produto em homologação
(`ambienteCodigo: 2`), usando notas recentes do Bling apenas como referência.
Nenhum documento foi enviado à produção e nenhum destinatário recebeu e-mail.

## Objetivo do produto

O fluxo pretendido é **marketplace → EcommerceAI → CorePet → IntNFe**. O
EcommerceAI recebe os pedidos dos canais; o CorePet passa a ser a fonte operacional
do pedido, estoque e histórico fiscal; a IntNFe transmite e acompanha o documento.
O Bling serve como referência de comparação durante a transição e deixa de ser
necessário quando o novo fluxo provar equivalência funcional e fiscal.

## Resultado executivo

Foram reproduzidos quatro cenários reais de NF-e modelo 55, um de cada origem:
Amazon, Shopee, Mercado Livre e TikTok Shop. As quatro notas foram autorizadas
pela SEFAZ em homologação, com XML e DANFE disponíveis. Quantidade de itens,
CFOP, tributação principal, descontos e totais foram conferidos nos XMLs.

O CSC ativo de homologação foi localizado na SEFAZ-SP e cadastrado na IntNFe.
Depois disso, uma NFC-e modelo 65 baseada em cupom recente do PDV foi autorizada
com cStat 100. O XML confirmou CSOSN 900, `pCredSN=1,3600`,
`vCredICMSSN=2,72`, QR Code, série 023 e total de R$ 199,90. O DANFE NFC-e também
foi baixado e conferido visualmente.

Para operações de marketplace existia um problema fiscal bloqueador. As quatro
notas de origem no Bling identificavam a operação com intermediador, mas os XMLs
gerados pela IntNFe saíram com `indIntermed=0` e sem o grupo `infIntermed`. A API
documentada naquele momento não oferecia os campos correspondentes. O reteste
feito depois da correção está registrado abaixo.

## Retestes após a atualização da IntNFe

| Correção informada | Resultado prático | Situação |
|---|---|---|
| Intermediador de marketplace | Nova NF-e Amazon autorizada com cStat 100; XML contém `indIntermed=1`, `infIntermed`, CNPJ e `idCadIntTran` corretos | **Comprovada** |
| CSOSN 900 e crédito do Simples | NFC-e modelo 65 autorizada com cStat 100; XML contém `ICMSSN900`, `pCredSN=1,3600` e `vCredICMSSN=2,72` | **Comprovada** |
| CSC da NFC-e | CSC ativo de homologação localizado na SEFAZ-SP, `PUT` da IntNFe respondeu 204 e o `GET` posterior confirmou o cadastro | **Comprovado em homologação** |
| Frete automático nos itens | A mesma venda com R$ 5,59 de frete autorizou com dinheiro; XML contém `vFrete=5.59` no item e no total | **Comprovada** |
| Descrição da NFC-e em homologação | NFC-e enviada com a descrição natural do produto autorizou; o XML trouxe automaticamente a frase exigida pela SEFAZ | **Comprovada** |
| Eventos da NF-e | CC-e e cancelamento autorizados com código 135; consulta de eventos trouxe protocolos e a nota passou para Cancelada | **Comprovada** |
| Inutilização | Faixa de teste homologada com código 102, protocolo e presença na listagem | **Comprovada** |
| Cancelamento da NFC-e | POST respondeu 202, mas a NFC-e continuou Autorizada nas consultas; a rota equivalente de eventos retornou 404 | **Não confirmado** |

A tentativa anterior no modelo 55 recebeu cStat 600 porque não reproduzia o
documento de origem: o cupom do Bling é modelo 65. O novo teste no modelo correto
encerrou essa dúvida. O segredo do CSC não foi incluído neste documento nem no Git.

## Testes executados

Cada cenário usou uma série isolada, chave de idempotência própria e apenas uma
requisição de emissão. Após a autorização, o XML foi baixado e conferido.

| Origem | Cenário reproduzido | Resultado na IntNFe | Conferência principal |
|---|---|---|---|
| Amazon | Venda interna, um item, total de R$ 83,90 | Autorizada | CFOP 5405, CSOSN 500, PIS/COFINS 49 e total corretos |
| Shopee | Um item com quantidade 2 e desconto de R$ 121,62, total de R$ 118,38 | Autorizada | Quantidade, desconto, CSOSN 500 e total corretos |
| Mercado Livre | Venda interestadual, um item, total de R$ 37,57 | Autorizada | CFOP 6404, destino interestadual e total corretos |
| TikTok Shop | Três itens e desconto total de R$ 9,00, total de R$ 50,70 | Autorizada | Três linhas, descontos e total corretos |

Nos quatro XMLs, o meio de pagamento ficou como dinheiro porque essa também era
a informação encontrada nas notas consultadas no Bling. Esse dado provavelmente
não representa a liquidação real dos marketplaces e precisa ser validado com a
contabilidade antes de virar regra do CorePet.

### Reteste de frete e Pix

Uma quinta NF-e reproduziu uma venda recente do TikTok com um item, desconto de
R$ 6,00, frete de R$ 5,59, total de R$ 38,49 e pagamento Pix. Antes da correção,
a SEFAZ a rejeitou com código 535 porque o frete do total não aparecia nos itens.

No reteste, a IntNFe passou a ratear automaticamente `frete.valor`. Com pagamento
em dinheiro, a nota foi autorizada com cStat 100; o XML confirmou `vFrete=5.59`
no item e no total, além de `vNF=38.49`. Portanto, o problema do frete está
resolvido.

Com `formaPagamento: "17"`, que a documentação identifica como PIX, a mesma nota
foi rejeitada com cStat 391: a SEFAZ entendeu a forma como cartão e exigiu dados
da operação. Alterar somente a forma para dinheiro fez o cenário autorizar. O
mapeamento ou a serialização do código 17 precisa ser corrigido pela IntNFe.

## Estados e tributação

Além do cenário já emitido para o Pará, foram examinadas notas recentes com destino
a Goiás, Ceará e Mato Grosso do Sul. Elas confirmam que a UF altera CFOP, alíquotas
interestaduais, eventual DIFAL/FCP e algumas validações estaduais. Portanto,
operações para outros estados precisam de homologação.

Emitir várias notas com o mesmo CFOP 6404 e CSOSN 500 tem ganho limitado. A próxima
amostra interestadual deve acrescentar uma diferença fiscal real: produto sem ST
com CFOP 6102/CSOSN 102, comprador contribuinte com IE, operação com DIFAL/FCP ou
outro benefício/regra validado pela contabilidade.

## Logística de marketplace e transportadora fiscal

Nas notas examinadas, o Bling separa a integração logística dos campos fiscais da
transportadora. Amazon DBA, Mercado Envios e a logística do TikTok aparecem como
serviço operacional, com objeto de postagem, rastreio e volume. Mesmo assim, razão
social, CNPJ, IE e endereço da transportadora podem permanecer vazios, e a NF-e
pode usar modalidade 9.

A IntNFe aceita modalidade, valor do frete e uma transportadora opcional. O contrato
atual não oferece objetos de postagem, rastreio, quantidade/espécie dos volumes ou
pesos. Portanto, transporte ainda não está homologado de ponta a ponta. O CorePet
precisa guardar separadamente:

- **informação fiscal:** modalidade, valor e transportadora quando ela realmente
  deve constar no XML;
- **informação operacional:** operador logístico, serviço, etiqueta, código de
  rastreio, volumes, pesos e endereço de entrega.

Não se deve inventar uma transportadora no XML a partir apenas do nome “Mercado
Envios”, “Amazon DBA” ou “Logística TikTok”. O mapeamento depende dos dados que o
marketplace/EcommerceAI efetivamente entregar e da regra fiscal aplicável.

## DANFE: validação visual

Os quatro DANFEs foram convertidos para A4 e examinados visualmente. Todos ficaram
em uma página, com cabeçalho, destinatário, itens, totais e dados adicionais
legíveis, sem sobreposição ou corte interno. Quantidades e valores acompanharam
os respectivos XMLs, inclusive nos casos com desconto e vários itens.

Ainda há conteúdo e linhas muito próximos das bordas da página. Impressoras que
não trabalham até a borda podem cortar parte da moldura. A geração deve reservar
uma margem física segura para A4 e ser validada em impressão real.

O DANFE NFC-e autorizado foi renderizado no formato de cupom e conferido
visualmente. Cabeçalho de homologação, emitente, item, total, forma de pagamento,
consumidor não identificado, chave, QR Code e protocolo estão presentes e
legíveis, sem sobreposição. Ainda falta uma impressão física em bobina de 80 mm.

## Cupom fiscal, NFC-e e Nota Fiscal Paulista

Em São Paulo, o fluxo de varejo a validar no CorePet é a NFC-e modelo 65. A partir
de 01/01/2026, ela substituiu o SAT e outros cupons de varejo no estado. Para
autorizar NFC-e é necessário credenciamento e CSC específico do ambiente; o CSC
de homologação deve ser obtido na SEFAZ. Com o ID e o token em mãos, o integrador
pode cadastrá-los em `PUT /integrador/emitentes/{tenantId}/csc`; o `GET` da mesma
rota informa apenas se existe CSC e qual é seu ID, sem devolver o segredo.

O contrato atualizado recebe `ambienteCodigo` no PUT e devolve estados separados
para homologação e produção no GET. O CSC antigo apareceu ausente após a mudança;
foi necessário recadastrar o valor protegido em homologação. Isso liberou o novo
teste, mas a política de migração dos cadastros anteriores deve ser confirmada.

A Nota Fiscal Paulista não é outro modelo de nota nem exige uma segunda emissão.
Quando o consumidor pede CPF ou CNPJ, o documento eletrônico deve identificar o
comprador; a transmissão à SEFAZ alimenta o programa. Portanto, depois de liberar
a NFC-e, precisamos testar ao menos dois cupons: um para consumidor não identificado
e outro com CPF solicitado para a Nota Fiscal Paulista.

Foram examinadas três NFC-e recentes do PDV no Bling: uma com vários itens e duas
com um item. Todas eram para consumidor não identificado, série 3, CFOP 5102,
CSOSN 900 e PIS/COFINS 49. Os pagamentos estavam registrados como dinheiro.

Quatro tentativas controladas documentaram a evolução do bloqueio até a
autorização:

| Tentativa | Resultado | Diagnóstico |
|---|---|---|
| NFC-e com `crt` numérico | HTTP 400 | O contrato exige `emitente.crt` como texto; o serializador do CorePet deve enviar `"1"`, e não `1` |
| NFC-e com `crt` em texto | HTTP 422 `OperacaoInvalida` | Emitente sem CSC de NFC-e; a requisição parou antes de validar os impostos |
| NFC-e após o CSC | cStat 373 | A SEFAZ exige a frase padrão de homologação na descrição do primeiro item; a IntNFe não a substituiu automaticamente |
| NFC-e com descrição padrão | **Autorizada, cStat 100** | XML modelo 65 confirmou CSC, QR Code, `ICMSSN900`, crédito do Simples e total |
| Reteste com descrição natural | **Autorizada, cStat 100** | A IntNFe substituiu automaticamente a descrição do primeiro item pela frase obrigatória de homologação |

Não é correto trocar o CSOSN 900 por outro código apenas para fazer o teste passar.
O contrato atualizado aceita `icms.cst=900` e mapeia `icms.aliquota` e
`icms.valor` para `pCredSN` e `vCredICMSSN`; o XML autorizado comprovou o
mapeamento. A substituição automática da descrição no construtor da IntNFe foi
confirmada no reteste.

## Pendências priorizadas

### P0 — bloqueiam o piloto correto ou a produção

| Pendência | O que falta | Responsável sugerido |
|---|---|---|
| Pagamento PIX | Corrigir o mapeamento de `formaPagamento: "17"`, documentado como PIX, mas enviado à SEFAZ como cartão e rejeitado com cStat 391 | Equipe IntNFe |
| Regra fiscal por operação | Confirmar com a contabilidade CFOP, CSOSN/CST, benefícios, DIFAL/FCP e natureza por estado/canal | Empresa/contador |
| Separação de ambientes | Manter CSC, série, numeração e credenciais explicitamente separados entre homologação e produção | CorePet/IntNFe |
| Identificação da numeração | Corrigir `GET /painel/numeracao`, que devolveu `modelo: null` em todas as séries; sem 55/65 o CorePet não pode identificar a sequência | Equipe IntNFe |
| Cancelamento da NFC-e | Processar ou expor o resultado do cancelamento aceito com HTTP 202; a nota permaneceu Autorizada e não há consulta de eventos NFC-e documentada | Equipe IntNFe |
| Migração do CSC | Confirmar se CSCs cadastrados antes da separação por ambiente serão migrados; homologação apareceu ausente e exigiu recadastro | Equipe IntNFe |

### P1 — necessários para equivalência com as notas reais

| Pendência | Evidência encontrada |
|---|---|
| GTIN/EAN comercial e tributável | O produto de referência tinha GTIN no Bling, mas o XML IntNFe saiu como `SEM GTIN`; a documentação não expõe esses campos |
| Referência do pedido | Faltam campos estruturados como `xPed` e `nItemPed`, além do vínculo interno com canal e pedido |
| Pagamento detalhado | Faltam integração do pagamento, CNPJ da instituição/adquirente, bandeira, autorização, descrição, troco e múltiplos pagamentos quando aplicáveis |
| Transporte e volumes | Faltam quantidade/espécie/marca/numeração dos volumes, pesos, rastreio e dados logísticos completos |
| Entrega ao consumidor | O contrato de presença documentado não lista o código 4, necessário para entrega em domicílio quando aplicável |
| DANFE A4 | Reservar margem de impressão e conferir em impressora física comum |
| DANFE NFC-e | Versão simples conferida em tela; faltam impressão física em 80 mm, descontos, múltiplos itens e identificação do consumidor |

### P2 — completar antes de ampliar a operação

- Tela e persistência de cancelamento, CC-e, inutilização e consulta de eventos no CorePet; os eventos de NF-e já foram comprovados diretamente na IntNFe.
- Recuperação após timeout, repetição com idempotência e reconciliação por chave.
- Contingência da NFC-e e comportamento do caixa quando a SEFAZ estiver indisponível.
- Devolução, nota complementar, nota de ajuste e referência ao documento original.
- Venda para pessoa jurídica com IE, consumidor final interestadual e cenários com
  tributação diferente de substituição tributária.
- NFS-e para serviços de banho, tosa e atendimento veterinário, em uma frente
  própria; a documentação atual da IntNFe ainda não comprova essa cobertura.
- Retenção de XML/protocolo, controle de acesso, auditoria e política de guarda.

## Dados que o CorePet precisa guardar

O CorePet deve manter um documento fiscal próprio e tratar Bling e IntNFe como
provedores. Para atender os cenários observados, o modelo precisa guardar:

1. emitente, ambiente, modelo 55/65, série, número, finalidade e indicador de
   presença;
2. canal de origem, pedido externo, CNPJ do intermediador e identificador da conta
   do vendedor no marketplace;
3. fotografia do destinatário usada na emissão, permitindo consumidor anônimo na
   NFC-e e CPF/CNPJ opcional para Nota Fiscal Paulista;
4. fotografia fiscal de cada item: descrição, SKU, GTIN, NCM, CEST, CFOP, origem,
   CSOSN/CST, bases, alíquotas, créditos e valores de tributos;
5. quantidade, unidade, preço, desconto rateado, frete, seguro, outras despesas e
   totais reconciliáveis;
6. um ou mais pagamentos fiscais, troco e dados de integração quando exigidos;
7. modalidade de frete, transportador, volumes, pesos e rastreio;
8. tentativas, chave de idempotência, corpo enviado, resposta bruta, status, chave,
   protocolo, eventos, XML autorizado e representação para impressão;
9. vínculo imutável entre venda/pedido e documento, evitando duplicar estoque,
   financeiro ou emissão ao sincronizar mais de um provedor.

## Situação atual do EcommerceAI no CorePet

A integração existente ainda não recebe pedidos de marketplace. Ela oferece o
catálogo do CorePet para leitura pelo EcommerceAI e aceita eventos com idempotência,
mas somente `integration.test` e `company.overview.snapshot` são processados. Um
evento de pedido seria armazenado com estado `unsupported`.

Para substituir o Bling, precisamos acrescentar um contrato versionado com pelo
menos estes eventos:

| Evento | Finalidade |
|---|---|
| `marketplace.order.upsert` | Criar ou atualizar o pedido pela identidade do canal e sua versão |
| `marketplace.order.cancelled` | Cancelar de modo idempotente e acionar as regras de estoque/fiscal |
| `marketplace.order.shipping.updated` | Atualizar etiqueta, serviço, rastreio e volumes sem reemitir a nota |

O pedido recebido precisa conter canal, conta do vendedor, ID e versão externos,
datas, comprador, endereço de entrega/cobrança, itens/SKUs/GTIN, valores e descontos,
pagamentos, intermediador, logística, frete e referências do marketplace. O CorePet
deve deduplicar o evento, resolver o produto, reservar estoque, criar o pedido,
montar uma fotografia fiscal, emitir pela IntNFe e devolver ao EcommerceAI o estado,
número, chave e motivo de rejeição quando aplicável.

Os dados tributários finais não devem ser aceitos cegamente do canal. O pedido traz
os fatos comerciais; o CorePet aplica a configuração fiscal revisada da empresa e
do produto antes de formar o corpo da IntNFe.

Segredos, certificados, CSC, dados pessoais e XMLs completos devem permanecer em
armazenamento protegido; não entram em logs comuns, documentos versionados ou
mensagens de diagnóstico.

## Próxima rodada de testes

1. Emitir uma NFC-e com CPF para validar a Nota Fiscal Paulista.
2. Validar impressão física do DANFE em bobina de 80 mm, depois cancelamento e
   reconsulta.
3. Corrigir o pagamento PIX e repetir a amostra rejeitada com cStat 391.
4. Confirmar o cancelamento da NFC-e e a forma de consultar seu evento.
5. Repetir o intermediador nos demais marketplaces como regressão, sem prioridade
   sobre os bloqueios ainda abertos.
6. Definir e homologar o contrato de entrada de pedidos do EcommerceAI.
7. Repetir os cenários com pagamento e logística fiéis à operação real.

## Fontes

- [Documentação da API IntNFe](https://intnfe.com.br/api/doc)
- [Portal da NFC-e da Secretaria da Fazenda de São Paulo](https://portal.fazenda.sp.gov.br/servicos/nfce/)
- [Sobre a NFC-e em São Paulo](https://portal.fazenda.sp.gov.br/servicos/nfce/Paginas/Sobre.aspx)
- [Como participar da Nota Fiscal Paulista](https://portal.fazenda.sp.gov.br/servicos/nfp/Paginas/Como-participar.aspx)
- [Nota Técnica NF-e 2020.006 — intermediador da operação](https://www.nfe.fazenda.gov.br/Portal/exibirArquivo.aspx?conteudo=A6qvFRVbPSA%3D)
