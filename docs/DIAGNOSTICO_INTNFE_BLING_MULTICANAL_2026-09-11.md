# IntNFe e Bling — diagnóstico multicanal em homologação

Data: 11/09/2026. Escopo: emissão de documentos de produto em homologação
(`ambienteCodigo: 2`), usando notas recentes do Bling apenas como referência.
Nenhum documento foi enviado à produção e nenhum destinatário recebeu e-mail.

## Resultado executivo

Foram reproduzidos quatro cenários reais de NF-e modelo 55, um de cada origem:
Amazon, Shopee, Mercado Livre e TikTok Shop. As quatro notas foram autorizadas
pela SEFAZ em homologação, com XML e DANFE disponíveis. Quantidade de itens,
CFOP, tributação principal, descontos e totais foram conferidos nos XMLs.

O teste de cupom fiscal eletrônico, a NFC-e modelo 65, ficou bloqueado antes do
envio à SEFAZ porque o emitente ainda não possui CSC de homologação cadastrado
na IntNFe. Os três cupons recentes analisados no Bling também revelaram um
segundo bloqueio: usam CSOSN 900 com crédito do Simples Nacional, enquanto a
documentação atual da IntNFe não lista o CSOSN 900 entre as situações aceitas.

Para operações de marketplace existe um problema fiscal bloqueador. As quatro
notas de origem no Bling identificavam a operação com intermediador, mas os XMLs
gerados pela IntNFe saíram com `indIntermed=0` e sem o grupo `infIntermed`. A API
documentada não oferece campos para enviar CNPJ do intermediador e o identificador
da conta do vendedor. A autorização em homologação não torna essa perda aceitável
para produção.

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

## DANFE: validação visual

Os quatro DANFEs foram convertidos para A4 e examinados visualmente. Todos ficaram
em uma página, com cabeçalho, destinatário, itens, totais e dados adicionais
legíveis, sem sobreposição ou corte interno. Quantidades e valores acompanharam
os respectivos XMLs, inclusive nos casos com desconto e vários itens.

Ainda há conteúdo e linhas muito próximos das bordas da página. Impressoras que
não trabalham até a borda podem cortar parte da moldura. A geração deve reservar
uma margem física segura para A4 e ser validada em impressão real.

## Cupom fiscal, NFC-e e Nota Fiscal Paulista

Em São Paulo, o fluxo de varejo a validar no CorePet é a NFC-e modelo 65. A partir
de 01/01/2026, ela substituiu o SAT e outros cupons de varejo no estado. Para
autorizar NFC-e é necessário credenciamento e CSC específico do ambiente; o CSC
de homologação deve ser obtido na SEFAZ e cadastrado na IntNFe pelo operador.

A Nota Fiscal Paulista não é outro modelo de nota nem exige uma segunda emissão.
Quando o consumidor pede CPF ou CNPJ, o documento eletrônico deve identificar o
comprador; a transmissão à SEFAZ alimenta o programa. Portanto, depois de liberar
a NFC-e, precisamos testar ao menos dois cupons: um para consumidor não identificado
e outro com CPF solicitado para a Nota Fiscal Paulista.

Foram examinadas três NFC-e recentes do PDV no Bling: uma com vários itens e duas
com um item. Todas eram para consumidor não identificado, série 3, CFOP 5102,
CSOSN 900 e PIS/COFINS 49. Os pagamentos estavam registrados como dinheiro.

Duas tentativas controladas foram feitas sem consumir numeração:

| Tentativa | Resultado | Diagnóstico |
|---|---|---|
| NFC-e com `crt` numérico | HTTP 400 | O contrato exige `emitente.crt` como texto; o serializador do CorePet deve enviar `"1"`, e não `1` |
| NFC-e com `crt` em texto | HTTP 422 `OperacaoInvalida` | Emitente sem CSC de NFC-e; a requisição parou antes de validar os impostos |

Não é correto trocar o CSOSN 900 por outro código apenas para fazer o teste passar.
Depois do cadastro do CSC, a IntNFe precisa aceitar os campos do regime usados nos
cupons reais ou informar formalmente a conversão fiscal válida.

## Pendências priorizadas

### P0 — bloqueiam o piloto correto ou a produção

| Pendência | O que falta | Responsável sugerido |
|---|---|---|
| CSC da NFC-e em homologação | Obter na SEFAZ e cadastrar ID do token e segredo no emitente por canal protegido | Empresa/contador e equipe IntNFe |
| CSOSN 900 na NFC-e | Aceitar `ICMSSN900`, inclusive `pCredSN` e `vCredICMSSN` quando aplicáveis, e documentar o corpo | Equipe IntNFe |
| Intermediador de marketplace | Aceitar `indIntermed`, CNPJ do intermediador e `idCadIntTran`; gerar `indIntermed=1` e `infIntermed` no XML | Equipe IntNFe |
| Regra fiscal por operação | Confirmar com a contabilidade CFOP, CSOSN/CST, benefícios, DIFAL/FCP e natureza por estado/canal | Empresa/contador |
| Separação de ambientes | Manter CSC, série, numeração e credenciais explicitamente separados entre homologação e produção | CorePet/IntNFe |

### P1 — necessários para equivalência com as notas reais

| Pendência | Evidência encontrada |
|---|---|
| GTIN/EAN comercial e tributável | O produto de referência tinha GTIN no Bling, mas o XML IntNFe saiu como `SEM GTIN`; a documentação não expõe esses campos |
| Referência do pedido | Faltam campos estruturados como `xPed` e `nItemPed`, além do vínculo interno com canal e pedido |
| Pagamento detalhado | Faltam integração do pagamento, CNPJ da instituição/adquirente, bandeira, autorização, descrição, troco e múltiplos pagamentos quando aplicáveis |
| Transporte e volumes | Faltam quantidade/espécie/marca/numeração dos volumes, pesos, rastreio e dados logísticos completos |
| Entrega ao consumidor | O contrato de presença documentado não lista o código 4, necessário para entrega em domicílio quando aplicável |
| DANFE A4 | Reservar margem de impressão e conferir em impressora física comum |
| DANFE NFC-e | Conferir versão de 80 mm, QR Code, chave, protocolo, descontos, múltiplos itens e identificação do consumidor |

### P2 — completar antes de ampliar a operação

- Cancelamento, Carta de Correção, inutilização e consulta de eventos.
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

Segredos, certificados, CSC, dados pessoais e XMLs completos devem permanecer em
armazenamento protegido; não entram em logs comuns, documentos versionados ou
mensagens de diagnóstico.

## Próxima rodada de testes

1. Cadastrar o CSC de **homologação** sem expor o segredo em conversa ou commit.
2. Confirmar e liberar o CSOSN 900 no contrato da NFC-e.
3. Emitir uma NFC-e anônima equivalente a um cupom recente do PDV.
4. Emitir uma NFC-e com CPF para validar a Nota Fiscal Paulista.
5. Validar XML, QR Code e DANFE de 80 mm, depois cancelamento e reconsulta.
6. Corrigir o grupo de intermediador e repetir uma NF-e de cada marketplace.
7. Repetir os cenários com pagamento e logística fiéis à operação real.

## Fontes

- [Documentação da API IntNFe](https://intnfe.com.br/api/doc)
- [Portal da NFC-e da Secretaria da Fazenda de São Paulo](https://portal.fazenda.sp.gov.br/servicos/nfce/)
- [Sobre a NFC-e em São Paulo](https://portal.fazenda.sp.gov.br/servicos/nfce/Paginas/Sobre.aspx)
- [Como participar da Nota Fiscal Paulista](https://portal.fazenda.sp.gov.br/servicos/nfp/Paginas/Como-participar.aspx)
- [Nota Técnica NF-e 2020.006 — intermediador da operação](https://www.nfe.fazenda.gov.br/Portal/exibirArquivo.aspx?conteudo=A6qvFRVbPSA%3D)

