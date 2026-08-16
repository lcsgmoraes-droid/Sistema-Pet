# Integração CorePet com iFood — Fase 1

## Objetivo

Usar o cadastro de produtos já existente no CorePet para preparar o catálogo do
iFood, sem exigir que a loja cadastre os anúncios um a um. O CorePet permanece
como fonte principal de produto, preço e estoque.

Esta fase entrega configuração por empresa, diagnóstico do catálogo, simulação
de publicação e a base técnica da iFood Merchant API. O envio real permanece
bloqueado até a aprovação e a homologação do aplicativo CorePet no iFood.

## Como o catálogo é montado

A empresa pode escolher uma destas fontes:

- **E-commerce:** somente produtos marcados para anunciar no e-commerce. Usa o
  preço específico do e-commerce e, quando ele não existe, o preço de venda do
  ERP.
- **ERP:** todos os produtos ativos e vendáveis. Usa o preço de venda do ERP.

| CorePet | iFood Item API | Regra |
| --- | --- | --- |
| `codigo_barras` ou `gtin_ean` | `barcode` | Prioriza EAN; na ausência, usa o SKU como código interno permitido pela API |
| `codigo` | `plu` | Identificador interno da loja |
| `nome` | `name` | Obrigatório |
| preço do canal | `prices.price` | Deve ser maior que zero; pode receber acréscimo específico do iFood |
| promoção vigente | `prices.promotionPrice` | Enviada somente com desconto superior a 5% |
| `estoque_atual` | `inventory.stock` | Nunca fica negativo e pode descontar uma reserva de segurança |
| departamento/categoria/subcategoria | `details.categorization` | Aproveita a organização já cadastrada |
| marca | `details.brand` | Aproveita a marca já cadastrada |
| unidade | `details.unit` | Aproveita a unidade de venda |
| imagem principal | `details.imageUrl` | Converte caminho relativo em URL pública |
| descrição | `details.description` | Prioriza a descrição completa |

O campo `volume` atual do CorePet representa cubagem logística. Ele não é enviado
como volume comercial do iFood para evitar misturar conceitos diferentes.

Produtos inativos, excluídos, serviços, agrupadores, itens não vendáveis, sem
identificador ou sem preço válido ficam fora do envio e aparecem no diagnóstico.

## O que já está implementado

- Configuração multiempresa com Merchant ID, fonte do catálogo, acréscimo de
  preço e reserva de estoque.
- Credenciais OAuth centralizadas no servidor; nenhum `clientSecret` é salvo na
  configuração da loja.
- Tela em **Configurações > Integrações > iFood**.
- Prévia com itens aceitos, recusados, erros e avisos.
- Simulação de publicação sem chamada ao iFood.
- Cliente OAuth `client_credentials`, consulta das lojas autorizadas e ingestão
  pelo módulo Item.
- `POST` somente para criação/reativação e `PATCH` para atualização.
- O parâmetro destrutivo `reset=true` nunca é utilizado.
- Trava global para envio real e limite local de 200 produtos por chamada.

## Variáveis do servidor

```dotenv
IFOOD_API_BASE_URL=https://merchant-api.ifood.com.br
IFOOD_CLIENT_ID=
IFOOD_CLIENT_SECRET=
IFOOD_REQUEST_TIMEOUT_SECONDS=15
IFOOD_CATALOG_WRITE_ENABLED=false
```

`IFOOD_CATALOG_WRITE_ENABLED` deve continuar `false` até o aplicativo concluir a
homologação. Credenciais reais pertencem ao ambiente do servidor e não devem ser
commitadas.

## Passos externos para ativação

1. Cadastrar ou ajustar o aplicativo CorePet no Portal do Desenvolvedor iFood.
2. Solicitar acesso à categoria de mercado e ao módulo **Item**, que é exclusivo
   e não fica disponível automaticamente para todos os aplicativos.
3. Concluir o processo de autorização das lojas e obter o Merchant ID do cliente
   piloto.
4. Configurar `IFOOD_CLIENT_ID` e `IFOOD_CLIENT_SECRET` no ambiente de homologação.
5. Rodar o diagnóstico no CorePet e corrigir os produtos recusados.
6. Executar os casos exigidos na homologação do módulo Item.
7. Somente depois disso, liberar o envio real em ambiente controlado.

## Proteções operacionais

A documentação do iFood orienta usar `POST` apenas para produtos novos ou para
reativação e `PATCH` para alterações. Também limita o processamento de uma parte
do catálogo por janela e pode responder `429` quando a volumetria é excedida. O
próximo estágio deve persistir o vínculo de cada item e as diferenças já enviadas
para mandar somente o que mudou, além de controlar a fila por janela.

O iFood também pode expurgar itens inativos ou com preço inválido que permaneçam
sem atualização por determinado período. Esse monitoramento deverá entrar na
rotina de catálogo antes da liberação geral.

## Próximas fases recomendadas

1. **Homologação e catálogo piloto:** vínculo por produto, histórico de envio,
   controle de diferenças, fila de sincronização e conferência do resultado no
   Portal do Parceiro.
2. **Pedidos:** recebimento de eventos, aceite, atualização de status, impressão
   e envio automático para o App Separador.
3. **Operação:** baixa/reserva de estoque, substituição ou indisponibilidade de
   itens, cancelamento e conciliação do pedido.
4. **Financeiro e indicadores:** taxas, repasses, margem por canal, divergências e
   rentabilidade do iFood.

## Referências oficiais

- [Módulo Item — visão geral, payloads e limites](https://developer.ifood.com.br/pt-BR/docs/guides/modules/item/general/)
- [Homologação do módulo Item](https://developer.ifood.com.br/pt-BR/docs/guides/modules/item/homologation)
- [Portal do Desenvolvedor iFood](https://developer.ifood.com.br/)
