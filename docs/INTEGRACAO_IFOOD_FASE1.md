# Integração CorePet com iFood — Fase 1

## Objetivo

Usar o cadastro de produtos já existente no CorePet para preparar o catálogo do
iFood, sem exigir que a loja cadastre os anúncios um a um. O CorePet permanece
como fonte principal de produto, preço e estoque.

Esta fase entrega configuração por empresa, diagnóstico do catálogo, simulação
de publicação e a base técnica da iFood Merchant API. O envio real permanece
bloqueado até a aprovação e a homologação do aplicativo CorePet no iFood.

## Cadastro e central operacional (2026-10-19)

A preparação local agora usa uma seleção **própria do iFood**, dentro do mesmo
componente de cadastro/edição de produtos do CorePet. A central fica em
**Vendas e relacionamento > iFood** (`/ifood`) e abre esse cadastro para editar.
Não existe um segundo cadastro de anúncios.

- `anunciar_ifood` controla a intenção de venda da loja; começa desmarcado.
- `preco_ifood` informado prevalece exatamente; vazio usa o preço normal do ERP
  com o acréscimo da loja. Promoções de app/ecommerce/ERP não são herdadas.
- Promoção exclusiva do iFood tem preço e período próprios, opcionais.
- A margem exibida é contribuição estimada por unidade, com custo, comissão por
  modalidade, taxa de pagamento, tributos estimados e despesas unitárias.
  Premissa desconhecida fica sem valor e impede o cálculo; zero é explícito.
- Estoque é derivado do ERP, descontando reservas e segurança; kits virtuais
  usam a capacidade dos componentes. Pausa manual permanece após reposição.
- Pendências de canal não impedem salvar um produto válido no ERP. Foto e
  descrição são recomendações; serviços, agrupadores e granel ficam impedidos.
- Seleção, pausa e preços pertencem à loja. Produtos de outra loja compartilhados
  pelo grupo precisam ser cadastrados localmente antes de configurar o canal.

O diagnóstico de integração passou a respeitar essa seleção e o preço iFood.
Os campos históricos `catalog_source` são preservados para compatibilidade,
mas não autorizam selecionar automaticamente produtos de outro canal.
`pronto_para_envio` significa apenas cadastro local apto; não confirma anúncio
publicado. Fila, vínculo remoto, confirmação de publicação e pedidos no PDV
continuam nas próximas etapas.

Veja a [ficha da entrega](entregas/2026-10-19-cadastro-central-ifood.md) e o
[registro de validação local](homologacoes/2026-10-19-cadastro-central-ifood.md).

## Calculadora de preço na central (2026-10-20)

Na central, a ação **Simular preço e margem** abre a calculadora do produto.
O usuário pode testar um preço específico ou a regra da loja e alternar os
cenários de entrega. A estimativa e as pendências são recalculadas pela mesma
regra usada no cadastro, com custo, estoque, taxas e promoção vigentes.

A simulação não grava nada. **Aplicar preço ao produto** altera somente o preço
específico iFood no cadastro canônico, para quem tem permissão de editar o
produto. Não altera o preço ERP, os outros canais, custos, seleção ou pausa.
Se houver promoção iFood vigente, ela continua determinando o preço efetivo;
alterar o preço regular não remove a promoção.

Endpoint somente de consulta: `POST /integracoes/ifood/catalogo/produto/simular-preco`,
com `product_id` e `preco_ifood` (nulo segue a regra da loja). A gravação usa o
`PUT /produtos/{id}` existente. Confira a
[entrega da calculadora](entregas/2026-10-20-calculadora-preco-ifood.md).

## Fontes históricas do diagnóstico

Antes da seleção própria por produto, o diagnóstico oferecia estas fontes:

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
- `reset=true` fica disponível apenas na ação explícita de homologação, exige
  confirmação adicional na tela e somente pode ser usado com `POST`. A ação
  informa que todos os produtos omitidos serão desativados pelo iFood.
- Trava global para envio real e limite local de 200 produtos por chamada.

## Variáveis do servidor

```dotenv
IFOOD_API_BASE_URL=https://merchant-api.ifood.com.br
IFOOD_CLIENT_ID=
IFOOD_CLIENT_SECRET=
IFOOD_REQUEST_TIMEOUT_SECONDS=15
IFOOD_CATALOG_WRITE_ENABLED=false
```

`IFOOD_CATALOG_WRITE_ENABLED` deve ficar `true` somente no ambiente controlado
em que os testes do módulo Item serão executados. Credenciais reais pertencem ao
ambiente do servidor e não devem ser commitadas.

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
