# IntNFe — rejeição de XML na primeira NF-e de homologação

A primeira solicitação de NF-e do piloto CorePet foi aceita com HTTP 202, mas
o processamento terminou em `SCHEMA`, sem autorização. Cadastro do emitente,
autenticação e certificado A1 já funcionam. A pendência atual é a geração dos
grupos de ICMS-ST e PIS/COFINS.

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

## Pendências para a equipe IntNFe

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
