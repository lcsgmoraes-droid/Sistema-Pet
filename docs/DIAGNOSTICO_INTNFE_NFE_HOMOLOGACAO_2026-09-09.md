# IntNFe — diagnóstico e reteste da NF-e de homologação

**Atualização em 09/09/2026 às 23:19 de Brasília:** a correção dos valores e
da quantidade do DANFE foi confirmada por nova consulta da nota **1/003**,
já autorizada em homologação. Total agora **R$ 71,23**, com XML e autorização
intactos. A conferência adicional identificou divergência no **frete**:
XML com modalidade 9; DANFE exibe 0 (emitente).

Consulta posterior da nova rota de numeração do integrador: HTTP 200, com série
001 de homologação em `ultimoNumero=1000000` (próximo 1.000.001) e série 003 em
`ultimoNumero=1` (próximo 2). Isso é a sequência configurada no emissor, não um
histórico de notas autorizadas. Nenhum PUT foi realizado nessa verificação;
conciliar com a IntNFe a origem do avanço da série 001. O CorePet recebeu tela
para configurar a sequência por série/ambiente, ainda em desenvolvimento:
[contrato, testes e limites](ATIVACAO_FISCAL_INTNFE.md#numeração-por-série-e-ambiente).

## DANFE após a correção — valores corrigidos, frete pendente

Lucas informou a publicação da correção. Às **23:19:40 de Brasília**, foi
repetido somente `GET /nfe/3a6cea68-0a2d-4b1d-b7db-aff339a30497/danfe`, após
autenticação e consulta da nota. Retorno HTTP 200, com HTML diferente do
anterior. O mesmo endpoint entregou a versão corrigida para a nota existente,
sem nova emissão ou autorização. Estado, chave, protocolo e XML mantidos.

| Campo | Antes | Agora | Resultado |
|---|---|---|---|
| Produtos | 19.900,00 | 199,00 | Igual ao XML |
| Desconto | 12.777,00 | 127,77 | Igual ao XML |
| Total | 7.123,00 | 71,23 | Igual ao XML |
| Quantidade | 100.000 | 1,000 | Corresponde a uma unidade |

### Pendências restantes do DANFE

1. **Modalidade do frete divergente:** JSON enviado `frete.modalidade: "9"`;
   XML autorizado `<modFrete>9</modFrete>`; HTML no campo `FRETE POR CONTA`
   contém `<span class="info">0</span>` e legenda `0 - Emitente`. Representar
   a modalidade 9 (sem ocorrência de transporte) conforme o XML, incluindo
   o código e a legenda corretos. O valor do frete é zero; a divergência é
   o responsável/modalidade exibido, não o total financeiro da nota.
2. **Padronização decimal na linha do item:** valor unitário e total do item
   continuam como `199.00`, e impostos como `0.00`. Os valores são corretos,
   mas a apresentação ainda mistura ponto com a vírgula dos totais; usar
   formatação brasileira consistente, preservando a precisão de cada campo.

Para validar esses ajustes, consultar de novo o DANFE da **mesma nota 1/003**.
O XML autorizado permanece correto; não é necessário emitir outra nota.
Evidências privadas em `reteste-03-serie3/` na pasta local do piloto:
`DANFE-1-003-reconsulta-20260910T021940Z.html`,
`danfe-reconsulta-20260910T021940Z.json` e
`validacao-danfe-20260910T021940Z.json`. O HTML original e as versões anteriores
foram preservados, sem edição local. O histórico abaixo registra os problemas
anteriores e sua investigação.

## Teste com série 3 — autorizado, DANFE divergente

Lucas sugeriu testar outra série, como 3 ou 4. Foi alterado **somente** o campo
`serie` de `"1"` para `"3"`. Comparação do JSON confirmou os demais dados
preservados. Antes do POST, a tentativa anterior continuava rejeitada, o A1
seguia válido e a série 3 não constava na numeração da API. Nova chave de
idempotência foi persistida antes do envio; nenhuma sequência existente foi
editada. O ambiente permaneceu `2`, sem e-mail ao destinatário.

| Campo | Resultado |
|---|---|
| Correlation ID | `3a6cea68-0a2d-4b1d-b7db-aff339a30497` |
| ID da nota | `1be5fe0e-aa71-4077-82db-bfb00806546b` |
| Número/série | 1 / 003 |
| Aceite | HTTP 202, 09/09/2026 23:04:08 de Brasília |
| Autorização | Status 3, Autorizada, às 23:04:11; modelo 55, homologação |
| Chave | `35260933590794000140550030000000011158859473` |
| Protocolo | `135260008437173` |
| XML | `nfeProc`, `cStat=100`, `tpAmb=2` na nota e no protocolo |

O XML contém um item e os mesmos códigos/valores enviados. Foram conferidos
CNPJ, destinatário, nome padrão de homologação, modelo, chave, protocolo,
quantidade, produto, NCM, CFOP, CEST e total. Os grupos de impostos agora são
`ICMSSN500`, `PISOutr` e `COFINSOutr`, com CSOSN 500 e CST 49 preservados.

### Novo problema: números no DANFE

Comparação do XML autorizado com o texto do HTML devolvido por
`GET /nfe/{correlationId}/danfe`:

| Campo | XML correto | Texto exibido no DANFE |
|---|---|---|
| Produtos | `199.00` (R$ 199,00) | `19.900,00` |
| Desconto | `127.77` (R$ 127,77) | `12.777,00` |
| Total da nota | `71.23` (R$ 71,23) | `7.123,00` |
| Quantidade do item | 1 | `100.000` |

O DANFE contém a chave correta e o aviso sem valor fiscal. Seus números,
porém, não correspondem ao XML. O comportamento é compatível com problema
de interpretação de separadores decimais; a causa interna ainda exige
verificação na IntNFe. Conferir conversão dos decimais do XML e formatação
em português do Brasil, incluindo quantidades, valores, descontos e totais.
O HTML original foi preservado sem correção local.

### Endpoint confirmado para consultar novamente o DANFE

Em **09/09/2026 às 23:13:26 de Brasília**, a pedido de Lucas, foi testado:

```http
GET https://api.intnfe.com.br/nfe/3a6cea68-0a2d-4b1d-b7db-aff339a30497/danfe
Authorization: Bearer <token do emitente>
```

Retorno **HTTP 200**, HTML do DANFE da nota 1/003. Foram feitas consultas da
nota antes e depois e nova leitura do XML: estado, chave, protocolo, horário
de autorização e XML permaneceram idênticos. **Não houve POST de emissão**.
O DANFE ainda mostrou total 7.123,00 e teve o mesmo hash do arquivo anterior.

O endpoint permite obter novamente a representação da nota autorizada, sem
repetir autorização. A documentação não especifica se há renderização a cada
requisição ou cache; a resposta idêntica antes do ajuste não distingue esses
comportamentos. Depois da correção, repetir somente esse GET e comparar o HTML
com o XML. Se ainda vier antigo, verificar cache/geração do DANFE no provedor.

Evidências em `reteste-03-serie3/` dentro da pasta privada do piloto:
`DANFE-1-003-reconsulta-20260910T021325Z.html` e
`danfe-reconsulta-20260910T021325Z.json`. Script local
`baixar-danfe-autorizada.ps1` consulta apenas a nota existente, XML e DANFE;
o único POST nele é para obter o token de autenticação.

**Próxima ação da equipe IntNFe:** corrigir o DANFE e regenerá-lo para esta
mesma nota autorizada. Não é necessário emitir outra NF-e para validar a
representação, pois XML, chave e protocolo já existem. Depois comparar de
novo os totais e a quantidade com o XML.

Evidências privadas em `runtime/analises/fiscal/2026-09-09/reteste-03-serie3/`:
`NF-e-LJ-HOMOLOGACAO-1-003.xml`, `NF-e-LJ-HOMOLOGACAO-1-003.html`,
`validacao-arquivos.json`, payload, controle, resposta, status e preflight.
Arquivos com dados pessoais permanecem fora do Git.

### Como localizar e preparar a numeração

A [IntNFe documenta](https://intnfe.com.br/api/doc) numeração independente por
emitente, série e ambiente. A última NF-e **de produção** do Bling não resolve
a colisão dos testes de **homologação**. O uso da série 3 permitiu prosseguir
com este piloto, sem alterar o histórico da série 1 ou as notas do Bling.

Para preparar uma futura migração de produção, consultar no Bling **Vendas →
Notas Fiscais de Saída**, conferir CNPJ, ambiente, séries utilizadas e a
numeração já consumida, incluindo situações e faixas inutilizadas. O XML
mostra `emit/CNPJ`, `ide/serie`, `ide/nNF` e `ide/tpAmb`. Conferir a sequência
vigente no momento da mudança de emissor e coordenar emissões simultâneas.
O [Bling descreve a sequência por série](https://ajuda.bling.com.br/hc/pt-br/articles/360035907793-Como-preencher-os-dados-da-nota-fiscal).
Depois desse levantamento, a IntNFe oferece `PUT /painel/numeracao` com
último número, série e ambiente. Esse ajuste de produção não foi executado.

O histórico da duplicidade da série 001 em homologação continua pendente
de conciliação se essa série voltar a ser usada. Não bloqueia a nota já
autorizada na série 003. Os testes anteriores estão preservados abaixo.

## Histórico do segundo teste — erro de duplicidade

## Reteste com dados idênticos

Lucas pediu nova tentativa sem alterar os dados. A nota anterior foi consultada
e continuava rejeitada. O JSON original foi copiado sem alteração, com hash
SHA-256 idêntico; foi usada nova chave de idempotência, registrada antes do POST.
Cliente, item, impostos, total de R$ 71,23, série 1 e ambiente 2 foram mantidos.

| Campo | Reteste |
|---|---|
| Correlation ID | `9b91430f-836f-4e50-9b87-18d3c621ae00` |
| ID da nota | `65e07293-430b-4eef-9e1c-99e96196872c` |
| Número/série | 2 / 001, atribuídos pela IntNFe |
| Aceite | HTTP 202, 09/09/2026 22:38:58 de Brasília |
| Resultado | Status 4, Rejeitada, código `539`, às 22:39:03 |
| Chave gerada para a tentativa | `35260933590794000140550010000000021129399375` |
| Chave preexistente indicada no retorno | `35260933590794000140550010000000021831593887` |
| Recibo indicado no retorno | `351000217826821` |
| Protocolo/autorizadoEm | Nulos |

Mensagem recebida:

```text
Rejeição: Duplicidade de NF-e com diferença na Chave de Acesso [chNFe:35260933590794000140550010000000021831593887][nRec:351000217826821]
```

Os erros anteriores de `ICMSSN500` e CST 49 não apareceram no novo retorno.
Isso indica avanço da validação do XML para uma rejeição de duplicidade neste
cenário; não comprova autorização nem valida todos os cenários tributários.

Conferências posteriores, somente leitura:

- `GET /painel/numeracao`: série 001, ambiente 2, último número 2, próximo 3.
- `GET /nfe/chave/{chavePreexistente}`: HTTP 404 `NfeNaoEncontrada` no emitente
  atual. A API não recuperou a nota que o retorno de duplicidade referencia.
- `GET /nfe`: apenas as notas 1/001 (`SCHEMA`) e 2/001 (`539`), ambas rejeitadas.

**Próxima ação da equipe IntNFe:** localizar o histórico da chave preexistente
e reconciliar a sequência de homologação antes do próximo envio. Uso anterior
da numeração antes da remoção dos emitentes é uma hipótese, não uma causa
confirmada. O próximo número 3 informado pela API não comprova disponibilidade
na SEFAZ. Nenhuma sequência foi alterada e não foram feitas outras emissões
para tentar ultrapassar o conflito.

O retorno desta nota rejeitada já contém uma chave gerada. Portanto, a presença
de `chaveAcesso` sozinha não significa autorização: conferir também status,
protocolo e XML autorizado. XML/DANFE autorizado permanecem pendentes.

Evidências privadas em `runtime/analises/fiscal/2026-09-09/reteste-02/`, incluindo
payload, controle, resposta, status e `conciliacao-duplicidade.json`. O erro
original segue abaixo como histórico para comparação.

## Histórico: primeira tentativa com erro de XML

A primeira solicitação foi aceita com HTTP 202 e terminou em `SCHEMA`.
Cadastro do emitente, autenticação e certificado A1 já estavam funcionando.

## Identificação para localizar o processamento

| Campo | Valor |
|---|---|
| Integrador | CorePet — Lucas Guerra |
| Emitente | LJ COMERCIO DE RACOES E PET SHOP LTDA, CNPJ 33590794000140 |
| Tenant | `4ef8812e-51da-4dd7-85dc-8b47df8c5148` |
| Correlation ID | `d8026b27-c1e9-441f-b8a0-8f667a901376` |
| ID da nota | `14c0f376-6bd8-4c9e-b7e5-a3de537defdc` |
| Ambiente/modelo | Homologação (`ambienteCodigo: 2`), NF-e modelo 55 |
| Número/série | 1 / 001 |
| Criação | 09/09/2026 21:37:43 de Brasília; 10/09/2026 00:37:43 UTC |
| Resultado | Status 4, Rejeitada, código `SCHEMA` |
| Chave/protocolo | Nulos; nenhum XML autorizado ou DANFE obtido |

## Cenário enviado

Lucas autorizou usar um cliente e um produto existentes no Bling exclusivamente
em homologação. A referência foi a nota autorizada 017697, série 2, consultada
sem alterações. O destinatário é pessoa física não contribuinte em SP, com
nome padrão de homologação, CPF válido e endereço conferido; seu e-mail foi
omitido. Seus dados pessoais não estão neste relatório.

Um item: MGZ EXT COELHOS ORNAMENTAIS 1,2 KG; SKU `022860.1/1`; quantidade 1 UN;
R$ 199,00 menos R$ 127,77 de desconto = **R$ 71,23**. Mesmo valor no pagamento
em dinheiro; sem frete. CRT `"1"`, NCM `23099010`, CFOP `5405`, CEST `2200100`.
Os códigos e os valores dos impostos foram mantidos conforme a nota de origem:

```json
{
  "icms": {
    "cst": "500",
    "origem": "0",
    "baseCalculoSt": 0,
    "valorStRetido": 0
  },
  "pis": { "cst": "49", "aliquota": 0 },
  "cofins": { "cst": "49", "aliquota": 0 }
}
```

Sem IPI na referência. A [documentação consultada](https://intnfe.com.br/api/doc)
descreve CSOSN 500 e os campos de retenção; para PIS/COFINS, descreve 01/02 como
tributados e os demais como não tributados. O contrato precisa distinguir os
CST aceitos e o grupo XML correspondente, incluindo o CST 49 deste caso.

## Retorno recebido

Trechos literais do `motivoRejeicao`, preservando os nomes das tags:

```text
1:1773 The element 'ICMSSN500' in namespace 'http://www.portalfiscal.inf.br/nfe' has invalid child element 'vICMSSTRet' in namespace 'http://www.portalfiscal.inf.br/nfe'. List of possible elements expected: 'pST' in namespace 'http://www.portalfiscal.inf.br/nfe'.
1:1841 The 'http://www.portalfiscal.inf.br/nfe:CST' element is invalid - The value '49' is invalid according to its datatype 'String' - The Enumeration constraint failed.
1:1886 The 'http://www.portalfiscal.inf.br/nfe:CST' element is invalid - The value '49' is invalid according to its datatype 'String' - The Enumeration constraint failed.
```

O retorno aponta para a estrutura do XML gerado. O XML rejeitado não foi
obtido pelo piloto; a confirmação da causa interna exige a equipe IntNFe
examinar esse processamento e o código que constrói os grupos.

## Pendências levantadas na primeira tentativa (histórico)

1. Conferir campos e ordem de `ICMSSN500`: o schema espera `pST` antes do
   `vICMSSTRet` que foi gerado. Verificar o contrato necessário para a retenção,
   inclusive quando seus valores são zero, e atualizar a documentação.
2. Conferir o grupo XML usado para PIS e COFINS com CST 49 e alíquota zero.
   Esse código veio do cenário real de referência; não foi substituído por
   outro código tributário para contornar a rejeição.
3. Validar o XML corrigido no schema antes de retomar a emissão. Se forem
   necessários novos campos no JSON, informar seu nome, tipo e regra.
4. Depois da correção, realizar tentativa controlada em homologação e conferir
   chave/protocolo, `tpAmb=2`, modelo 55, item, totais, XML autorizado e DANFE.

O primeiro pedido HTTP do teste tinha CRT numérico e recebeu HTTP 400. Isso
foi corrigido para string conforme o exemplo oficial, após consulta comprovar
zero notas. Esse erro de formato do cliente está resolvido e é distinto da
rejeição de schema do processamento aceito acima. Houve apenas uma nota criada.

Corpo exato, chave de idempotência e respostas foram preservados somente em
`runtime/analises/fiscal/2026-09-09/`, ignorado pelo Git. Segredos usam DPAPI e
não estão no relatório. [Registro completo e pendências do piloto](FISCAL_INTNFE_PILOTO_HOMOLOGACAO.md).
