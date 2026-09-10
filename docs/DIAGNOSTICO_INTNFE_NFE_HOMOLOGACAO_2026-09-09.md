# IntNFe — diagnóstico e reteste da NF-e de homologação

**Atualização em 09/09/2026 às 22:39 de Brasília:** o reteste com os mesmos dados
não repetiu os erros de XML. A nota **2/001** foi rejeitada com **539 — duplicidade
de NF-e com diferença na chave de acesso**. A pendência atual é reconciliar a
numeração de homologação com o histórico já existente. Ainda sem autorização.

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
