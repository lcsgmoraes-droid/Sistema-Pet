# Inventario de estrutura geral

Data: 2026-05-16

Objetivo: identificar os maiores arquivos e hotspots de mudanca para guiar
refatoracoes pequenas, sem alterar comportamento e sem perder o trilho de PRs
curtos.

## Metodo

Comandos usados na raiz do repositorio:

```powershell
git ls-files
git log --name-only --pretty=format: --since='180 days ago'
```

Foram ignorados artefatos e dependencias locais: `node_modules`, `.venv`,
`dist`, `runtime`, `logs`, `__pycache__`, `.pytest_cache`, `uploads`,
`backups`, `limpeza`, `package-lock.json`, `.txt`, `.md` e backups locais.

## Maiores arquivos de codigo

| Posicao | Linhas | Arquivo | Leitura |
|---:|---:|---|---|
| 1 | 5479 | `backend/app/produtos_routes.py` | Rotas e regras de produtos concentradas demais. |
| 2 | 5311 | `backend/app/estoque_routes.py` | Estoque mistura operacao, validacao e integracoes. |
| 3 | 3871 | `frontend/src/components/EntradaXML.jsx` | Tela/componente grande de XML e entrada. |
| 4 | 3575 | `backend/app/notas_entrada_routes.py` | Entrada fiscal e notas em arquivo monolitico. |
| 5 | 3534 | `backend/app/pedidos_compra_routes.py` | Compras com varias regras no router. |
| 6 | 3399 | `backend/app/campaigns/routes.py` | Campanhas com superficie grande de endpoints. |
| 7 | 3096 | `backend/app/vendas/service.py` | Service central e critico do PDV/vendas. |
| 8 | 2785 | `backend/app/clientes_routes.py` | Cliente em router grande, muito reutilizado. |
| 9 | 2608 | `frontend/src/pages/EstoqueTransferenciaParceiro.jsx` | Fluxo operacional grande em uma pagina. |
| 10 | 2600 | `frontend/src/pages/ecommerce/EcommerceMVP.jsx` | Ecommerce concentrado em tela grande. |

## Hotspots por mudanca recente

Janela: ultimos 180 dias.

| Posicao | Alteracoes | Arquivo | Leitura |
|---:|---:|---|---|
| 1 | 82 | `backend/app/produtos_routes.py` | Maior combinacao de tamanho e churn. |
| 2 | 77 | `frontend/src/pages/PDV.jsx` | PDV muda muito e deve ter contrato forte. |
| 3 | 57 | `backend/app/main.py` | Entrada do backend ainda recebe muitas mudancas. |
| 4 | 57 | `frontend/src/components/Layout.jsx` | Layout global impacta muitas telas. |
| 5 | 54 | `frontend/src/App.jsx` | Roteamento/estrutura global com churn alto. |
| 6 | 42 | `frontend/src/components/VendasFinanceiro.jsx` | Financeiro de vendas com alto risco operacional. |
| 7 | 41 | `frontend/src/components/EntradaXML.jsx` | Tambem aparece entre os maiores arquivos. |
| 8 | 40 | `frontend/src/pages/Produtos.jsx` | Produto no frontend acompanha hotspot backend. |
| 9 | 35 | `frontend/src/components/PedidosCompra.jsx` | Compras e XML merecem separacao gradual. |
| 10 | 31 | `frontend/src/pages/ProdutosNovo.jsx` | Produto novo/formulario tem churn relevante. |

## Top 10 arquivos de maior risco

Ranking qualitativo combinando tamanho, churn, impacto de negocio e chance de
regressao.

| Risco | Arquivo | Motivo | Primeira acao segura |
|---:|---|---|---|
| 1 | `backend/app/produtos_routes.py` | Maior arquivo e maior churn. | Separar consultas/leitura em service sem mudar endpoints. |
| 2 | `frontend/src/pages/PDV.jsx` | Alto churn e fluxo de caixa critico. | Mapear contrato de eventos e dependencias antes de extrair componentes. |
| 3 | `backend/app/estoque_routes.py` | Muito grande e ligado a produto/compras. | Extrair helpers puros e cobrir com testes unitarios. |
| 4 | `frontend/src/components/EntradaXML.jsx` | Grande, muda bastante e afeta compras/fiscal. | Separar parse/estado em hook ou helper testado. |
| 5 | `backend/app/vendas/service.py` | Service critico de venda/pagamento/cupom. | Criar testes de contrato antes de qualquer quebra. |
| 6 | `backend/app/pedidos_compra_routes.py` | Router grande e operacional. | Mover regras de email/status para service. |
| 7 | `backend/app/notas_entrada_routes.py` | Fiscal/entrada com alto acoplamento. | Inventariar endpoints e schemas antes de extrair. |
| 8 | `frontend/src/components/Layout.jsx` | Componente global de navegacao/permissao. | Isolar configuracao de menu em arquivo puro. |
| 9 | `frontend/src/App.jsx` | Roteamento global com alto churn. | Extrair tabela de rotas por modulo. |
| 10 | `backend/app/clientes_routes.py` | Cliente e usado por quase todos os fluxos. | Separar buscas/listagens de mutacoes. |

## Padrao de modulo recomendado

Para cada modulo novo ou quebrado:

- `routes`: apenas HTTP, auth, status code e injecao de dependencias.
- `schemas`: entrada/saida Pydantic ou tipos frontend.
- `services`: regra de negocio e orquestracao.
- `repositories` ou queries: acesso a banco quando a regra ficar repetida.
- `tests`: contrato de endpoints criticos e unitarios dos services puros.
- `docs`: decisao operacional quando o modulo for sensivel.

## Primeira fatia recomendada

Modulo piloto: Produtos.

Motivo: `backend/app/produtos_routes.py` e telas de produtos aparecem no topo
de tamanho e churn. E um modulo grande, mas permite uma primeira fatia sem
mudar comportamento se comecarmos por leitura/consulta.

Sequencia sugerida:

1. Congelar comportamento atual com testes focados de listagem/busca de produto.
2. Criar pacote `backend/app/produtos/` com service de consultas.
3. Mover apenas funcoes puras ou queries de leitura para o service.
4. Manter as rotas e contratos HTTP iguais.
5. Repetir no frontend somente depois: extrair helpers de filtros/listagem em
   `frontend/src/features/produtos/`.

Nao comecar por venda/PDV ou pagamento. Esses fluxos devem vir depois que o
padrao estiver provado em uma fatia menos explosiva.

## Fechamento da etapa estrutural

Atualizacao: 2026-05-16.

Fatia executada em PRs curtos e validados:

- Produtos: busca, validade/listagem e racao/classificacao extraidas para
  `backend/app/produtos/`.
- Estoque: helpers de granel extraidos para `backend/app/estoque/granel.py`.
- PDV/vendas: regras puras de totalizacao/status extraidas para
  `backend/app/vendas/regras.py`.
- Campanhas/cupons: regras puras de cupom extraidas para
  `backend/app/campaigns/coupon_rules.py`.
- Financeiro: origem de contas a pagar extraida para
  `backend/app/financeiro/contas_pagar_origem.py`.

Foto da varredura final:

- Maiores arquivos ainda sao `produtos_routes.py`, `estoque_routes.py`,
  `EntradaXML.jsx`, `notas_entrada_routes.py` e `pedidos_compra_routes.py`.
- Hotspots recentes ainda incluem `produtos_routes.py`, `PDV.jsx`,
  `Layout.jsx`, `main.py` e `App.jsx`.
- A meta 10/10 de Estrutura geral fica condicionada a governanca continua:
  qualquer nova regra em hotspot deve entrar em fatia pequena, com teste focado
  e seguindo a Definition of Done modular.

## Atualizacao continua - 2026-06-03

Fatia executada na trilha Produtos/listagem:

- `backend/app/produtos_routes.py` extraiu helpers de listagem, promocao de
  preco para exibicao, reservas multitenant, area/fornecedor e metricas de
  valorizacao para `backend/app/produtos/listagem.py`.
- O router principal caiu de 6275 para 4677 linhas, preservando os nomes
  importados usados pelas rotas e testes antigos. A fatia de 2026-06-08 tambem
  extraiu a montagem de load options e filtros basicos de `listar_produtos` e
  `listar_produtos_vendaveis`.
- Testes focados adicionados em
  `backend/tests/unit/test_produtos_listagem_helpers.py` e mantidos em
  `test_produtos_listagem_kit_virtual.py`, `test_produtos_validade_listagem.py`
  e `test_produtos_search_helpers.py`.

## Atualizacao continua - 2026-06-23

Fatia executada na trilha Produtos/listagem:

- `backend/app/produtos_routes.py` extraiu a construcao de query base/status/busca
  de `listar_produtos` e `listar_produtos_vendaveis` para
  `_montar_query_listagem_produtos` e `_montar_query_produtos_vendaveis` em
  `backend/app/produtos/listagem.py`.
- A mesma rodada continuou com a extracao da expansao de hierarquia da listagem
  para `_expandir_produtos_listagem`, preservando contagem de variacoes,
  enriquecimento, validade e inclusao das variacoes logo apos o produto PAI.
- A fatia seguinte extraiu o fetch final paginado para
  `_buscar_pagina_produtos_listagem`, centralizando `count`, ordenacao,
  load options, offset/limit e remocao de itens nulos.
- A fatia de acabamento extraiu a montagem da resposta paginada para
  `_montar_resposta_produtos_paginados`, preservando `items`, `total`, `page`,
  `page_size`, `pages` e o fallback de total estimado em produtos vendaveis.
- As rotas preservaram endpoints, payloads, permissoes, tenant, paginacao,
  filtros basicos/fornecedor, reservas, validade e enriquecimento.
- Na branch atual, o router principal caiu de 1837 para 1740 linhas.
- Testes focados: `pytest backend/tests/unit/test_produtos*.py -q` passou com
  89 testes.

Proxima fatia recomendada:

1. Encerrar Produtos/listagem nesta rodada ou migrar para outro hotspot acima
   de 1000 linhas.
2. Manter endpoints, payloads, permissoes, tenant e paginacao iguais.
3. Nao misturar com estoque, PDV, fiscal, cadastro em lote ou regras de preco.

## Atualizacao continua - 2026-06-23 - Compras/Pedidos

Fatia executada na trilha Pedidos de Compra:

- `backend/app/pedidos_compra_routes.py` extraiu constantes e helpers puros da
  sugestao inteligente para `backend/app/pedidos_compra/sugestao.py`.
- Foram movidos: normalizacao numerica, arredondamento seguro, sanitizacao JSON,
  conversao de datetime para UTC naive, formatacao de origem de venda e estrutura
  inicial de estatisticas de venda.
- A fatia seguinte moveu tambem os acumuladores puros `_somar_venda_sugestao`
  e `_somar_conversao_granel_sugestao` para o mesmo modulo, cobrindo periodo,
  janelas, origens, fontes e conversao de granel por teste unitario.
- A agregacao de `vendas_rows` foi extraida para `_somar_vendas_rows_sugestao`,
  preservando a lista de pares `(venda_id, produto_id)` usada para nao contar
  venda direta duas vezes junto com movimentacoes de estoque.
- A agregacao de `conversoes_rows` foi extraida para
  `_somar_conversoes_granel_rows_sugestao`, mantendo a query no router e
  delegando apenas o consumo dos rows carregados para helper testado.
- A agregacao das movimentacoes complementares foi extraida para
  `_somar_movimentacoes_complementares_sugestao`, preservando deduplicacao de
  venda direta, consumo derivado e origem externa/Bling.
- A montagem do payload final foi extraida para `_montar_resultado_vendas_sugestao`,
  preservando arredondamento, ordenacao de origens/fontes e filtro/ordenacao dos
  itens de granel.
- O calculo de cobertura/ruptura `_calcular_dias_com_estoque` foi movido para
  `backend/app/pedidos_compra/sugestao.py`, mantendo a consulta de movimentacoes
  no router.
- A montagem textual `_gerar_observacao` foi movida para o mesmo modulo,
  preservando mensagens de ruptura, tendencia, ausencia de venda e fallback.
- O calculo de tendencia de vendas foi extraido para
  `_calcular_tendencia_vendas_sugestao`, preservando limiares de crescimento,
  queda, estavel e fallback `N/A`.
- O planejamento de compra da sugestao foi extraido para
  `_calcular_planejamento_compra_sugestao`, reunindo consumo observado/recente,
  ajuste por ruptura, lead time, cobertura alvo, quantidade sugerida e
  prioridade.
- A montagem do item final da sugestao foi extraida para
  `_montar_item_sugestao_compra`, preservando payload operacional,
  arredondamentos, janelas de venda, ruptura, estoque derivado e observacao.
- A deduplicacao dos vinculos fornecedor/produto e a montagem da resposta final
  foram extraidas para `_selecionar_produtos_fornecedor_sugestao` e
  `_montar_resposta_sugestao_compra`, preservando preferencia por fornecedor
  selecionado/principal, ordenacao por prioridade, resumo e sanitizacao JSON.
- Os helpers de consulta da sugestao foram movidos para
  `backend/app/pedidos_compra/sugestao_queries.py`, reunindo resolucao de
  fornecedores/grupos, carga de vendas/conversoes/movimentacoes, agrupamento de
  movimentacoes de estoque e estoque virtual.
- Endpoints, payloads, permissoes, tenant e regras de calculo de sugestao foram
  preservados; o router continua orquestrando consultas e montagem da resposta.
- Na branch atual, o router principal caiu de 1968 para 1253 linhas.
- Testes focados: `pytest backend/tests/unit/test_pedidos_compra_sugestao_helpers.py -q`
  passou com 20 testes.

Proxima fatia recomendada:

1. Encerrar Compras/Pedidos nesta rodada ou escolher outro hotspot acima de
   1000 linhas.
2. Nao mexer em recebimento de pedido, entrada de estoque, fiscal ou envio real
   de e-mail/WhatsApp na mesma rodada.

## Atualizacao continua - 2026-06-23 - Vendas/Comissoes

Fatia executada na trilha Vendas:

- `backend/app/vendas_routes.py` moveu helpers de reprocessamento de comissoes
  para `backend/app/vendas/comissoes.py`.
- Foram movidos os helpers de pagamentos tenant-safe, parcelas ja comissionadas,
  geracao de comissoes pendentes, total pago, contagem e remocao de comissoes.
- Os nomes continuam reexportados por `vendas_routes.py` para preservar imports
  internos e testes existentes.
- Na branch atual, o router principal caiu de 2236 para 2115 linhas.
- Testes focados: `pytest backend/tests/unit/test_vendas_comissao_reprocessamento_contract.py backend/tests/multi_tenant/test_phase2b_tenant_safe_sql.py -q`
  passou com 15 testes.
- Fatia seguinte na mesma data moveu os schemas Pydantic de entrada para
  `backend/app/vendas/schemas.py`, preservando os nomes expostos pelo router.
- No estado atual da branch, `backend/app/vendas_routes.py` esta com 2398
  linhas depois da extracao de schemas.
- Contagem atual recalculada: 79 arquivos de aplicacao ainda estao com 1000+
  linhas quando testes, migrations e builds sao excluidos. A contagem bruta com
  testes/migrations e 83.
- Testes focados da fatia de schemas: `pytest backend/tests/unit/test_vendas_comissao_reprocessamento_contract.py backend/tests/unit/test_entrega_status_contract.py -q`
  passou com 10 testes.

Proxima fatia recomendada:

1. Seguir em Vendas apenas se a proxima extracao for isolada de PDV/estoque ou
   escolher outro hotspot acima de 1000 linhas.
2. Nao misturar finalizacao/cancelamento/devolucao de venda com refatoracao de
   comissoes na mesma rodada.

## Atualizacao continua - 2026-06-23 - Dashboard/Ponto de Equilibrio

Fatia maior executada na trilha de arquivos grandes:

- `backend/app/dashboard_routes.py` moveu os calculos e classificacoes do Ponto
  de Equilibrio para `backend/app/dashboard/ponto_equilibrio.py`.
- Os endpoints `/financeiro/ponto-equilibrio` e
  `/financeiro/ponto-equilibrio/detalhes` foram movidos para
  `backend/app/dashboard/ponto_equilibrio_routes.py`.
- O router principal inclui o subrouter novo e reexporta os endpoints/helpers
  antigos para preservar imports internos e testes existentes.
- O arquivo principal caiu de 2227 para 762 linhas e saiu da zona acima de
  1000 linhas. Os dois novos arquivos ficaram abaixo de 1000 linhas.
- Contagem atual recalculada: 78 arquivos de aplicacao ainda estao com 1000+
  linhas quando testes, migrations e builds sao excluidos.
- Testes focados: `pytest backend/tests/unit/test_ponto_equilibrio_margem_vendas.py backend/tests/unit/test_ponto_equilibrio_classificacao.py backend/tests/unit/test_ponto_equilibrio_contract.py -q`
  passou com 13 testes.

Proxima fatia recomendada:

1. Escolher outro hotspot acima de 1000 linhas, priorizando modulo com testes
   existentes e corte por dominio claro.
2. Bons candidatos atuais: `clientes_routes.py`, `vendas/service.py`,
   `dre_canais_routes.py`, `vendas_routes.py` ou `nfe/listagem.py`.

## Atualizacao continua - 2026-06-23 - Clientes/Subrouters

Fatia maior executada na trilha de arquivos grandes:

- `backend/app/clientes_routes.py` moveu rotas financeiras e historicos legados
  para `backend/app/clientes/financeiro_routes.py`.
- Rotas de pets foram para `backend/app/clientes/pets_routes.py`.
- Rotas de credito/remocao de campo duplicado foram para
  `backend/app/clientes/credito_routes.py`.
- Rotas de parceiros, controle DRE e custo operacional de entregador foram para
  `backend/app/clientes/parceiros_routes.py`.
- Rotas de duplicidade e fusao de pessoas foram para
  `backend/app/clientes/duplicidades_routes.py`.
- O router principal inclui todos os subrouters e reexporta as funcoes antigas
  para preservar imports internos e testes existentes.
- O arquivo principal caiu de 2661 para 903 linhas e saiu da zona acima de 1000
  linhas. Todos os subrouters novos ficaram abaixo de 1000 linhas.
- Contagem atual recalculada: 77 arquivos de aplicacao ainda estao com 1000+
  linhas quando testes, migrations e builds sao excluidos.
- Testes focados: `pytest backend/tests/unit/test_clientes_financeiro_routes_contract.py backend/tests/unit/test_clientes_timeline_routes_contract.py backend/tests/unit/test_cliente_alertas_pdv.py backend/tests/unit/test_pessoa_duplicate_service.py backend/tests/unit/test_user_controlled_logging_contract.py -q`
  passou com 17 testes.

Observacao de validacao:

- `pytest backend/tests/unit/test_fornecedor_selector_quick_create_contract.py -q`
  tem uma falha preexistente em contrato textual do frontend, esperando
  `api.post('/clientes/', dados)` enquanto o arquivo atual usa outro formato de
  aspas. Nao foi alterado nesta fatia para evitar misturar escopo.

Proxima fatia recomendada:

1. Escolher o proximo hotspot acima de 1000 linhas com suite dedicada.
2. Candidatos atuais: `vendas/service.py`, `dre_canais_routes.py`,
   `vendas_routes.py`, `nfe/listagem.py` ou `contas_pagar_routes.py`.

