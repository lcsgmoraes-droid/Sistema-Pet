# Evolucao enterprise, UI e refatoracao

Arquivo consolidado para reduzir a dispersao de documentacao sobre padronizacao visual, componentes reutilizaveis, refatoracao de arquivos grandes, auditoria enterprise e historico de padronizacao.

Este arquivo substitui os documentos antigos abaixo, preservando o conteudo util em uma unica fonte de consulta:
- docs/MAPEAMENTO_EVOLUCAO_ENTERPRISE_2026-05-02.md
- docs/DESIGN_SYSTEM_UI.md
- docs/AUDITORIA_ENTERPRISE_SISTEMA_2026-03-29.md
- CHANGELOG_PADRONIZACAO.md

## Indice

- Mapa de evolucao enterprise
- Design system UI
- Auditoria enterprise do sistema
- Changelog de padronizacao de nomes

---

<!-- Origem consolidada: docs/MAPEAMENTO_EVOLUCAO_ENTERPRISE_2026-05-02.md -->

# Mapeamento de evolucao enterprise - sistema inteiro - 2026-05-02

Este documento organiza a evolucao visual, estrutural e logica do sistema inteiro. Produtos, campanhas e comissoes foram apenas exemplos iniciais; a meta e repassar todas as telas e todos os fluxos recorrentes.

## Objetivo

Transformar o sistema em uma base mais modular, previsivel e facil de manter:

- Componentes reutilizaveis para pessoas, produtos, pets, filtros, tabelas, botoes, cards, modais e dashboards.
- Regras visuais claras: mesmas cores, tamanhos, fontes, espacamentos e estados para a mesma intencao.
- Regras de negocio centrais e auditaveis, sem depender do caminho executado pelo usuario.
- Arquivos grandes sendo reduzidos por etapas, sem refatoracao cega.
- Conteudo rico seguro via Markdown/renderizacao controlada.

## Andamento

### Foco atual - Plano Basico vendavel

Antes de ampliar a varredura para o sistema inteiro, a frente atual e fechar o Plano Basico como primeiro produto vendavel. O controle vivo de telas testadas, isolamento tenant, bloqueio de premium, padronizacao visual e pendencias P1 esta em `docs/auditorias/plano-basico-tenant-checklist.md`.

Regra pratica desta fase: primeiro deixar Pessoas, Pets, Produtos, Estoque, PDV, Financeiro de Vendas, Cadastros essenciais, Configuracoes e Usuarios com fluxo principal confiavel em tenant novo; depois voltar para refatoracoes maiores fora desse escopo.

### Fase 1 - Fundacao visual e piloto PDV

Status: iniciada.

Componentes globais criados ou consolidados:

- `ActionButton` e `IconActionButton` para a regra unica de cores por intencao.
- `Panel` para cards/blocos com borda, raio, sombra e padding consistentes.
- `PageHeader` para cabecalho padrao de telas e modulos.
- `StatusBadge` para status como pago, aberto, cancelado, ativo e entregue.
- `MetricCard` e `MetricGrid` para padronizar dashboards e cards de indicadores.
- `MoneyCell`, `ChannelBadges` e `SafeMarkdown`, ja iniciados na fatia de produtos.
- `CopyableValue` para valores copiaveis padronizados, como numero de venda, nome de produto, SKU e codigos operacionais.
- `CustomerIdentity`, `PetIdentity`, `FornecedorIdentity`, `ProductIdentity` e `SaleReference` para cliente/codigo, pet/codigo, fornecedor/documento, produto/SKU e venda sempre copiaveis.
- `FornecedorSelector` para busca de fornecedor com autocomplete e cadastro rapido, evitando selects locais e campos livres inconsistentes.
- `FormField`, `TextField` e `SelectField` para campos de formulario com tons visuais reaproveitaveis sem quebrar telas existentes.
- `PaginationControls` para paginacao, seletor de quantidade por pagina e navegacao com tamanho/cor padrao.
- `EmptyState`, `LoadingState` e `ErrorState` para estados vazios, carregamento e falhas com visual unico.

Separacao operacional iniciada:

- `MLProHub Ops`: central propria em `/ops`, fora do layout de operacao do Pet Shop.
- Cockpit inicial em `/ops`, com health, alertas automaticos, tenants/rotas sensiveis, deploys recentes e auto-recuperacao.
- A observabilidade detalhada saiu do menu normal de Administracao e passou para `/ops/observabilidade`.
- A rota antiga `/admin/observabilidade` deve apenas redirecionar, para nao quebrar link salvo.
- Backend consolidado em `/admin/observabilidade/ops-summary`, para a inteligencia operacional ficar centralizada e reutilizavel.
- Watchdog passou a registrar eventos em `logs/watchdog_events.jsonl`, permitindo auditar quando o sistema tentou se recuperar sozinho.
- Painel de suporte em `/ops/incidentes`, com drilldown por tenant, rota e request_id para investigar producao sem depender apenas de relato do cliente.
- Alertas acionaveis por tenant/rota em `/ops/incidentes`, com severidade, filtro em um clique e sugestao de correcao para erro repetido, lentidao recorrente e recuperacao automatica.
- Ops/tenants: MVP tecnico integrado em `/ops/tenants`, com lista de tenants, plano/cobranca, contagens, uso, manutencao comercial e simulacao/aplicacao controlada do catalogo base. Pendencia operacional: Lucas confirmar a tela em producao e validar uma simulacao real antes de qualquer aplicacao em cliente.
- Incidentes operacionais passaram a ter persistencia em banco (`ops_error_events`, `ops_alerts`, `ops_recovery_actions`), mantendo os `.jsonl` apenas como fallback/backfill.
- Deploy seguro agora aplica Alembic automaticamente antes das validacoes finais, para evitar producao com codigo novo e banco antigo.
- Watchdog ganhou registro de recuperacao de health e guarda contra loop de restart em janela curta.
- Incidente de lentidao de 2026-05-04: Ops apontou degradacao sem 5xx, concentrada em requisicoes lentas no tenant principal. A rota mais critica foi `/produtos/vendaveis`, usada pelo PDV durante digitacao/bipagem.
- Hotfix local preparado: `/produtos/vendaveis` passou a usar enriquecimento leve, sem calcular composicao/custo/estoque virtual detalhado por sugestao; logs de kit/custo foram rebaixados para debug; o frontend do PDV passou a cancelar buscas antigas e limitar sugestoes.
- Proxima evolucao de performance: criar endpoint dedicado de sugestao de produtos para PDV, cachear estoque virtual/custo de kits por evento de estoque, auditar dados de `tipo_kit` inconsistentes e adicionar indices/EXPLAIN nas rotas mais lentas do Ops.
- Incidente de lentidao de 2026-05-07: Ops apontou degradacao sem 5xx, concentrada em `/integracoes/bling/pedido`. Causa raiz: webhook fazia consulta externa ao Bling, retries e esperas dentro da request publica.
- Melhoria de escala preparada: `/integracoes/bling/pedido` passou a enfileirar eventos em `bling_pedido_webhook_events` e responder rapidamente; o processamento pesado fica no `BlingSyncScheduler`, com idempotencia por `eventId`/payload, retry com backoff e indices por tenant/pedido/status.
- Correcao de rastreabilidade Ops: webhooks Bling agora marcam `tenant_id` no contexto da request pelo `BLING_WEBHOOK_TENANT_ID`, evitando incidentes operacionais como `sem_tenant`; historico recente pode ser corrigido com `python -m app.scripts.backfill_ops_tenant_context --path-prefix /integracoes/bling/`.
- Orientacao de producao registrada em `docs/PRODUCAO_DEPLOY_SSH.md`: deploy real por SSH no IP `192.241.150.121`, caminho `/opt/petshop`, script oficial `bash scripts/deploy_producao_seguro.sh`.
- Proxima evolucao operacional: separar containers de `backend-api`, `worker-bling`, `worker-campanhas` e `worker-sefaz`, para impedir que integracoes externas concorram com PDV/admin pelo mesmo orcamento de workers e conexoes.

Tela piloto:

- PDV: cabecalho, botoes principais, botoes de modo visualizacao, sidebar de vendas recentes e cards principais comecaram a consumir a fundacao global.
- Banho & Tosa: agenda, ficha operacional, creditos, fotos, ocorrencias e taxi dog passaram a usar os campos reutilizaveis mantendo o tom visual atual.
- Banho & Tosa: listas de servicos, recursos, parametros e pacotes passaram a usar `ActionButton` global para edicao/exclusao com cores por intencao.
- Banho & Tosa: formularios de pacotes e campanhas de retorno tambem passaram a usar `TextField`/`SelectField` globais.
- Banho & Tosa: `FormField` ganhou acessorio de rotulo e os formularios com tooltip migraram para os campos globais, removendo os campos locais duplicados do modulo.
- Banho & Tosa: checkboxes de servicos, recursos, portes e pacotes passaram a usar `CheckboxField` global com o mesmo tom visual.
- Banho & Tosa: tela de parametros foi reorganizada para abrir com resumo e lista compacta; configuracoes gerais e cadastro/edicao de porte agora aparecem apenas por acao explicita.
- Banho & Tosa: agenda deixou de exibir a grade "Horarios x recursos"; agenda, sugestoes de horarios e fila passaram a exibir foto do pet quando disponivel.
- Banho & Tosa: fila do dia foi redesenhada em kanban compacto com cards arrastaveis, etapas reordenaveis por drag and drop e acoes reduzidas para avancar ou escolher etapa.
- Banho & Tosa: ao marcar atendimento como entregue, o frontend tenta gerar a venda no PDV pelo endpoint existente, reduzindo dependencia da tela de fechamentos.
- Produtos e Pessoas: paginacoes locais foram substituidas por `PaginationControls` global, removendo controles duplicados.
- Operadoras, internacoes veterinarias e Estoque Bling comecaram a usar estados globais de vazio/carregamento.
- Pets: `PetSelector` e `NovoPetButton` passaram para `components/pets`; PDV, seletor tutor/pet do veterinario e fluxos de agenda, IA, calculadora de doses, exames, internacoes e vacinas agora usam a mesma base visual e de comportamento.
- PDV: resumo de cliente selecionado passou a usar `EntityCard` em modo compacto, mantendo o alinhamento de CPF, codigo, telefone, fidelidade, cupons e credito.
- PDV/Caixa: devolucao aberta a partir de uma venda carregada passa a iniciar diretamente naquela venda, mantendo a busca manual como caminho alternativo.
- PDV/Produtos: numero de venda, nomes de produtos e SKUs avancaram para o padrao copiavel reutilizavel.
- Fornecedores: cadastro de fornecedor no produto, edicao em lote de fornecedores e despesa do caixa passaram a usar autocomplete/cadastro rapido via `FornecedorSelector`.
- Produtos: filtros de categoria e marca migraram para `AutocompleteSelect`, mantendo seta de abertura e busca digitavel; o filtro de fornecedor segue com `FornecedorSelector`.
- Produtos: opcao "Persistir filtros" agora salva busca, categoria, marca, fornecedor, status, estoque baixo, promocao, pais/variacoes, pagina e itens por pagina.
- Backend/Produtos: primeira fatia de reducao de `produtos_routes.py` extraiu helpers de listagem para `app/produtos/listagem.py`, com testes unitarios para flags, ordenacao e enriquecimento de kits.
- Backend/Produtos: fatia de 2026-06-07 extraiu helpers puros de codigo de barras/EAN para `app/produtos/codigo_barras.py`, com teste unitario dedicado e comportamento das rotas preservado.
- Backend/Produtos: fatia de 2026-06-07 extraiu os schemas Pydantic de produtos para `app/produtos/schemas.py`, removendo cerca de 700 linhas do router sem alterar contratos de API.
- Backend/Produtos: fatia de 2026-06-07 extraiu normalizacoes centrais, validadores de tenant/entidades e helpers de relatorio para `app/produtos/core.py`, `app/produtos/validators.py` e `app/produtos/relatorios.py`, com testes unitarios dedicados e reducao adicional do router.
- Backend/Produtos: fatia de 2026-06-08 extraiu helpers puros de palavras de busca e tipos base de listagem para `app/produtos/listagem.py`, removendo duplicacao entre listagem, vendaveis e relatorios sem alterar filtros.
- Backend/Produtos: fatia de 2026-06-08 extraiu a resolucao/aplicacao de filtros de fornecedor e grupo para `app/produtos/listagem.py`, preservando a diferenca entre busca do tenant atual e tenants parceiros.
- Backend/Produtos: fatia de 2026-06-08 extraiu normalizacao de paginacao para `app/produtos/listagem.py`, reaproveitando page/page_size/offset em produtos vendaveis e relatorios paginados.
- Backend/Produtos: fatia de 2026-06-08 extraiu helpers de vinculo de fornecedores para `app/produtos/fornecedores.py`, cobrindo fornecedor principal unico e operacoes em lote com teste unitario dedicado.
- Backend/Produtos: fatia de 2026-06-08 extraiu consumo FIFO de lotes para `app/produtos/lotes.py`, preservando o payload legado da rota de saida e adicionando testes unitarios para consumo parcial, consumo em multiplos lotes e quantidade zero.
- Backend/Produtos: fatia de 2026-06-08 extraiu helpers de hierarquia de categorias para `app/produtos/categorias.py`, preservando os decorators das rotas no router principal e adicionando testes unitarios para nivel, ciclo e arvore.
- Backend/Produtos: fatia de 2026-06-08 extraiu a montagem de load options e filtros basicos de `listar_produtos` e `listar_produtos_vendaveis` para `app/produtos/listagem.py`, preservando imagens/lotes opcionais e reduzindo o router para `4677` linhas.
- Backend/Notas de entrada: fatia de 2026-06-07 extraiu helpers fiscais/XML e regras de conferencia/lotes para `app/notas_entrada/fiscal.py` e `app/notas_entrada/conferencia.py`, mantendo imports compativeis no router e testes focados para custo efetivo, pack, conferencia, validade e lotes.
- Backend/Notas de entrada: fatia de 2026-06-07 extraiu helpers de produto, SKU, EAN/codigo de barras e vinculo automatico para `app/notas_entrada/produtos.py`, mantendo os nomes reexportados pelo router e testes dedicados para normalizacao/divergencia de codigos fiscais.
- Backend/Notas de entrada: fatia de 2026-06-07 extraiu helpers de fornecedor automatico para `app/notas_entrada/fornecedores.py`, adicionou testes de prefixo/criacao e corrigiu o upload em lote para inicializar usuario/tenant e gravar `tenant_id` em notas e itens.
- Backend/Notas de entrada: fatia de 2026-06-07 moveu a sugestao de SKU/produto para `app/notas_entrada/produtos.py`, reduzindo mais o router e mantendo testes de SKU apontando para o modulo dedicado.
- Backend/Notas de entrada: fatia de 2026-06-07 moveu a criacao de contas a pagar da NF para `app/notas_entrada/financeiro.py`, mantendo contrato de classificacao aprendida e teste unitario para duplicatas parceladas.
- Backend/Notas de entrada: fatia de 2026-06-08 moveu o parser XML NF-e para `app/notas_entrada/xml_parser.py`, preservando o import `parse_nfe_xml` no router para compatibilidade com rotas e testes existentes.
- Backend/Notas de entrada: fatia de 2026-06-08 moveu os schemas Pydantic para `app/notas_entrada/schemas.py`, mantendo os mesmos nomes importados pelo router e reduzindo acoplamento entre contratos e handlers.
- Backend/Notas de entrada: fatia de 2026-06-08 moveu a importacao automatica de docs SEFAZ para `app/notas_entrada/sefaz_importer.py`, mantendo `importar_docs_sefaz` reexportado pelo router para nao quebrar chamadas existentes.
- Backend/Notas de entrada: fatia de 2026-06-08 moveu rotas de rateio da nota e do item para `app/notas_entrada/rateio_routes.py`, mantendo o prefixo publico pelo `include_router` do router principal.
- Backend/Notas de entrada: fatia de 2026-06-08 moveu rotas de vinculo, desvinculo, sugestao de SKU e criacao de produto por item para `app/notas_entrada/itens_produto_routes.py`, preservando contratos e reduzindo o router principal para `1824` linhas.
- Testes/fixtures: a base legada de testes agora roda sem PostgreSQL local usando SQLite em memoria, reexporta `tenant_factory`, `user_factory`, `auth_headers` e `client`, e cria usuarios com bcrypt/vinculo `UserTenant` para validar o fluxo multitenant atual.
- Produtos/Estoque: tela de movimentacoes voltou a exibir "Lancar granel" para produtos elegiveis e manteve balanco manual permitido em produto granel para ajuste de inventario.
- Pessoas: listagem ganhou selecao em massa e fluxo de fusao de 2 cadastros, transferindo vinculos/historico para o principal e inativando o duplicado.
- Pessoas `/clientes`: a barra de busca e acoes voltou para `Panel`, `ActionButton` e `IconActionButton`; o botao `Novo` usa `intent=create` (verde/emerald) e `Importar Excel` ficou como acao secundaria neutra.
- Financeiro/Vendas: a tabela principal da lista de vendas foi extraida para `VendasFinanceiroListaTable` e passou a consumir `DataTable`, `MoneyCell`, `NumberCell` e `StatusBadge`.
- Financeiro/Vendas: a tabela "Vendas por data" do resumo foi extraida para `VendasPorDataTable`, mantendo badges de dia, valores zerados como traco e totalizacao no componente.
- Financeiro/Vendas: as tabelas "Formas de recebimento" e "Funcionario" foram extraidas para componentes dedicados com `DataTable`, mantendo totalizacao local e celulas monetarias padronizadas.
- Financeiro/Vendas: as tabelas agregadas de "Tipo" e "Grupo de produto" passaram a usar `VendasResumoAgregadoTable`, preparando o mesmo padrao para outros resumos.
- Financeiro/Vendas: as comparacoes de periodo por forma de pagamento, grupo de produto e funcionario passaram para `VendasComparativoPeriodoTable`, padronizando variacao, valores e estados vazios.
- Financeiro/Vendas: a aba de produtos/servicos detalhados passou a usar `ProdutosServicosDetalhadosTable`, mantendo hierarquia de categoria, subcategoria, produto e total geral.
- Financeiro/Vendas: a tabela de itens promocionais foi extraida para `ProdutosPromocionaisTable`, reaproveitando celulas numericas e monetarias globais.
- Financeiro/Vendas: o ranking de top produtos por lucro foi extraido para `TopProdutosLucroTable`, padronizando ranking, margem e valores.
- Financeiro/Vendas: acoes superiores de relatorios/exportacoes foram alinhadas em altura e densidade, mantendo cor compacta por referencia sem competir com a tela.
- Estoque/Transferencia Parceiro: helpers de documento/cupom, seletor de colunas, modal de documento e cards/badges locais foram extraidos para modulos dedicados, com teste unitario para as regras de colunas, cupom e busca por codigo.
- Estoque/Transferencia Parceiro: cupom de impressao, cabecalho/abas, formulario de lancamento e filtros/resumo do historico foram extraidos para componentes dedicados, reduzindo o arquivo principal e mantendo as regras de estado e APIs concentradas na pagina.
- Estoque/Transferencia Parceiro: resultados do historico, cards de transferencia, tabela de itens e painel de baixa/compensacao foram isolados em `HistoricoTransferenciaResults`, deixando a pagina principal focada em estado, efeitos e chamadas de backend.
- Estoque/Transferencia Parceiro: factories de estado, normalizacao de itens, payloads de transferencia e compensacoes de baixa foram movidos para helpers testados em `transferenciaParceiroUtils`, reduzindo logica pura dentro do componente React.
- Financeiro/Fluxo de Caixa: cabecalho passou para `PageHeader` e o Chat IA existente foi conectado ao modal padrao.
- Financeiro/Contas: estados de carregamento de contas a pagar/receber passaram para `LoadingState` global.
- Financeiro/DRE e Fluxo de Caixa: carregamentos iniciais passaram para `LoadingState`; botoes PDF/Excel da DRE ganharam referencia visual compacta no padrao de acoes.

Proxima varredura recomendada:

- Criar trilha continua de responsividade do ERP no celular/app: revisar tela por tela em largura mobile, priorizando fluxos diarios de PDV, Produtos, Pessoas/Pets, Financeiro, Veterinario, Estoque e Ops.
- Finalizar PDV cliente/produtos/modais.
- Depois aplicar o mesmo padrao em Financeiro/Vendas, DRE, Produtos, Pessoas, Pets, Veterinario, Banho & Tosa, Campanhas e demais modulos.

## Escopo global

O trabalho vale para todos os modulos:

- Dashboard e Dashboard Gerencial.
- Pessoas/clientes e pets.
- Veterinario.
- Banho & Tosa.
- Produtos, estoque, validade, balanco, movimentacoes e Bling.
- Lembretes.
- Calculadora de racao.
- PDV/vendas.
- Campanhas.
- E-commerce/app.
- Pedidos Bling e monitor Bling.
- NF de saida e NF de entrada.
- Compras.
- Financeiro/contabil: vendas, DRE, fluxo de caixa, contas, conciliacoes.
- Comissoes.
- Entregas.
- Cadastros.
- RH.
- IA.
- Administracao, usuarios, roles e configuracoes.
- Telas publicas como rastreio e e-commerce.
- Central MLProHub Ops: saude tecnica, erros por tenant, watchdog, deploys, alertas e suporte interno.

## Principios obrigatorios

1. Antes de criar componente novo, procurar se ja existe algo em `frontend/src/components` ou `frontend/src/components/ui`.
2. O componente deve nascer transversal quando o padrao aparece em mais de uma tela.
3. Cor representa intencao da acao, nao gosto do modulo.
4. Cards, botoes, filtros e tabelas devem ter densidade operacional, sem visual de landing page.
5. Regras de negocio nao devem depender do caminho da tela. Se a regra existe, deve valer ao criar, editar, reabrir, cancelar, reprocessar ou importar.
6. Toda regra financeira/campanha/comissao/estoque/cupom deve ser rastreavel por extrato, log, ledger ou evento.
7. Refatorar em fatias pequenas, com comportamento externo preservado.
8. Nao misturar melhoria visual, regra de negocio e reorganizacao grande no mesmo pacote quando isso aumentar risco.

## Refatoracao de arquivos grandes

Arquivos grandes devem virar uma frente explicita do roadmap. A regra pratica:

- Acima de 700 linhas: arquivo em atencao, mapear responsabilidades internas.
- Acima de 1000 linhas: prioridade de refatoracao por fatias.
- Acima de 1500 linhas: critico, separar em componentes/servicos/hooks antes de novas funcionalidades grandes.

Regras para refatorar sem quebrar producao:

- Nao misturar mudanca visual, regra de negocio e extracao grande no mesmo pacote.
- Primeiro extrair componentes/servicos puros mantendo comportamento igual.
- Depois mover regras repetidas para helpers/servicos centrais.
- Cada extracao deve ter build/teste e, quando possivel, validacao visual da tela afetada.
- Arquivos de rota backend devem ser quebrados por dominio, schema, service e router.
- Arquivos frontend devem ser quebrados por `Page`, `Header`, `Filters`, `Table`, `Modal`, `Card`, `hooks` e `utils`.

Maiores arquivos mapeados em 2026-05-04:

Inventario atualizado em 2026-06-07, excluindo testes e migracoes Alembic da fila operacional:

- 112 arquivos de aplicacao acima de 700 linhas, em atencao.
- 54 arquivos de aplicacao acima de 1000 linhas, prioridade de refatoracao.
- 22 arquivos de aplicacao acima de 1500 linhas, criticidade alta.
- 12 arquivos de aplicacao acima de 2000 linhas.
- 4 arquivos de aplicacao acima de 3000 linhas.

Top criticos ainda pendentes no inventario de 2026-06-07:

| Linhas | Arquivo | Prioridade |
| --- | --- | --- |
| 4677 | `backend/app/produtos_routes.py` | Critico |
| 1824 | `backend/app/notas_entrada_routes.py` | Em reducao por fatias |
| 3576 | `backend/app/pedidos_compra_routes.py` | Critico |
| 3459 | `backend/app/campaigns/routes.py` | Critico |
| 3107 | `backend/app/vendas/service.py` | Critico |
| 2863 | `backend/app/clientes_routes.py` | Critico |
| 2599 | `backend/app/bling_sync_routes.py` | Critico |
| 2552 | `backend/app/services/tenant_onboarding_service.py` | Critico |
| 2374 | `backend/app/nfe_routes.py` | Critico |
| 2239 | `backend/app/estoque_transferencia_parceiro_routes.py` | Critico |
| 2077 | `backend/app/contas_pagar_routes.py` | Critico |
| 2067 | `backend/app/vendas_routes.py` | Critico |
| 1969 | `backend/app/routes/app_mobile_routes.py` | Critico |
| 1816 | `backend/app/dashboard_routes.py` | Critico |
| removido | `backend/app/stone_routes.py` | Integração Stone online removida na frente 1.5 |
| 1766 | `backend/app/integracao_bling_pedido_routes.py` | Critico |
| 1752 | `backend/app/services/bling_flow_monitor_service.py` | Critico |
| 1643 | `backend/app/dre_canais_routes.py` | Critico |
| 1632 | `frontend/src/components/ContasPagar.jsx` | Critico |
| 1604 | `backend/app/api/endpoints/rotas_entrega.py` | Critico |
| 1560 | `backend/app/conciliacao_services.py` | Critico |
| 1536 | `backend/app/comissoes_demonstrativo_routes.py` | Critico |

| Linhas | Arquivo | Prioridade |
| --- | --- | --- |
| 4677 | `backend/app/produtos_routes.py` | Critico |
| 621 | `frontend/src/components/EntradaXML.jsx` | Atencao |
| 4064 | `backend/app/estoque_routes.py` | Critico |
| 1980 | `frontend/src/components/VendasFinanceiro.jsx` | Critico |
| 3411 | `backend/app/notas_entrada_routes.py` | Critico |
| 3295 | `backend/app/campaigns/routes.py` | Critico |
| 3225 | `frontend/src/components/PedidosCompra.jsx` | Critico |
| 3036 | `backend/app/vendas/service.py` | Critico |
| 2724 | `backend/app/clientes_routes.py` | Critico |
| 2599 | `backend/app/bling_sync_routes.py` | Critico |
| 2550 | `backend/app/pedidos_compra_routes.py` | Critico |
| 2229 | `frontend/src/pages/ecommerce/EcommerceMVP.jsx` | Critico |
| 2418 | `frontend/src/pages/EstoqueTransferenciaParceiro.jsx` | Critico |
| 2280 | `backend/app/nfe_routes.py` | Critico |
| 2181 | `backend/app/vendas_routes.py` | Critico |
| 1760 | `frontend/src/components/ModalPagamento.jsx` | Critico |
| 1729 | `backend/app/services/bling_flow_monitor_service.py` | Critico |
| 1721 | `backend/app/integracao_bling_pedido_routes.py` | Critico |
| 1670 | `frontend/src/pages/ProdutosForm.jsx` | Critico |
| 1654 | `frontend/src/pages/entregas/RotasEntrega.jsx` | Critico |
| 1641 | `backend/app/dre_canais_routes.py` | Critico |
| 1560 | `backend/app/conciliacao_services.py` | Critico |
| 1490 | `backend/app/api/endpoints/rotas_entrega.py` | Prioridade |
| 1452 | `frontend/src/components/EstoqueBling.jsx` | Prioridade |
| 1424 | `frontend/src/pages/CalculadoraRacao.jsx` | Prioridade |
| 1413 | `frontend/src/components/DashboardAnaliseRacoes.jsx` | Prioridade |
| 844 | `frontend/src/components/MovimentacoesProduto.jsx` | Atencao |
| 1330 | `backend/app/financeiro_routes.py` | Prioridade |
| 1329 | `frontend/src/pages/comissoes/ComissoesListagem.jsx` | Prioridade |
| 1325 | `frontend/src/components/Layout.jsx` | Prioridade |

## Regra visual base

Ver a secao "Design System UI - Sistema Pet" neste arquivo.

Resumo de intencoes:

| Intencao | Uso | Cor |
| --- | --- | --- |
| `create` | Novo, adicionar, cadastrar, incluir, importar quando adiciona dados | verde/emerald |
| `edit` | Editar, salvar alteracao, atualizar cadastro | azul |
| `delete` | Excluir, remover, cancelar destrutivo, estornar destrutivo | vermelho |
| `neutral` | Voltar, fechar, limpar, navegar, imprimir, atualizar lista | slate/cinza |
| `warning` | Reabrir, alerta, pendencia, conflito, acao sensivel reversivel | amber/orange |
| `success` | Pago, concluido, ativo, entregue, reconciliado | emerald |
| `info` | Informativo, sincronizacao, detalhes, ajuda | blue/cyan |

## Padrao de tamanho e alinhamento

### Botoes

- Altura padrao compacta: `h-9` ou equivalente.
- Botao principal de tela: `md`, com icone + texto.
- Botao de linha/tabela: quadrado `h-8 w-8`, com tooltip/title.
- O mesmo verbo deve usar o mesmo intent em todas as telas.
- Evitar botao grande quando a acao e secundaria.

### Cards e dashboards

Problema observado: dashboards e cards de resumo variam muito em altura, largura, cor e densidade, como no PDV.

Padrao desejado:

- `MetricCard`: mesmo padding, borda, raio, titulo, valor e subtitulo.
- Grid com linhas alinhadas: `auto-rows-fr` ou `items-stretch`.
- Cards de uma mesma faixa devem ter mesma altura minima.
- Valor principal sempre no mesmo ponto visual.
- Zero pode virar traco quando o objetivo for destacar numeros relevantes.
- Cores dos cards indicam natureza do dado, nao modulo.

### Paineis

- `Panel`: bloco de trabalho com titulo, subtitulo opcional e acoes.
- Nao usar card dentro de card.
- Evitar paineis muito altos quando a informacao e pequena.

### Tabelas e listas

- `DataTable`: cabecalho, colunas, linhas, empty/loading/error state, acoes e paginacao.
- `MobileList`: versao responsiva de tabela.
- Colunas monetarias e numericas sempre alinhadas a direita.
- Status, canais e tags sempre via componentes de badge.

## Mapa de componentes globais

### Fundacao UI

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `ActionButton` | Botao semantico com intent, tone, size, icone, loading e disabled | Todas as telas |
| `IconActionButton` | Acao compacta de tabela/card com tooltip | Produtos, PDV, financeiro, cadastros, campanhas |
| `ButtonGroup` | Agrupar acoes relacionadas sem desalinhamento | PDV, DRE, vendas, dashboards |
| `PageHeader` | Titulo da pagina, subtitulo, icone, acoes principais | Todos os modulos internos |
| `ModuleTabs` | Abas padronizadas | Veterinario, banho/tosa, campanhas, DRE, produtos |
| `Panel` | Area de trabalho padrao | Formularios, dashboards, relatorios |
| `EmptyState` | Lista vazia com mensagem e acao opcional | Todas as listas |
| `LoadingState` | Carregamento padrao | Todas as telas |
| `ErrorState` | Erro padrao com tentar novamente | Todas as telas |

### Formularios

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `FormField` | Label, ajuda, erro, obrigatorio, input/select/textarea | Todos os formularios |
| `FormSection` | Agrupar campos com titulo e descricao curta | Produto, cliente, pet, venda, configuracoes |
| `SearchInput` | Campo de busca com icone, limpar e loading | Produtos, pessoas, PDV, financeiro |
| `FilterBar` | Filtros horizontais/empilhados responsivos | Produtos, vendas, campanhas, entregas, financeiro |
| `DateRangeFilter` | Periodos rapidos + personalizado | Financeiro, campanhas, entregas, relatorios |
| `MoneyInput` | Moeda BR com mascara | PDV, financeiro, produtos, comissoes |
| `PercentInput` | Percentual consistente | Produtos, margem, campanhas, comissoes |
| `QuantityInput` | Stepper de quantidade | PDV, compras, estoque |
| `SafeMarkdownField` | Texto rico seguro com editar/previa | Produtos, e-commerce, app, mensagens |

### Entidades recorrentes

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `PessoaSelector` | Buscar/selecionar cliente/tutor/pessoa | PDV, financeiro, campanhas, veterinario, banho/tosa |
| `CustomerIdentity` | Exibir cliente com nome/codigo copiaveis | PDV, vendas, financeiro, NF, entregas, comissoes |
| `PetIdentity` | Exibir pet com nome/codigo copiaveis | Banho & Tosa, veterinario, PDV, lembretes, relatorios |
| `TutorPetSelector` | Selecionar tutor + pet + novo pet | Veterinario, banho/tosa, vacinas, internacoes, exames, calculadoras |
| `PetSelector` | Selecionar pet quando tutor ja esta definido | PDV item pet, campanhas pet, app/vet |
| `ProdutoSelector` | Buscar produto/servico/SKU/codigo de barras | PDV, compras, NF, estoque, kits, campanhas |
| `FornecedorSelector` | Buscar fornecedor | Produtos, compras, NF entrada |
| `FornecedorIdentity` | Exibir fornecedor com nome/documento/codigo copiaveis | Produtos, compras, contas a pagar, conciliacao, NF entrada |
| `FuncionarioSelector` | Buscar funcionario/vendedor/entregador/veterinario | PDV, comissoes, entregas, RH, veterinario |
| `ContaBancariaSelector` | Selecionar conta | Financeiro, caixa, conciliacao |
| `FormaPagamentoSelector` | Selecionar forma de pagamento | PDV, financeiro, contas, configuracoes |

### Dados, status e badges

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `MoneyCell` | Valor em BRL, com `zeroAsDash` | Vendas, DRE, PDV, relatorios, produtos |
| `NumberCell` | Numero alinhado e com traco opcional | Dashboards, relatorios, estoque |
| `PercentCell` | Percentual padrao | Margem, DRE, campanhas, comissoes |
| `StatusBadge` | Status semantico | Venda, pedido, NF, campanha, pet, produto, entrega |
| `ChannelBadges` | App/E-commerce/PDV, sem exibir desligados | Produtos, campanhas, vendas |
| `StockBadge` | Estoque baixo/zerado/ok/reservado | Produtos, PDV, compras |
| `PaymentStatusBadge` | Pago/aberto/parcial/cancelado | PDV, financeiro, contas |
| `DueDateBadge` | Vencido/vencendo/ok | Contas, validade, campanhas |

### Tabelas, cards e dashboards

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `DataTable` | Tabela padrao desktop | Todas as listagens |
| `MobileList` | Lista mobile equivalente a tabela | Produtos, vendas, campanhas, entregas |
| `ColumnSelector` | Mostrar/ocultar colunas | Produtos, vendas, relatorios |
| `PaginationControls` | Paginacao padrao | Todas as listas paginadas |
| `MetricCard` | Card de indicador com altura padronizada | Dashboards, PDV, financeiro, campanhas |
| `MetricGrid` | Grade alinhada de cards | PDV, DRE, Dashboard, entregas |
| `SummaryStrip` | Faixa compacta de indicadores | Vendas, PDV, campanhas |
| `InfoCard` | Card de informacao nao numerica | Cliente, pet, produto, ajuda |
| `EntityCard` | Card de pessoa/produto/pet com campos alinhados | Pessoas, pets, produtos, campanhas |

### Modais e fluxos

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `AppModal` | Modal padrao com header/body/footer | Todas as telas |
| `ConfirmDialog` | Confirmacao destrutiva/sensivel | Excluir, cancelar, estornar |
| `Drawer` | Painel lateral de detalhes | Vendas recentes, analise, cliente, produto |
| `WizardSteps` | Passos de fluxo | Consulta vet, importacoes, cadastro cliente |
| `InlineAlert` | Aviso dentro da tela | PDV, DRE, campanhas, estoque |
| `ToastPattern` | Mensagem de sucesso/erro consistente | Sistema inteiro |

### Conteudo rico seguro

| Componente | Objetivo | Onde usar |
| --- | --- | --- |
| `SafeMarkdown` | Renderizar Markdown sem HTML cru | Produtos, mensagens, ajuda, app/e-commerce |
| `MarkdownPreview` | Previa de texto editavel | Produtos, campanhas, mensagens |
| `RichTextSanitizer` | Limpar HTML legado de ERP/Bling | Produtos, descricoes importadas |

## Mapa por entidade

### Pessoas/clientes/tutores

Telas provaveis:

- Clientes/pessoas.
- PDV.
- Financeiro vendas e historico por cliente.
- Campanhas.
- Veterinario.
- Banho & Tosa.
- Contas a receber.
- Entregas.

Padronizar:

- Busca, selecao, card resumido, link para detalhes, telefone/documento, status.
- Acoes: novo cliente, editar, ver historico, selecionar.

### Pets

Telas provaveis:

- Pets.
- Pet detalhes.
- Veterinario.
- Banho & Tosa.
- Calculadora de racao.
- PDV quando item/venda exige pet.
- Campanhas de aniversario de pet.

Padronizar:

- `TutorPetSelector`.
- `PetInfoRow` com nome, especie, raca, sexo, idade, codigo.
- Cards de pet com campos sempre alinhados, mesmo quando vazios.
- Botao `Novo pet` sempre `create`.

### Produtos/servicos

Telas provaveis:

- Produtos.
- Produto novo/editar.
- PDV.
- Compras.
- Entrada XML/NF.
- Estoque.
- Kits/variacoes.
- E-commerce/app.
- Calculadora de racao.
- Alertas de racao/IA.

Padronizar:

- `ProdutoSelector`.
- `ChannelBadges`.
- `StockBadge`.
- `MoneyCell`, `PercentCell`, `QuantityInput`.
- `SafeMarkdownField` para descricoes.

### Vendas/caixa/financeiro

Telas provaveis:

- PDV.
- Meus caixas.
- Financeiro/vendas.
- DRE.
- Fluxo de caixa.
- Contas a pagar/receber.
- Conciliacao.
- Comissoes.
- Campanhas quando envolve cupom/cashback.

Padronizar:

- `PaymentStatusBadge`.
- `MoneyCell` com `zeroAsDash`.
- `DateRangeFilter`.
- `MetricGrid`.
- `DataTable`.
- Regras centrais para comissao, cupom, cashback, imposto e rentabilidade.

### Campanhas/cupons/creditos

Telas provaveis:

- Campanhas.
- PDV.
- Cliente.
- App/e-commerce.
- Financeiro/vendas.

Padronizar:

- Extrato/ledger.
- `StatusBadge` para cupom.
- `ChannelBadges`.
- `MetricCard`.
- Reprocessamento idempotente.

### Entregas

Telas provaveis:

- Entregas abertas.
- Rotas.
- Historico.
- Financeiro entregas.
- PDV com taxa/entrega.

Padronizar:

- Status de entrega.
- Cards de rota.
- Tabelas com motorista/cliente/valor/status.
- Mapas e paineis com mesma estrutura.

## Mapa por modulo

| Modulo | Componentes prioritarios |
| --- | --- |
| Dashboard/Dashboard Gerencial | `PageHeader`, `MetricGrid`, `MetricCard`, `Panel`, `DataTable` |
| Pessoas/clientes | `PessoaSelector`, `EntityCard`, `DataTable`, `StatusBadge`, `ActionButton` |
| Pets | `TutorPetSelector`, `PetInfoRow`, `EntityCard`, `ActionButton`, `EmptyState` |
| Veterinario | `TutorPetSelector`, `ModuleTabs`, `FormField`, `Panel`, `WizardSteps`, `MetricCard` |
| Banho & Tosa | `TutorPetSelector`, `ModuleTabs`, `DataTable`, `MetricGrid`, `StatusBadge` |
| Produtos/Estoque | `ProdutoSelector`, `DataTable`, `ChannelBadges`, `StockBadge`, `SafeMarkdown` |
| Calculadora de Racao | `PetSelector`, `ProdutoSelector`, `Panel`, `Dropdown/Combobox`, `MetricCard` |
| PDV | `PessoaSelector`, `ProdutoSelector`, `PetSelector`, `ActionButton`, `MetricGrid`, `Drawer`, `StatusBadge` |
| Campanhas | `PessoaSelector`, `DataTable`, `MetricGrid`, `StatusBadge`, `Statement/Extrato` |
| E-commerce/App | `SafeMarkdown`, `ChannelBadges`, `ProdutoSelector`, `StatusBadge` |
| Compras/NF Entrada | `FornecedorSelector`, `ProdutoSelector`, `DataTable`, `UploadArea`, `ConfirmDialog`, `PendenciaFornecedorPanel`, `ExportActionButton` |
| NF Saida | `DataTable`, `StatusBadge`, `ActionButton`, `FilterBar` |
| Financeiro | `DateRangeFilter`, `MetricGrid`, `MoneyCell`, `DataTable`, `PaymentStatusBadge` |
| Comissoes | `FuncionarioSelector`, `MoneyCell`, `StatusBadge`, `DataTable`, `Statement/Extrato` |
| Entregas | `FuncionarioSelector`, `StatusBadge`, `MetricGrid`, `DataTable`, `MapPanel` |
| Cadastros | `DataTable`, `FormField`, `AppModal`, `ActionButton`, `ConfirmDialog` |
| RH | `FuncionarioSelector`, `DataTable`, `StatusBadge`, `FormField` |
| IA | `Panel`, `MetricCard`, `MarkdownPreview`, `DataTable`, `InlineAlert` |
| Administracao/Configuracoes | `FormSection`, `FormField`, `ActionButton`, `DataTable`, `StatusBadge` |

## Markdown seguro

### Problema

Descricoes de produtos e textos vindos de ERP/Bling podem vir com HTML, tags ou codigos de formatacao. Renderizar HTML puro resolve aparencia, mas abre risco de seguranca.

### Direcao

Usar Markdown como formato principal para conteudo rico editavel pelo usuario.

### Padrao

- `SafeMarkdown`: renderizacao segura, HTML desligado.
- `SafeMarkdownField`: textarea + previa.
- `normalizeMarkdownContent`: limpar HTML legado antes de salvar/exibir.
- Evitar `dangerouslySetInnerHTML` fora de componentes controlados.

Primeiros usos:

- Produtos.
- App/e-commerce.
- Mensagens de campanhas.
- Central de ajuda.
- Observacoes padronizadas quando fizer sentido.

## Pendencias rastreaveis

### Compras e NF de entrada

Quando a conferencia de uma NF identifica falta, avaria ou divergencia que depende do fornecedor, o sistema deve transformar isso em uma pendencia operacional rastreavel.

Padrao esperado:

- origem vinculada a NF de entrada, pedido de compra e fornecedor;
- itens divergentes congelados no momento da criacao da pendencia;
- PDF informativo com resumo, itens, quantidades e valores estimados;
- mensagem sugerida para fornecedor, editavel antes do envio;
- registro de envio ou envio automatico com anexo quando SMTP estiver configurado;
- historico com data, usuario, observacao, mudanca de status e resolucao;
- tela propria em Compras > Pendencias para acompanhar prazo, retorno e fechamento.

Esse mesmo modelo pode ser reaproveitado depois para outras pendencias operacionais: estoque, entrega, comissao, financeiro e integracoes.

## Regras de negocio centrais auditaveis

Esta frente vale para todo o sistema, nao so campanhas/comissoes.

### Nome pratico

**Regras centrais auditaveis**.

### Problema

Algumas regras podem depender do caminho executado.

Exemplos:

- Parametro X carimbos = 1 cupom deve valer sempre, inclusive apos cancelamento, restauracao ou reprocessamento.
- Se uma venda tem comissao marcada/configurada, a comissao deve existir mesmo se foi incluida depois, reaberta ou ajustada.
- Se estoque muda por venda, devolucao, NF, ajuste ou kit, o saldo deve reconciliar pela mesma regra.
- Se uma venda muda de status, financeiro, cupom, comissao, caixa, DRE e estoque devem ser atualizados pelo mesmo mecanismo central.

### Padrao recomendado

Para cada dominio sensivel:

1. `sync_<dominio>_for_<entidade>()`
2. `reconcile_<dominio>()`
3. ledger/extrato com creditos, debitos, reversoes e origem
4. testes de dominio cobrindo criar, editar, cancelar, reabrir e reprocessar
5. rotas e telas chamando o mesmo service

### Dominios prioritarios

| Dominio | Regra central |
| --- | --- |
| Campanhas/carimbos/cupons/cashback | Credito, debito, conversao, anulacao, saldo negativo |
| Comissoes | Gerar, recalcular, estornar, reabrir, auditar |
| Estoque | Venda, devolucao, compra, NF, kit, reserva, ajuste |
| Financeiro/caixa | Baixa, reabertura, cancelamento, contas, conciliacao |
| DRE/rentabilidade | Snapshot, rateio, imposto, custo, comissao |
| Entregas | Taxa, status, financeiro do entregador |
| NF/Bling | Importacao, vinculo, conciliacao, idempotencia |

## Arquivos grandes e risco

### Frontend mais criticos

| Arquivo | Linhas aprox. | Risco |
| --- | ---: | --- |
| `frontend/src/components/EntradaXML.jsx` | 621 | Medio/alto |
| `frontend/src/components/VendasFinanceiro.jsx` | 1980 | Alto |
| `frontend/src/components/PedidosCompra.jsx` | 3225 | Alto |
| `frontend/src/pages/ecommerce/EcommerceMVP.jsx` | 2229 | Alto |
| `frontend/src/pages/EstoqueTransferenciaParceiro.jsx` | 2418 | Alto |
| `frontend/src/components/ModalPagamento.jsx` | 1760 | Medio/alto |
| `frontend/src/pages/ProdutosForm.jsx` | 1670 | Medio/alto |
| `frontend/src/pages/CalculadoraRacao.jsx` | 1424 | Medio |
| `frontend/src/components/Layout.jsx` | 1324 | Alto por ser global |
| `frontend/src/components/DRE.jsx` | 835 | Medio |

### Backend mais criticos

| Arquivo | Linhas aprox. | Risco |
| --- | ---: | --- |
| `backend/app/produtos_routes.py` | 4677 | Muito alto |
| `backend/app/estoque_routes.py` | 4064 | Muito alto |
| `backend/app/notas_entrada_routes.py` | 3411 | Alto |
| `backend/app/campaigns/routes.py` | 3295 | Alto |
| `backend/app/vendas/service.py` | 3036 | Muito alto |
| `backend/app/clientes_routes.py` | 2724 | Alto |
| `backend/app/bling_sync_routes.py` | 2599 | Alto |
| `backend/app/pedidos_compra_routes.py` | 2550 | Alto |
| `backend/app/nfe_routes.py` | 2280 | Alto |
| `backend/app/vendas_routes.py` | 2181 | Alto |

## Como refatorar sem quebrar

1. Primeiro criar componente global com API pequena.
2. Aplicar em uma tela piloto.
3. Validar visual e build.
4. Aplicar em telas irmas.
5. So depois remover duplicacoes antigas.
6. Para regra de negocio, adicionar teste antes ou junto.
7. Para tela grande, extrair primeiro componentes de apresentacao, depois hooks, depois services.

## Sequencia sugerida

### Fase 0 - Inventario e governanca

- Criar checklist de componentes globais.
- Marcar cada tela com: botoes, cards, filtros, tabelas, seletores, modais, regras sensiveis.
- Atualizar a secao "Design System UI - Sistema Pet" deste arquivo com tamanhos oficiais de botao/card/tabela.

### Fase 1 - Fundacao visual global

- `ActionButton`, `IconActionButton`, `PageHeader`, `Panel`.
- `MetricCard`, `MetricGrid`.
- `StatusBadge`, `ChannelBadges`, `MoneyCell`, `NumberCell`.
- `EmptyState`, `LoadingState`, `ErrorState`.

### Fase 2 - Seletores de entidades

- `PessoaSelector`.
- `TutorPetSelector` consolidado.
- `ProdutoSelector`.
- `FornecedorSelector`.
- `FuncionarioSelector`.
- `FormaPagamentoSelector`.

### Fase 3 - Tabelas, filtros e modais

- `DataTable`.
- `MobileList`.
- `FilterBar`.
- `DateRangeFilter`.
- `AppModal`.
- `ConfirmDialog`.
- `Drawer`.

### Fase 4 - Aplicacao por modulo

Ordem sugerida por impacto e repeticao:

1. PDV, porque concentra pessoa, produto, pet, cards, botoes, status e drawer.
2. Financeiro/vendas/DRE, porque concentra cards, tabelas, periodo e dinheiro.
3. Pessoas e pets, porque viram fonte para outros fluxos.
4. Produtos/estoque/compras/NF, porque compartilham produto, fornecedor, estoque e canal.
5. Veterinario e banho/tosa, porque ja tem parte do `TutorPetSelector`.
6. Campanhas e comissoes, porque precisam de padrao visual e regra central auditavel.
7. Entregas, e-commerce/app, cadastros, RH, IA, configuracoes.

### Fase 5 - Regras centrais auditaveis

- Campanhas/carimbos/cupons/cashback.
- Comissoes.
- Estoque.
- Financeiro/caixa.
- DRE/rentabilidade.
- NF/Bling.

### Fase 6 - Refatoracao dos arquivos grandes

- Atacar um arquivo grande por vez.
- Extrair componentes sem mudar comportamento.
- Criar testes nos dominios sensiveis.

## Definition of Done para padronizacao

Uma melhoria so esta pronta quando:

- usa componente existente ou justifica componente novo;
- aplica `ActionButton`/`IconActionButton` quando for acao;
- usa `MetricCard`/`MetricGrid` em indicadores;
- usa `DataTable`/`MobileList` em listagens novas ou refatoradas;
- usa seletor de entidade quando selecionar pessoa, produto, pet, fornecedor ou funcionario;
- segue a secao "Design System UI - Sistema Pet" deste arquivo;
- mantem alinhamento e tamanho consistente no desktop e mobile;
- regra de negocio fica em service/domain, nao so na tela;
- caso sensivel tem teste ou roteiro de validacao;
- tem rastreabilidade quando envolve dinheiro, campanha, estoque, cupom, NF ou comissao;
- build/check passam antes de deploy.

## Situacao atual da primeira fatia

Ja foi iniciada uma primeira aplicacao em Produtos:

- `ActionButton`.
- `ChannelBadges`.
- `MoneyCell`.
- `SafeMarkdown`.
- limpeza de HTML legado em descricao.

Isso deve ser tratado como **piloto de fundacao**, nao como prioridade exclusiva de Produtos.

## Inventario operacional do frontend - 2026-05-02

Este inventario foi extraido do codigo atual em `frontend/src`, principalmente `App.jsx`, `pages` e `components`. Ele serve como mapa de execucao, nao como documentacao estatica definitiva.

### Volume por area

| Area | Arquivos aproximados | Leitura |
| --- | ---: | --- |
| `pages/veterinario` | 265 | Modulo mais componentizado; bom candidato para padronizacao incremental por subpasta |
| `components/campanhas` | 64 | Ja tem decomposicao, mas precisa consolidar tabelas, badges, extrato e regras visuais |
| `pages/banhoTosa` | 49 | Precisa reaproveitar seletores e paineis padrao |
| `components/pdv` | 26 | Tela piloto transversal; concentra pessoa, pet, produto, financeiro, campanhas e caixa |
| `components/produto` | 22 | Produto novo/editar ja esta separado em secoes; bom para `FormField`, `SafeMarkdownField` e `ChannelBadges` |
| `components/clientes` | 15 | Deve alimentar `PessoaSelector`, `EntityCard` e padrao de wizard/modal |
| `components/produtos` | 12 | Ja iniciou tabela/listagem padronizada |
| `components/ui` | 11 | Fundacao existe, mas ainda precisa ganhar `DataTable`, `FilterBar`, `AppModal`, `EmptyState`, `NumberCell` |

### Hotspots de padronizacao visual

Estes arquivos combinam muito botao, modal, card, filtro, tabela ou dashboard. Sao bons alvos para migracao para componentes globais porque cada ajuste elimina muita repeticao.

| Prioridade | Arquivo | Motivo principal |
| --- | --- | --- |
| 1 | `frontend/src/components/VendasFinanceiro.jsx` | Financeiro, filtros, cards, tabelas, dinheiro, periodo e status |
| 2 | `frontend/src/components/PedidosCompra.jsx` | Compras, produtos, fornecedor, acoes, modais e tabelas |
| 3 | `frontend/src/components/EntradaXML.jsx` | Arquivo muito grande, NF/itens/produtos, modais e conciliacao |
| 4 | `frontend/src/pages/EstoqueTransferenciaParceiro.jsx` | Estoque, produtos, filtros, cards e acoes |
| 5 | `frontend/src/pages/ecommerce/EcommerceMVP.jsx` | Produto/canal/markdown/aparencia e telas publicas |
| 6 | `frontend/src/pages/ProdutosValidadeProxima.jsx` | Produtos, alertas, tabelas e status |
| 7 | `frontend/src/components/ContasPagar.jsx` e `ContasReceber.jsx` | Financeiro, dinheiro, vencimento, filtros e modais |
| 8 | `frontend/src/components/DRE.jsx` | Indicadores, periodo, dinheiro, tabelas e exportacoes |
| 9 | `frontend/src/pages/GerenciamentoPets.jsx` | Cards desalinhados, entidade pet e acoes repetidas |
| 10 | `frontend/src/pages/comissoes/ComissoesListagem.jsx` | Regras sensiveis, dinheiro, funcionario, tabelas e status |

### Padroes repetidos encontrados

| Padrao textual no codigo | Ocorrencias aproximadas | Direcao |
| --- | ---: | --- |
| `button` | 4206 | Migrar gradualmente para `ActionButton` e `IconActionButton` |
| `Modal` | 1658 | Criar `AppModal` e `ConfirmDialog` antes de mexer em todos |
| `Filtro/Filtros` | 2638 | Criar `FilterBar`, `DateRangeFilter`, `SearchInput` |
| `toast` | 830 | Criar padrao de mensagens por tipo de operacao |
| `Card` | 595 | Consolidar `Panel`, `MetricCard`, `EntityCard`, `InfoCard` |
| `confirm` | 555 | Padronizar confirmacao destrutiva/sensivel |
| `Badge` | 341 | Expandir `StatusBadge` e badges especificos |
| `<select` | 297 | Criar `FormField`/`SelectField` e depois `Combobox` |
| `<table` | 138 | Criar `DataTable` antes de refatorar listas grandes |
| `dangerouslySetInnerHTML` | 1 | Manter excecao monitorada; preferir `SafeMarkdown` |

### Adoção dos componentes globais

| Componente | Referencias aproximadas | Estado |
| --- | ---: | --- |
| `ActionButton` | 90 | Ja util; precisa virar padrao obrigatorio em novas telas/refatores |
| `Panel` | 85 | Ja entrou no PDV; precisa migrar cards soltos |
| `StatusBadge` | 47 | Bom inicio, faltam mapeamentos por dominio |
| `MetricCard` | 30 | Ainda pouco frente aos dashboards existentes |
| `IconActionButton` | 10 | Prioritario para acoes de tabela |
| `MoneyCell` | 6 | Deve ir para financeiro, DRE, vendas e relatorios |
| `ChannelBadges` | 5 | Deve ir para produtos, campanhas, app/e-commerce |
| `SafeMarkdown` | 3 | Deve ir para produtos, app/e-commerce, campanhas e ajuda |
| `TutorPetSelector` | 6 | Ja existe; deve ser padrao para vet, banho/tosa, vacinas, internacoes e calculadoras |
| `PageHeader` | 3 | Prioritario para uniformizar telas |
| `MetricGrid` | 1 | Prioritario para dashboards/resumos |

### Rotas e modulos que precisam entrar no ciclo

| Grupo | Rotas principais | Componentes base obrigatorios |
| --- | --- | --- |
| Publico/e-commerce | `/landing`, `/ecommerce`, `/:tenantId`, `/rastreio/:token` | `SafeMarkdown`, `ChannelBadges`, `StatusBadge`, `Panel` |
| Dashboard | `/dashboard`, `/dashboard-gerencial` | `PageHeader`, `MetricGrid`, `MetricCard`, `Panel` |
| Pessoas/clientes | `/clientes`, `/clientes/:id/financeiro`, `/clientes/:id/timeline` | `PessoaSelector`, `EntityCard`, `DataTable`, `StatusBadge` |
| Pets | `/pets`, `/pets/novo`, `/pets/:id`, `/pets/:id/editar` | `TutorPetSelector`, `PetInfoRow`, `EntityCard`, `ActionButton` |
| Veterinario | `/veterinario/*` | `TutorPetSelector`, `ModuleTabs`, `FormField`, `Panel`, `DataTable` |
| Banho & Tosa | `/banho-tosa/*` | `TutorPetSelector`, `ModuleTabs`, `Panel`, `DataTable`, `StatusBadge` |
| Produtos/estoque | `/produtos/*`, `/estoque/*` | `ProdutoSelector`, `DataTable`, `FilterBar`, `ChannelBadges`, `StockBadge` |
| PDV/caixa | `/pdv`, `/meus-caixas` | `PessoaSelector`, `ProdutoSelector`, `PetSelector`, `ActionButton`, `Panel`, `MetricGrid` |
| Fiscal/Bling/compras | `/notas-fiscais/*`, `/compras/*`, `/vendas/bling-*`, `/produtos/sinc-bling` | `ProdutoSelector`, `FornecedorSelector`, `StatusBadge`, `DataTable`, `ConfirmDialog` |
| Financeiro | `/financeiro/*` | `MoneyCell`, `DateRangeFilter`, `MetricGrid`, `DataTable`, `PaymentStatusBadge` |
| Comissoes | `/comissoes/*` | `FuncionarioSelector`, `MoneyCell`, `StatusBadge`, `DataTable`, extrato/regra central |
| Campanhas | `/campanhas`, `/campanhas/canais` | `PessoaSelector`, `StatusBadge`, `MetricGrid`, `DataTable`, extrato/ledger |
| Entregas | `/entregas/*` | `FuncionarioSelector`, `StatusBadge`, `MetricGrid`, `DataTable`, `MapPanel` |
| Cadastros/RH/Admin | `/cadastros/*`, `/rh/*`, `/admin/*`, `/configuracoes/*` | `PageHeader`, `FormField`, `DataTable`, `AppModal`, `ConfirmDialog` |
| IA/Ajuda | `/ia/*`, `/ajuda` | `Panel`, `SafeMarkdown`, `MetricCard`, `InlineAlert` |

## Onda 1 - Fundacao realmente transversal

Objetivo: parar de resolver cada tela como se fosse unica. Esta onda nao tenta "embelezar tudo"; ela cria blocos pequenos e aplica em telas que mais repetem padrao.

### Componentes a fechar primeiro

| Componente | Por que vem agora | Telas piloto |
| --- | --- | --- |
| `DataTable` | Existem muitas tabelas com cabecalho, empty state, paginacao e acoes repetidas | Produtos, financeiro/vendas, pets |
| `FilterBar` + `SearchInput` | Filtros aparecem em praticamente todos os modulos | Produtos, financeiro/vendas, pets |
| `FormField` + `SelectField` | Muitos formularios e selects soltos | Produto editar, pet, banho/tosa agenda |
| `AppModal` + `ConfirmDialog` | Modais e confirms estao espalhados | Produtos, PDV, campanhas |
| `EntityCard` | Pessoas, pets e produtos precisam de alinhamento consistente | Pets, cliente no PDV, pessoas |
| `NumberCell` + ampliar `MoneyCell` | Zero como traco e alinhamento numerico deve ser padrao | Financeiro/vendas, DRE, produtos |
| `StockBadge` + `PaymentStatusBadge` | Status precisa parar de variar por tela | Produtos, vendas, contas |

### Ordem de aplicacao da Onda 1

1. **Pets**: resolver desalinhamento de cards e criar `EntityCard`/`PetInfoRow`.
2. **Financeiro/Vendas**: aplicar `MoneyCell`, `NumberCell`, `MetricGrid`, `FilterBar` e preparar `DataTable`.
3. **Produtos**: terminar listagem com `DataTable`/`FilterBar` e consolidar `ChannelBadges`.
4. **PDV**: manter como vitrine de interacao compacta e aplicar `EntityCard` no cliente.
5. **Banho & Tosa + Veterinario**: reaproveitar `TutorPetSelector` e padronizar formularios.

### Progresso da Onda 1

- 2026-05-02: criado `EntityCard`/`EntityInfoRow` e aplicado em `/pets`, com campos fixos mesmo vazios, botoes padronizados e card preparado para reuso em pessoas/produtos.
- 2026-05-02: ampliado `MoneyCell` com sinal/zero como traco, criado `NumberCell` e aplicado na consulta de vendas em resumo por data, lista de vendas e itens expandidos.
- 2026-05-02: criado `FilterBar`/`FilterRow`/`FilterAdvanced` e aplicado em `/pets` como primeiro padrao de filtros reutilizaveis.
- 2026-05-03: iniciada a fatia Financeiro/DRE, com `MetricGrid`/`MetricCard` na DRE e `MoneyCell`/`NumberCell`/`StatusBadge`/`ActionButton` aplicados em DRE, contas a pagar e contas a receber.
- 2026-05-03: `FluxoCaixa` entrou na mesma fundacao visual, com cards de resumo via `MetricGrid`/`MetricCard`, valores via `MoneyCell`, botoes via `ActionButton` e status de movimentacao via `StatusBadge`.
- 2026-05-03: `VendasFinanceiro` recebeu primeira fatia da fundacao, com filtros avancados em `FilterBar`, status da lista via `StatusBadge` e totalizadores compactos em `MetricGrid`/`MetricCard`.
- 2026-05-03: criado `DataTable` base para migrar listagens com cabecalho, alinhamento, loading, vazio, clique de linha e linha expandida sem reescrever cada tela.
- 2026-05-03: `ContasPagar` e `ContasReceber` migraram a listagem principal para `DataTable`, mantendo `MoneyCell`, `StatusBadge` e `ActionButton` como padrao financeiro.
- 2026-05-03: `DataTable` ganhou compatibilidade com colunas legadas que renderizam `<th>`/`<td>`, permitindo migrar a listagem desktop de `ProdutosTabelaSection` sem reescrever as colunas existentes.
- 2026-05-03: `ProdutosFiltrosPanel` passou a usar `FilterBar`, preservando a grade atual de filtros e alinhando o container ao padrao global.
- 2026-05-03: `ProdutosHeaderActions` passou a usar `PageHeader`, padronizando titulo, subtitulo, tour e acoes principais da tela de Produtos.
- 2026-05-03: filtros de `ContasPagar` e `ContasReceber` passaram a usar `FilterBar`, mantendo os campos e handlers atuais.
- 2026-05-03: cabecalhos de `ContasPagar` e `ContasReceber` passaram a usar `PageHeader`, com acoes em `ActionButton` e icones padronizados.
- 2026-05-03: `PDVClienteCard` foi quebrado em blocos internos de busca, resumo, fidelidade, credito, acoes e seletor de pet, preparando o card de cliente para virar componente reutilizavel sem mudar o fluxo do PDV.
- 2026-05-03: criado `ProdutoSelector` reutilizavel e aplicado na busca de produtos/servicos do PDV, mantendo a renderizacao customizada das sugestoes do carrinho.
- 2026-05-03: criado `PessoaSelector` reutilizavel e aplicado na busca de cliente do PDV, preservando a busca externa atual e preparando o reaproveitamento em pets, financeiro, campanhas e banho/tosa.
- 2026-05-03: `/pets` passou a usar `PessoaSelector` na busca de tutor, removendo o dropdown manual duplicado e consolidando o segundo uso real do selector de pessoa.
- 2026-05-03: `EntityCard` ganhou modo compacto/header opcional e passou a ser usado no resumo de cliente selecionado do PDV, aproximando o card de cliente do mesmo padrao usado em pets.
- 2026-05-03: `Banho & Tosa` iniciou a reorganizacao visual: parametros, painel, servicos e agenda passaram a abrir formularios sob demanda e usar `Panel`, `MetricGrid`, `MetricCard`, `StatusBadge`, `ActionButton`, `EmptyState` e `TutorPetSelector` em vez de cards grandes sempre expostos.
- 2026-05-03: agenda de `Banho & Tosa` alinhada ao padrao da agenda veterinaria: o botao `Agendar` abre modal com tutor/pet/servico, horarios livres/ocupados e compromissos do dia selecionado.
- 2026-05-03: fluxo operacional de `Banho & Tosa` simplificado: a etapa `entregue` agora centraliza a geracao da venda no backend, `Retornos` virou `Reagendar`, taxi dog/relatorios foram alinhados aos componentes globais e fotos de pets passaram a aparecer tambem nas sugestoes de reagendamento.
- 2026-05-03: `Banho & Tosa` teve a grade antiga de capacidade removida da agenda, o taxi dog recebeu painel compacto com metricas e a limpeza de componentes antigos/orfaos reduziu o risco de retorno do visual anterior.
- 2026-05-03: indicadores restantes do `Banho & Tosa` foram suavizados para o padrao visual atual, removendo tons laranja decorativos e pesos de fonte excessivos onde nao havia alerta real.
- 2026-05-03: criado `ModuleTabs` e aplicado em Financeiro/Vendas, DRE, Fluxo de Caixa, Campanhas e Pessoas, removendo abas manuais duplicadas e aproximando a navegacao interna dos modulos ao mesmo padrao visual.
- 2026-05-03: DRE avancou na padronizacao financeira com acoes principais, presets, paginacao e detalhes usando `ActionButton`, alem da tabela principal e da tabela de lancamentos migradas para `DataTable`.
- 2026-05-03: Fluxo de Caixa substituiu a tabela manual de previsto/realizado por `DataTable` com linhas expansivas, valores por `MoneyCell`, status por `StatusBadge` e erro via toast em vez de alerta bloqueante.
- 2026-05-03: modais de `ContasPagar` e `ContasReceber` tiveram acoes de confirmar/cancelar/fechar e atalhos de fluxo/venda alinhados ao padrao `ActionButton`, mantendo intencao de cor e tamanho consistente.
- 2026-05-07: `Compras/Pedidos` iniciou a fatia enterprise segura: filtros da listagem extraidos para `PedidosCompraFiltros`, tabela de pedidos extraida para `PedidosCompraTabela` e acoes/status/valor da lista passaram a consumir `ActionButton`, `StatusBadge` e `MoneyCell` sem alterar a regra de negocio.
- 2026-05-07: `Compras/Pedidos` teve o modal de sugestao inteligente extraido para `PedidosCompraSugestaoModal` e o modal de grupos de fornecedor extraido para `ModalGruposFornecedores`, reduzindo o arquivo principal sem mover regra de negocio.
- 2026-05-07: `Compras/Pedidos` teve os modais restantes de rascunho, recebimento, exportacao e envio extraidos para `components/compras`, com o seletor de colunas do documento centralizado em `pedidoDocumentoColunas`, mantendo a regra de negocio na pagina principal.
- 2026-05-07: `Compras/Pedidos` teve o formulario de novo/editar pedido extraido para `PedidoCompraFormulario`, mantendo carregamento, sugestao, submit e estado no componente pai.
- 2026-05-07: `Compras/Pedidos` moveu helpers puros de normalizacao, consolidacao de itens e download de documento para `pedidoCompraUtils`, deixando a pagina focada em estado e orquestracao.
- 2026-05-07: `Compras/Pedidos` agrupou a renderizacao dos modais em `PedidosCompraModalsLayer`, reduzindo o JSX da pagina principal sem mover regras de envio, recebimento, rascunho ou sugestao.
- 2026-05-07: `Compras/Pedidos` extraiu o estado, filtros e calculos da sugestao inteligente para `usePedidosCompraSugestao`, mantendo a decisao de rascunho e aplicacao final orquestradas na pagina.
- 2026-05-07: `Compras/Pedidos` extraiu o estado e operacoes de grupos de fornecedores para `usePedidosCompraGruposFornecedores`, mantendo a tela principal apenas como consumidora do fluxo.
- 2026-05-07: iniciado o padrao operacional de selecao/copia: `ContasPagar` passou a usar `FornecedorSelector` no filtro e nomes copiaveis, enquanto Financeiro/Vendas passou a mostrar produto/SKU com `CopyableValue`/`CopyableCode` nas listas detalhadas.
- 2026-05-07: `Compras/Pedidos` trocou o autocomplete proprio do formulario pelo `FornecedorSelector` compartilhado e os itens do pedido passaram a exibir produto/SKU com componentes copiaveis.
- 2026-05-07: historicos financeiros de cliente e produtos promocionais passaram a usar `CopyableValue`/`CopyableCode` para numero de venda, produto e SKU, reforcando o padrao de consulta operacional.
- 2026-05-07: criado `ProductIdentity` como padrao reutilizavel para nome de produto + SKU/codigo copiavel, aplicado em vendas financeiras, devolucao, compras, widget de cliente, campanhas e rotas de entrega.
- 2026-05-07: criado `SaleReference` para padronizar referencias copiaveis de venda em PDV, devolucao, financeiro, campanhas, caixa e entregas.
- 2026-05-07: PDV reforcou o padrao `SaleReference` em vendas em aberto, vendas recentes e historico do cliente, mantendo a venda copiavel no fluxo de atendimento.
- 2026-05-07: `SaleReference` e codigos copiaveis foram aplicados em conciliacao de vendas, comissoes, devolucao e lista financeira, reduzindo exibicoes manuais de numero de venda/produto.
- 2026-05-07: filtros de fornecedor em Valorizacao de Estoque e Validade Proxima passaram a usar `FornecedorSelector`, mantendo autocomplete, limpar e cadastro rapido no mesmo padrao dos demais fluxos.
- 2026-05-07: filtros de fornecedor em Balanco de Estoque e na listagem de Pedidos de Compra tambem passaram a usar `FornecedorSelector`, removendo selects duplicados.
- 2026-05-07: filtro principal de fornecedor em Produtos e a modal de Nova Conta a Pagar passaram a usar `FornecedorSelector`, reforcando autocomplete/cadastro rapido no cadastro operacional.
- 2026-05-07: Pendencias de fornecedor, Entrada de Estoque, modal legado de fornecedor do produto e Grupos de Fornecedores passaram a usar `FornecedorSelector`, incluindo cadastro rapido e selecao padronizada.
- 2026-05-07: PDV passou a expor `Devolucao` diretamente no modo de visualizacao da venda elegivel, reaproveitando o modal de devolucao com venda inicial e mantendo produtos/SKUs copiaveis tambem nos componentes de kits.
- 2026-05-07: Relatorio de Movimentacoes passou a reutilizar `ProductIdentity` e `SaleReference` no produto selecionado, cabecalho, historico de vendas e tabela de movimentos, padronizando copia de produto/SKU/venda.
- 2026-05-08: Sugestao inteligente de compras deixou de somar movimentacoes de estoque com `referencia_tipo=venda` quando a venda referenciada nao existe, evitando que historico orfao infle o giro e gere compra exagerada.
- 2026-05-08: `Comissoes/Listagem` iniciou padronizacao visual com `MetricGrid`/`MetricCard`, `MoneyCell`, `NumberCell`, `StatusBadge`, `ActionButton` e estados globais de carregamento/erro/vazio, sem alterar a regra de fechamento.
- 2026-05-08: Modal de devolucao no PDV passou a usar `data_venda`, codigo do cliente e copia padronizada de cliente/codigo; producao ganhou `ops_disk_guard` preventivo para limpar cache Docker quando o disco entrar em faixa de risco.
- 2026-05-08: criado `CustomerIdentity` para nome/codigo de cliente copiaveis e aplicado em devolucao PDV, vendas recentes, financeiro, contas a receber, relatorio de produto, NF, entregas e comissoes.
- 2026-05-08: `CustomerIdentity` passou a reconhecer campos de tutor/pessoa e foi expandido para Banho & Tosa, Pets, campanhas, creditos, Pedido Bling e cards veterinarios.
- 2026-05-08: PDV expandiu `CustomerIdentity` para card do cliente, assistente IA, widget lateral, historico de compras e vendas em aberto, mantendo nome/codigo copiaveis nos fluxos de atendimento.
- 2026-05-08: criado `PetIdentity` para nome/codigo de pet copiaveis e aplicado em Banho & Tosa, veterinario, lembretes, relatorio de vendas, widget de cliente e alertas inteligentes do PDV.
- 2026-05-08: criado `FornecedorIdentity` para nome/documento/codigo de fornecedor copiaveis e aplicado em compras, contas a pagar, conciliacao e relatorios de produtos/validade.
- 2026-05-08: Go-live de autenticacao iniciado. Cadastro de novo tenant passou a exigir aceite explicito de Termos/Privacidade, salvar versoes/IP/user-agent, enviar confirmacao de e-mail e nao tentar carregar `/auth/me-multitenant` antes de selecionar tenant.
- 2026-05-08: Clientes do e-commerce/app tambem passaram a aceitar Termos/Privacidade e ficam bloqueados ate confirmar e-mail quando `EMAIL_VERIFICATION_REQUIRED=true`. Foram adicionadas `/verificar-email`, `/termos`, `/privacidade` e a migration `nv20260508a1_user_email_verification_lgpd.py`.
- 2026-05-08: Login ERP/e-commerce recebeu trava configuravel por tentativas falhas, auditoria de eventos sensiveis, registro de ultimo login/IP, revogacao de sessoes apos troca de senha e hardening de headers/CORS para reduzir risco antes do go-live.
- 2026-05-08: Endpoints LGPD legados do WhatsApp tiveram listagem/processamento de solicitacoes de exclusao e log de auditoria corrigidos para voltar a bater com os campos reais do banco.
- 2026-05-08: Termos de Uso e Politica de Privacidade foram expandidos para cobrir ERP, app, e-commerce, tenant, cookies, integracoes, retencao, direitos dos titulares, incidentes, IA, comunicacoes e canal de privacidade sem aviso juridico para o cliente final.
- 2026-05-08: LGPD operacional iniciada com dossie/exportacao de cliente, historico de consentimentos, preferencias de comunicacao, solicitacoes gerais de titulares e trilha de acesso tanto no ERP (`/lgpd`) quanto no app/e-commerce (`/app/privacidade`).
- 2026-05-08: tela operacional de LGPD adicionada ao ERP em Administracao > LGPD e Privacidade, com busca de cliente, dossie exportavel, preferencias, abertura/processamento de solicitacoes e campanhas respeitando opt-out explicito de email/push.
- 2026-05-08: API operacional de LGPD passou a exigir `usuarios.manage`, ganhou anonimizacao auditavel de cliente por solicitacao de exclusao e centralizou helpers de opt-out para WhatsApp/SMS quando esses disparos forem usados.
- 2026-05-08: migration complementar garante a tabela `data_access_logs` usada pela trilha de auditoria LGPD mesmo em ambientes que ja tinham consentimentos/exclusoes legados parcialmente criados.
- 2026-05-08: busca de titular na LGPD passou a usar `PessoaSelector` com `incluir_inativos=true`, permitindo localizar clientes ja inativados pelo cadastro antes da anonimizacao.
- 2026-05-08: tela LGPD reorganizada em fluxo guiado: cards de status, busca unica do titular, solicitacoes daquele cliente, acao explicita de exclusao/anonimizacao e dossie/preferencias apenas depois da selecao. Migration `nz20260508a5_lgpd_consent_audit_columns.py` alinha `data_privacy_consents` com as colunas de auditoria usadas pelo servico para evitar erro 500 no dossie.
- 2026-05-08: LGPD operacional foi simplificada para tela principal com apenas busca do titular e fila de solicitacoes; tratamento, registro manual de pedido, dossie/exportacao e preferencias passaram para modais. A busca de titular deixou de filtrar apenas `tipo_cadastro=cliente`, permitindo localizar titulares cadastrados como veterinario/funcionario/fornecedor, como `Lucas Guerra de Moraes`.
- 2026-05-08: exclusoes LGPD concluidas continuam auditaveis por filtro/pesquisa, mas a solicitacao deixa de guardar nome, e-mail, telefone e texto livre do solicitante apos a anonimizacao. Migration `oa20260508a6_scrub_completed_lgpd_deletion_requests.py` limpa tambem os historicos ja concluidos.
- 2026-05-08: auditoria pre-go-live de autenticacao encontrou rotas antigas sem dependencia explicita. Foram protegidas por auth/tenant as rotas legadas de comissoes, taxas de forma de pagamento, sugestao fiscal, canais DRE e lista de tools WhatsApp; o scanner local voltou a `0` rotas suspeitas fora da allowlist publica.
- 2026-05-09: promocao ERP de produto passou a usar componente com preco + inicio/fim em data e hora, e o PDV passou a consumir `preco_venda_pdv` com selo de promocao quando a janela estiver ativa. A antiga fusao de produtos encontrada em sugestoes de racoes e limitada; proxima entrega recomendada e uma fusao operacional segura por pares, com decisao campo a campo e transferencia auditada de historico.
- 2026-05-09: SKU de produto passou a ser normalizado em maiusculas no backend e validado por `lower(trim(codigo))` em cadastro, edicao, variacoes, importacao por planilha, criacao via XML e autocadastro Bling/NF. Isso bloqueia novos duplicados por diferenca de caixa, como `pet5136` versus `PET5136`; duplicados historicos devem ser resolvidos pela fusao segura.
- 2026-05-09: iniciado fluxo operacional de fusao segura de produtos na listagem: selecionar exatamente 2 produtos, escolher o principal, revisar conflitos campo a campo, somar estoque e transferir referencias historicas antes de inativar o duplicado. O indice unico de SKU tambem passa a usar `tenant_id + lower(trim(codigo))` no banco para impedir reincidencia.
- 2026-05-09: criado `scripts/smoke_golive.py` para rodada curta de go-live autenticado sem escrita de dados: health/frontend legal, login ERP, selecao de tenant, usuario atual, produtos, produtos vendaveis PDV, clientes, caixa aberto, LGPD status e catalogo publico e-commerce/app.
- 2026-05-16: `scripts/smoke_golive.py` ganhou modo publico (`GOLIVE_PUBLIC_ONLY=true`) e teste automatizado, permitindo validar health/paginas publicas sem credenciais antes da rodada autenticada.
- 2026-05-09: webhook Pagar.me endurecido para exigir assinatura HMAC quando a validacao estiver ligada ou quando o gateway Pagar.me estiver ativo; se faltar segredo em producao, o endpoint falha explicitamente em vez de aceitar payload sem validacao.
- 2026-05-09: Relatorio de Movimentacoes teve os modais de reservas, lancamento manual e lancamento de granel extraidos para `components/estoque`, reaproveitando `ActionButton`, `ProductIdentity`, `StatusBadge` e `EmptyState` sem alterar a regra da pagina.
- 2026-05-09: Relatorio de Movimentacoes tambem extraiu o painel `VendasPorCanalPanel`, deixando a pagina principal com calculo/orquestracao e a apresentacao do resumo por canal em componente dedicado.
- 2026-05-09: Relatorio de Movimentacoes extraiu a tabela de lancamentos para `MovimentacoesLancamentosTable`, padronizando a acao de exclusao com `ActionButton` e badges com `StatusBadge` enquanto preserva selecao, navegacao por origem e edicao por clique.
- 2026-05-09: Relatorio de Movimentacoes extraiu o cabecalho/resumo do produto para `MovimentacoesProdutoHeader`, incluindo avisos de kit, acoes rapidas e cards de estoque; o arquivo principal saiu da zona acima de 1000 linhas.
- 2026-05-09: `VendasFinanceiro` extraiu cabecalho/filtros/abas para `VendasFinanceiroHeader`, graficos do resumo para `VendasFinanceiroGraficosResumo` e painel de promocoes para `VendasPromocoesResumoPanel`, reduzindo o arquivo principal para 3177 linhas com build validado.
- 2026-05-10: `VendasFinanceiro` extraiu o painel de dias uteis para `DiasUteisResumoPanel` e o modal de relatorio personalizado para `VendasRelatorioPersonalizadoModal`, reduzindo o arquivo principal para 2988 linhas com build validado.
- 2026-05-10: `VendasFinanceiro` extraiu blocos visuais de composicao, resumo, lista, comparacao e analise inteligente para componentes dedicados, reduzindo o arquivo principal para 1980 linhas com build validado.
- 2026-05-10: `EntradaXML` iniciou a quebra segura dos modais operacionais, extraindo historico de precos, revisao de precos, resultado de lote e rascunho de devolucao para `components/entrada-xml`, reduzindo o arquivo principal para 4420 linhas com build validado.
- 2026-05-12: `EstoqueFullNF` passou a usar `PageHeader`, `ModuleTabs`, `Panel`, `ActionButton`, `IconActionButton`, `EmptyState` e `DataTable`; o badge de canal foi centralizado em `ChannelBadges` com suporte a Amazon, Mercado Livre, Shopee e FULL.
- 2026-05-12: criado `CatalogoProdutoSelectors` para centralizar autocomplete de categoria e marca de produtos, aplicado em filtros de produtos, edicao em lote, cadastro/edicao de produto, balanco, valorizacao e validade proxima.
- 2026-05-12: botoes de geracao no cadastro de produto e acoes principais de valorizacao/validade proxima passaram a usar `ActionButton`, mantendo o padrao visual sem alterar regras das telas.
- 2026-05-12: criado `SegmentedControl` para alternancias compactas, aplicado no modo de descricao do produto e no filtro de itens da Entrada XML, removendo botoes inline duplicados.
- 2026-05-10: `EntradaXML` extraiu o modal de visualizacao da NF para `EntradaXmlVisualizacaoNotaModal`, preservando os callbacks da pagina e reduzindo o arquivo principal para 4169 linhas com build validado.
- 2026-05-15: cadastros basicos de `Departamentos` e `Tipos de Despesa` iniciaram a padronizacao de acoes com `ActionButton`, `IconActionButton`, `LoadingState` e `EmptyState`, mantendo comportamento e endpoints iguais.
- 2026-05-17: `/clientes` foi realinhada com a fundacao visual: `PageHeader`, `Panel`, `LoadingState`, `EmptyState`, `ActionButton` e `IconActionButton`; `Novo` voltou para a cor semantica de criacao.
- 2026-05-18: `EntradaXML` extraiu cabecalho/acoes de upload para `EntradaXmlHeader`, metricas para `EntradaXmlMetricas` e paineis SEFAZ para `EntradaXmlSefazPanels`, usando `PageHeader`, `ActionButton`, `Panel`, `MetricGrid`/`MetricCard` e `StatusBadge`; o arquivo principal caiu de 3871 para 3717 linhas com build validado. Faltam blocos internos de itens da nota.
- 2026-05-18: `EntradaXML` extraiu a listagem principal de notas para `EntradaXmlNotasTable`, migrando filtros para `SegmentedControl`, acoes para `ActionButton`, status para `StatusBadge` e tabela para `DataTable`; o arquivo principal caiu de 3717 para 3561 linhas com build validado.
- 2026-05-18: `EntradaXML` extraiu o modal de criacao de produto para `EntradaXmlCriarProdutoModal`, mantendo callbacks da pagina e padronizando carregamento/acoes com `LoadingState`, `IconActionButton` e `ActionButton`; o arquivo principal caiu de 3561 para 3319 linhas com build validado. Faltam blocos internos de itens da nota.
- 2026-05-18: `EntradaXML` extraiu o modal de detalhes/conferencia para `EntradaXmlDetalhesModal`, preservando callbacks da pagina e reduzindo o arquivo principal de 3319 para 2486 linhas com build validado.
- 2026-05-18: `EntradaXmlDetalhesModal` extraiu o card de item para `EntradaXmlDetalhesItemCard`, reduzindo o modal de 957 para 464 linhas e padronizando acoes internas claras com `ActionButton`/`IconActionButton` por funcao.
- 2026-05-18: `EntradaXmlDetalhesModal` extraiu o rodape/rateio para `EntradaXmlDetalhesFooter`, reduzindo o modal de 464 para 357 linhas e padronizando acoes de rateio/processamento/exclusao com `ActionButton` por funcao.
- 2026-05-18: `EntradaXmlDetalhesModal` extraiu o painel de conferencia para `EntradaXmlDetalhesConferenciaPanel`, reduzindo o modal de 357 para 266 linhas e padronizando as acoes de conferencia, tratativas, pendencia e devolucao com `ActionButton` por funcao. Proximo passo: avaliar PR/smoke ou seguir com pequenas limpezas de cabecalho/listagem do modal.
- 2026-05-18: `EntradaXML` extraiu helpers puros de XML, packs, conferencia, custo, relatorio e divergencias para `entradaXmlUtils`, reduzindo o arquivo principal de 2743 para 2248 linhas com build validado. Proximo passo: extrair carregamento/acoes SEFAZ ou exportadores de relatorio.
- 2026-05-18: `EntradaXML` extraiu exportacao CSV/PDF e montagem do relatorio de custos maiores para `entradaXmlRelatorioCustos`, reduzindo o arquivo principal de 2248 para 1970 linhas com build validado. Proximo passo: extrair carregamento/acoes SEFAZ.
- 2026-05-18: `EntradaXML` extraiu estado e acoes de busca/configuracao/importacao SEFAZ para `useEntradaXmlSefaz`, reduzindo o arquivo principal de 1970 para 1798 linhas com build validado. Proximo passo: avaliar extracao de upload/lote ou revisao de precos.
- 2026-05-18: `EntradaXML` extraiu upload individual/lote, estados do modal de resultado e mensagens de processamento para `useEntradaXmlUpload`, reduzindo o arquivo principal de 1798 para 1663 linhas com build validado. Proximo passo: avaliar revisao de precos ou acoes de vinculacao/rateio.
- 2026-05-18: `EntradaXML` extraiu preview/processamento, calculos de margem/custo, confirmacao e exportacao da revisao de precos para `useEntradaXmlRevisaoPrecos`, reduzindo o arquivo principal de 1663 para 1190 linhas com build validado. Proximo passo: extrair busca/vinculacao/criacao de produtos da NF.
- 2026-05-18: `EntradaXML` extraiu busca com debounce, vinculacao/desvinculacao e criacao individual/em lote de produtos da NF para `useEntradaXmlProdutos`, reduzindo o arquivo principal de 1190 para 859 linhas com build validado. Proximo passo: avaliar rateio/conferencia residual ou PR/smoke.
- 2026-05-18: `EntradaXML` extraiu estado, salvamento/desfazer, rascunho de devolucao, pendencia de fornecedor e itens derivados de conferencia para `useEntradaXmlConferencia`, reduzindo o arquivo principal de 859 para 687 linhas com build validado. Proximo passo: avaliar rateio/historico ou preparar smoke do PR.
- 2026-05-18: `EntradaXML` extraiu estado/carregamento do historico de precos para `useEntradaXmlHistoricoPrecos` e estado/acoes de rateio e pack para `useEntradaXmlRateio`, reduzindo o arquivo principal de 687 para 621 linhas. Smoke visual local corrigiu a abertura do modal de detalhes e normalizou mensagens estruturadas de erro da API. Proximo passo: revisar proximo arquivo grande ou preparar validacao de PR.
- 2026-05-18: `EcommerceMVP` iniciou a quebra do storefront extraindo utilitarios de carrinho convidado, endereco, midia, estoque, banners e mensagens de erro para `ecommerceMvpUtils`, reduzindo a pagina de 2816 para 2542 linhas e usando `formatMoneyBRL` como base de moeda.
- 2026-05-18: `EcommerceMVP` extraiu o card de produto da vitrine para `EcommerceCatalogProductCard`, substituindo icones soltos por `lucide-react`, mantendo acoes de desejo/carrinho/aviso e reduzindo a pagina principal de 2542 para 2483 linhas.
- 2026-05-18: `EcommerceMVP` extraiu resumo, metricas e filtros da vitrine para `EcommerceCatalogControls`, preservando a composicao com sidebar e usando icones `lucide-react` para busca, atualizar e limpar filtros; a pagina principal caiu de 2483 para 2394 linhas. Proximo passo: separar a sidebar/resumo do carrinho da vitrine.
- 2026-05-18: `EcommerceMVP` extraiu a sidebar da loja e o resumo lateral do carrinho para `EcommerceCartPanels`, mantendo handlers de checkout/navegacao na pagina e trocando icones soltos por `lucide-react`; a pagina principal caiu de 2394 para 2349 linhas. Proximo passo: separar lista de itens do carrinho/checkout.
- 2026-05-18: `EcommerceMVP` ampliou a quebra do storefront extraindo a tela completa do carrinho para `EcommerceCartPanels` e o modal de detalhe do produto para `EcommerceProductDetailModal`, mantendo estado e handlers na pagina; a pagina principal caiu de 2349 para 2229 linhas. Proximo passo: separar checkout e pedidos em componentes de tela.
- 2026-05-19: `VendasFinanceiro` retomou a Onda 1 extraindo utilitarios puros de data, feriados, status, Excel e ajuste de imposto para `frontend/src/components/financeiro/vendasFinanceiroUtils.js`, com teste dedicado em Node; o arquivo principal caiu de 2013 para 1671 linhas. Proximo passo: extrair filtros/periodos ou banner de comparacao para componentes menores.
- 2026-05-19: `VendasFinanceiro` continuou a extracao para o mesmo utilitario, movendo filtro/ordenacao de relatorio, valor recebido visual, sanitizacao numerica, formatacao de data e texto de comparacao; o arquivo principal caiu de 1671 para 1584 linhas com os testes Node ampliados para 9 casos. Proximo passo: extrair calculo de periodo comparativo ou o banner de comparacao em componente dedicado.
- 2026-05-19: `VendasFinanceiro` extraiu calculo de periodo comparativo, variacao financeira e analise inteligente de produtos/alertas para `vendasFinanceiroUtils`, reduzindo o arquivo principal de 1584 para 1411 linhas e ampliando os testes Node para 12 casos. Proximo passo: avaliar se o restante vira hooks menores de carregamento/estado ou se a proxima frente deve atacar outro arquivo critico.
- 2026-05-19: `VendasFinanceiro` moveu filtros rapidos de periodo, consolidacao de formas de recebimento e filtros auxiliares para `vendasFinanceiroUtils`, reduzindo o arquivo principal de 1411 para 1282 linhas e ampliando os testes Node para 14 casos. Proximo passo: extrair calendarios/resumos de dias uteis ou encerrar a frente do financeiro e escolher outro arquivo critico.
- 2026-05-19: `VendasFinanceiro` extraiu feriados do periodo, calendario de vendas por dia e resumo de dias uteis para `vendasFinanceiroUtils`, reduzindo o arquivo principal de 1282 para 1220 linhas e ampliando os testes Node para 15 casos. Proximo passo: avaliar se vale extrair totalizadores/promocoes restantes ou migrar a refatoracao para outro arquivo critico.
- 2026-05-19: `VendasFinanceiro` extraiu totalizadores da lista e analise de promocoes para `vendasFinanceiroUtils`, reduzindo o arquivo principal de 1220 para 1104 linhas e ampliando os testes Node para 17 casos. Proximo passo: extrair rankings por dia/horario ou encerrar a frente do financeiro e escolher outro arquivo critico.
- 2026-05-19: `VendasFinanceiro` extraiu distribuicao temporal por dia da semana/horario e selecao de melhores periodos para `vendasFinanceiroUtils`, reduzindo o arquivo principal de 1104 para 1029 linhas e ampliando os testes Node para 18 casos. Proximo passo: extrair composicao dos cards/totalizadores restantes ou escolher o proximo arquivo critico.
- 2026-05-19: `VendasFinanceiro` moveu a composicao dos cards do resultado financeiro para `vendasFinanceiroUtils`, reduzindo o arquivo principal de 1029 para 915 linhas e ampliando os testes Node para 19 casos. Proximo passo: extrair cards totalizadores da lista ou encerrar esta frente por ja estar abaixo de 1000 linhas.
- 2026-05-19: `VendasFinanceiro` extraiu os cards totalizadores da lista para `vendasFinanceiroUtils`, reduzindo o arquivo principal de 915 para 904 linhas e ampliando os testes Node para 20 casos. Proximo passo: encerrar esta frente ou escolher outro arquivo critico acima de 1000 linhas.
- 2026-05-20: `Layout.jsx` iniciou a proxima frente de refatoracao extraindo a configuracao de menu para `frontend/src/components/layout/menuConfig.js`, reduzindo o componente principal de 1484 para 873 linhas e cobrindo o contrato basico do menu com teste Node dedicado. Proximo passo: extrair a renderizacao dos itens da sidebar ou escolher outro hotspot acima de 1000 linhas.
- 2026-05-20: `Layout.jsx` extraiu a renderizacao dos itens da sidebar para `frontend/src/components/layout/SidebarMenu.jsx`, mantendo os estados premium/dev e reduzindo o componente principal para 694 linhas. Proximo passo: acompanhar os checks do PR e, se seguir verde, escolher outro hotspot acima de 1000 linhas.
- 2026-05-20: iniciada a trilha de responsividade do ERP no celular/app pela fundacao global: `Layout`, `PageHeader`, `DataTable`, `ModuleTabs`, `ResponsiveTable` e `index.css` ganharam classes/contencoes para reduzir overflow lateral, melhorar acoes de cabecalho e preparar revisoes tela por tela.
- 2026-05-20: `/clientes` recebeu lista mobile em cards para Pessoas/Pets, mantendo a tabela apenas no desktop e preservando fusao, WhatsApp, edicao, exclusao e expansao de pets. A calculadora flutuante agora fica compacta no mobile para nao cobrir a lista. Validado em 390px sem overflow horizontal.
- 2026-05-20: `/pets` recebeu ajustes mobile na barra de filtros, filtros avancados e identidade do tutor, evitando campos espremidos e textos longos vazando no card. A calculadora flutuante global passou a ficar oculta no mobile para nao competir com acoes principais. Validado em 390px sem overflow horizontal.
- 2026-05-20: `/produtos` recebeu padding mobile consistente, acoes principais em largura cheia no celular, filtros booleanos com areas de toque mais confortaveis e codigos longos quebrando linha dentro dos cards de produto.
- 2026-05-20: `/pdv` iniciou a fatia mobile segura: topo, menu de caixa, busca de cliente, resumo de vendas abertas e controles do carrinho passaram a quebrar em coluna no celular, reduzindo risco de overflow sem alterar regra de venda, estoque, caixa ou pagamento.
- 2026-05-20: `/financeiro/vendas` recebeu a primeira fatia mobile: cabecalho, relatorios/exportacoes, filtros de periodo, filtros avancados, graficos, cards e lista de vendas passaram a se adaptar melhor ao celular/app sem alterar calculos financeiros, exportacoes ou regras de venda.
- 2026-05-20: `/veterinario/dashboard`, `/veterinario/consultas` e `/banho-tosa` receberam uma fatia mobile segura: cabecalhos e acoes empilham no celular, KPIs/atalhos deixam de apertar em duas colunas, a tabela de consultas ganha scroll controlado e o modal de agendamento do Banho & Tosa abre como folha inferior em telas estreitas.
- 2026-05-20: `EcommerceMVP.jsx` iniciou a proxima frente extraindo categorias, metricas e filtros/ordenacao do catalogo para `ecommerceMvpUtils`, com teste Node dedicado em `ecommerceMvpUtils.test.mjs`, reduzindo a tela para 2168 linhas. Proximo passo: extrair cabecalho/banner ou pedidos/conta em componente de apresentacao.
- 2026-05-20: `EcommerceMVP.jsx` moveu banners ativos, nome exibido da loja, mapa de produtos, validacao de perfil completo e mapeamento de endereco/cadastro do cliente para `ecommerceMvpUtils`, ampliando o teste Node para 9 casos e reduzindo a tela para 2105 linhas. Proximo passo: extrair pedidos ou conta em componente de apresentacao.
- 2026-05-20: `EcommerceMVP.jsx` extraiu a aba de pedidos para `frontend/src/pages/ecommerce/EcommerceOrdersPage.jsx`, preservando listagem, status, senha de retirada, fluxo drive e itens, reduzindo a tela principal para 2027 linhas. Proximo passo: extrair conta/login ou checkout em componentes de apresentacao.
- 2026-05-20: `EcommerceMVP.jsx` extraiu a aba de conta/login para `frontend/src/pages/ecommerce/EcommerceAccountPage.jsx`, mantendo cadastro, login, recuperacao de senha e perfil do cliente como apresentacao, reduzindo a tela principal para 1692 linhas. Proximo passo: extrair checkout ou modal avise-me.
- 2026-05-20: `EcommerceMVP.jsx` extraiu o modal avise-me para `frontend/src/pages/ecommerce/EcommerceNotifyMeModal.jsx`, mantendo fechamento, captura de email e submissao, reduzindo a tela principal para 1671 linhas. Proximo passo: extrair footer ou checkout.
- 2026-05-20: `EcommerceMVP.jsx` extraiu o rodape para `frontend/src/pages/ecommerce/EcommerceFooter.jsx`, preservando navegacao, contatos e dados do tenant, reduzindo a tela principal para 1639 linhas. Proximo passo: iniciar a extracao do checkout em componentes menores.
- 2026-05-20: `EcommerceMVP.jsx` extraiu a tela de checkout para `frontend/src/pages/ecommerce/EcommerceCheckoutPage.jsx`, mantendo formularios de entrega/pagamento e resumo como apresentacao, reduzindo a tela principal para 1514 linhas. Proximo passo: separar header/hero ou iniciar hooks de orquestracao.
- 2026-05-20: `EcommerceMVP.jsx` extraiu topbar, header, banner, barra do app e abas para `frontend/src/pages/ecommerce/EcommerceStorefrontChrome.jsx`, mantendo busca, navegacao e destaque visual como apresentacao, reduzindo a tela principal para 1408 linhas. Proximo passo: extrair a composicao da vitrine ou iniciar hooks de carrinho/autenticacao.
- 2026-05-20: `EcommerceMVP.jsx` extraiu a aba Loja para `frontend/src/pages/ecommerce/EcommerceStorePage.jsx`, mantendo resumo, filtros, grid de produtos e sidebar do carrinho como apresentacao, reduzindo a tela principal para 1372 linhas. Proximo passo: iniciar hooks de carrinho/autenticacao ou escolher outro hotspot acima de 1000 linhas.
- 2026-05-20: `EcommerceMVP.jsx` iniciou a extracao de hooks movendo estado, filtros, metricas e derivados do catalogo para `frontend/src/pages/ecommerce/useEcommerceCatalog.js`, reduzindo a tela principal para 1359 linhas. Proximo passo: extrair modal de produto ou carrinho em hooks menores.
- 2026-05-20: `EcommerceMVP.jsx` extraiu o estado do modal de produto para `frontend/src/pages/ecommerce/useEcommerceProductModal.js`, mantendo abertura por link direto, ESC, imagem ativa e analytics fora da tela principal, reduzindo o arquivo para 1334 linhas. Proximo passo: separar estados/efeitos de autenticacao ou carrinho.
- 2026-05-20: `EcommerceMVP.jsx` extraiu wishlist e avise-me para `frontend/src/pages/ecommerce/useEcommerceEngagement.js`, mantendo persistencia local, modal de aviso e chamada de registro fora da tela principal, reduzindo o arquivo para 1289 linhas. Proximo passo: separar estados/efeitos de autenticacao ou carrinho.
- 2026-05-20: `EcommerceMVP.jsx` extraiu pedidos recentes e drive-cheguei para `frontend/src/pages/ecommerce/useEcommerceOrders.js`, mantendo recarga da aba Pedidos, persistencia dos IDs e atualizacao apos checkout em hook dedicado, reduzindo o arquivo para 1254 linhas. Proximo passo: separar carrinho/checkout ou autenticacao em hooks menores.
- 2026-05-20: `EcommerceMVP.jsx` extraiu estado e operacoes do carrinho para `frontend/src/pages/ecommerce/useEcommerceCart.js`, mantendo carrinho visitante, sincronizacao apos login, adicionar/atualizar itens e total calculado em hook dedicado, reduzindo o arquivo para 1130 linhas. Proximo passo: separar checkout/pagamento ou autenticacao/perfil.
- 2026-05-20: `EcommerceMVP.jsx` extraiu estado e operacoes de checkout/pagamento para `frontend/src/pages/ecommerce/useEcommerceCheckout.js`, mantendo cupom, endereco, resumo, idempotencia, tracking e finalizacao em hook dedicado, reduzindo o arquivo para 983 linhas. Proximo passo: separar autenticacao/perfil ou finalizar esta rodada para merge controlado.
- 2026-05-20: `EcommerceMVP.jsx` extraiu autenticacao, perfil e recuperacao de senha para `frontend/src/pages/ecommerce/useEcommerceCustomer.js`, mantendo login, cadastro, sessao, CEPs do perfil e sincronizacao do carrinho apos autenticar em hook dedicado, reduzindo o arquivo para 637 linhas. Proximo passo: revisar o PR para merge/deploy controlado ou escolher outro hotspot.
- 2026-05-20: `EcommerceMVP.jsx` extraiu os estilos internos para `frontend/src/pages/ecommerce/ecommerceMvpStyles.js`, mantendo a mesma API de `styles={S}` usada pelas telas do storefront e reduzindo o arquivo para 553 linhas. Proximo passo: revisar o PR para merge/deploy controlado.
- 2026-06-03: `produtos_routes.py` retomou a frente de arquivos grandes extraindo helpers de listagem, promocao exibida no PDV, reservas multitenant, area/fornecedor e valorizacao para `backend/app/produtos/listagem.py`, reduzindo o router de 6275 para 6003 linhas com testes focados de listagem/validade/busca preservados. A fatia de 2026-06-08 concluiu a extracao da montagem de load options e dos filtros basicos das listagens, deixando o router com 4677 linhas. Proximo passo: extrair apenas construcao de query base/status/busca de `listar_produtos` e `listar_produtos_vendaveis`, sem mexer em estoque, fiscal, PDV ou regras de preco.
- 2026-06-23: `produtos_routes.py` executou a fatia recomendada de query base/status/busca, movendo a montagem de `listar_produtos` e `listar_produtos_vendaveis` para `_montar_query_listagem_produtos` e `_montar_query_produtos_vendaveis` em `backend/app/produtos/listagem.py`. As rotas continuam responsaveis por filtros basicos/fornecedor, paginacao, enriquecimento, reservas, validade e retorno HTTP. Na branch atual, o router caiu de 1837 para 1799 linhas, com `pytest` dos `backend/tests/unit/test_produtos*.py` passando 83 casos. Proximo passo: decidir entre uma fatia pequena de contagem/hierarquia de variacoes ou trocar para outro hotspot, sem mexer em estoque, fiscal, PDV ou regras de preco.
- 2026-06-23: `produtos_routes.py` continuou a mesma trilha extraindo a expansao de hierarquia da listagem para `_expandir_produtos_listagem` em `backend/app/produtos/listagem.py`. A rota preserva pagina, total, payload, filtros, reservas e validade, mas deixa de conter o loop de contagem/enriquecimento/variacoes. Na branch atual, o router caiu de 1799 para 1760 linhas, com `pytest` dos `backend/tests/unit/test_produtos*.py` passando 85 casos. Proximo passo: antes de nova fatia em Produtos, avaliar se vale extrair paginacao/fetch final ou migrar para outro hotspot acima de 1000 linhas.
- 2026-06-23: `produtos_routes.py` extraiu tambem o fetch final paginado das listagens para `_buscar_pagina_produtos_listagem`, centralizando `count`, ordenacao, load options, offset/limit e remocao de itens nulos em `backend/app/produtos/listagem.py`. `listar_produtos_vendaveis` preserva o modo sem contagem total e `listar_produtos` preserva o log/total/paginacao. Na branch atual, o router caiu de 1760 para 1743 linhas, com `pytest` dos `backend/tests/unit/test_produtos*.py` passando 87 casos. Proximo passo: considerar encerrar a rodada de Produtos/listagem e abrir outro hotspot critico acima de 1000 linhas.
- 2026-06-23: `produtos_routes.py` recebeu uma fatia de acabamento extraindo a montagem da resposta paginada para `_montar_resposta_produtos_paginados`, preservando `items`, `total`, `page`, `page_size`, `pages` e o fallback de total estimado de `listar_produtos_vendaveis`. Na branch atual, o router caiu de 1743 para 1740 linhas, com `pytest` dos `backend/tests/unit/test_produtos*.py` passando 89 casos. Proximo passo: encerrar Produtos/listagem nesta rodada ou migrar para outro hotspot critico acima de 1000 linhas.
- 2026-06-23: `pedidos_compra_routes.py` iniciou nova fatia backend em Compras/Pedidos extraindo constantes e helpers puros da sugestao inteligente para `backend/app/pedidos_compra/sugestao.py`: normalizacao numerica, arredondamento seguro, sanitizacao JSON, datetime UTC naive, origem de venda e estrutura inicial de estatisticas. O router caiu de 1968 para 1922 linhas, com `pytest backend/tests/unit/test_pedidos_compra_sugestao_helpers.py -q`, testes unitarios de pedidos de compra e import do router passando. Proximo passo: avaliar extrair os proximos helpers puros de acumulacao de vendas/granel ou encerrar a fatia para PR.
- 2026-06-23: `pedidos_compra_routes.py` continuou a extracao da sugestao inteligente movendo `_somar_venda_sugestao` e `_somar_conversao_granel_sugestao` para `backend/app/pedidos_compra/sugestao.py`, mantendo os acumuladores de periodo, janelas, origem, fonte e conversao de granel cobertos por teste unitario. O router caiu de 1922 para 1846 linhas, com `pytest backend/tests/unit/test_pedidos_compra_sugestao_helpers.py -q`, testes unitarios de pedidos de compra e import do router passando. Proximo passo: extrair apenas a leitura/agregacao de vendas da sugestao ou encerrar a fatia para PR.
- 2026-06-23: `pedidos_compra_routes.py` moveu a agregacao de `vendas_rows` para `_somar_vendas_rows_sugestao` em `backend/app/pedidos_compra/sugestao.py`, preservando o retorno de pares `(venda_id, produto_id)` usado para evitar dupla contagem com movimentacoes de estoque. O router caiu de 1846 para 1834 linhas, com o teste novo cobrindo acumulacao, origens, fontes e pares retornados. Proximo passo: extrair apenas a agregacao de conversoes de granel ou movimentacoes complementares da sugestao.
- 2026-06-23: `pedidos_compra_routes.py` extraiu a agregacao de `conversoes_rows` para `_somar_conversoes_granel_rows_sugestao`, mantendo a query no router e delegando apenas o consumo dos rows carregados para `backend/app/pedidos_compra/sugestao.py`. O router caiu de 1834 para 1827 linhas, com teste unitario cobrindo nome do produto granel, peso por pacote, origem e fonte. Proximo passo: extrair apenas a agregacao das movimentacoes complementares da sugestao ou encerrar a fatia para PR.
- 2026-06-23: `pedidos_compra_routes.py` moveu a agregacao das movimentacoes complementares para `_somar_movimentacoes_complementares_sugestao`, mantendo no router apenas a consulta e a validacao das vendas referenciadas. A fatia preserva a deduplicacao de venda direta, consumo derivado e origem externa/Bling, com teste unitario cobrindo os tres caminhos. O router caiu de 1827 para 1798 linhas. Proximo passo: encerrar a subtrilha de sugestao ou extrair apenas a montagem do resultado final.
- 2026-06-23: `pedidos_compra_routes.py` concluiu a subtrilha da sugestao extraindo a montagem do payload para `_montar_resultado_vendas_sugestao`, preservando arredondamento, ordenacao de origens/fontes e filtro/ordenacao dos itens de granel. O router caiu de 1798 para 1746 linhas, com teste unitario cobrindo o formato final. Proximo passo: encerrar Compras/Pedidos nesta rodada ou escolher outro hotspot acima de 1000 linhas.
- 2026-06-23: `pedidos_compra_routes.py` moveu o calculo de cobertura/ruptura `_calcular_dias_com_estoque` para `backend/app/pedidos_compra/sugestao.py`, mantendo a consulta de movimentacoes no router e cobrindo por teste o intervalo com estoque, ruptura e reposicao. O router caiu de 1746 para 1680 linhas. Proximo passo: encerrar Compras/Pedidos nesta rodada ou escolher outro hotspot acima de 1000 linhas.
- 2026-06-23: `pedidos_compra_routes.py` extraiu a montagem textual `_gerar_observacao` para `backend/app/pedidos_compra/sugestao.py`, preservando mensagens de ruptura, tendencia, ausencia de venda e fallback de estoque adequado com teste unitario. O router caiu de 1680 para 1637 linhas. Proximo passo: encerrar Compras/Pedidos nesta rodada ou escolher outro hotspot acima de 1000 linhas.
- 2026-06-23: `pedidos_compra_routes.py` extraiu o calculo de tendencia de vendas para `_calcular_tendencia_vendas_sugestao`, preservando os limiares de crescimento/queda/estavel e o fallback `N/A` para periodo curto ou sem consumo observado. O router caiu de 1637 para 1633 linhas, com teste unitario cobrindo todos os caminhos. Proximo passo: encerrar Compras/Pedidos nesta rodada ou escolher outro hotspot acima de 1000 linhas.
- 2026-06-23: `pedidos_compra_routes.py` extraiu o planejamento de compra da sugestao inteligente para `_calcular_planejamento_compra_sugestao`, reunindo consumo observado/recente, ajuste por ruptura, cobertura alvo, quantidade sugerida, lead time e prioridade. O router caiu de 1633 para 1586 linhas, com teste unitario cobrindo ajuste por ruptura e prioridade critica. Proximo passo: encerrar Compras/Pedidos nesta rodada ou escolher outro hotspot acima de 1000 linhas.
- 2026-06-23: `pedidos_compra_routes.py` extraiu a montagem do item final da sugestao para `_montar_item_sugestao_compra`, preservando payload operacional, arredondamentos, vendas por janela, ruptura, estoque derivado e observacao. O router caiu de 1586 para 1521 linhas, com teste unitario cobrindo o contrato do item. Proximo passo: encerrar Compras/Pedidos nesta rodada ou escolher outro hotspot acima de 1000 linhas.
- 2026-06-23: `pedidos_compra_routes.py` extraiu a deduplicacao dos vinculos fornecedor/produto e a montagem da resposta final para `_selecionar_produtos_fornecedor_sugestao` e `_montar_resposta_sugestao_compra`. A fatia preserva preferencia por fornecedor selecionado/principal, ordenacao por prioridade, resumo e sanitizacao JSON. O router caiu de 1521 para 1486 linhas, com testes unitarios cobrindo selecao e resposta final.
- 2026-06-23: `pedidos_compra_routes.py` moveu os helpers de consulta da sugestao para `backend/app/pedidos_compra/sugestao_queries.py`, reunindo resolucao de fornecedores/grupos, carga de vendas/conversoes/movimentacoes, agrupamento de movimentacoes de estoque e estoque virtual. O router caiu de 1486 para 1253 linhas, com teste unitario cobrindo os caminhos basicos sem consulta ao banco e compilacao dos modulos passando.
- 2026-06-23: `vendas_routes.py` iniciou a fatia backend de Vendas/Comissoes extraindo os helpers de reprocessamento, SQL tenant-safe, total pago, contagem e remocao de comissoes para `backend/app/vendas/comissoes.py`, preservando os nomes reexportados pelo router. O router caiu de 2236 para 2115 linhas, com testes de comissao e tenant-safe SQL passando.
- 2026-06-23: `vendas_routes.py` extraiu tambem os schemas Pydantic de entrada para `backend/app/vendas/schemas.py`, mantendo os mesmos nomes importados pelo router (`CriarVendaRequest`, `FinalizarVendaRequest`, `MarcarEntregueRequest` etc.). Na branch atual recalculada, o router esta com 2398 linhas; restam 79 arquivos de aplicacao com 1000+ linhas quando testes, migrations e builds sao excluidos.
- 2026-06-23: `dashboard_routes.py` recebeu uma fatia maior de Ponto de Equilibrio: calculos/classificacoes foram para `backend/app/dashboard/ponto_equilibrio.py` e os endpoints foram para `backend/app/dashboard/ponto_equilibrio_routes.py`, mantendo reexports no router principal. O arquivo principal caiu de 2227 para 762 linhas e saiu da lista de arquivos grandes; restam 78 arquivos de aplicacao com 1000+ linhas.
- 2026-06-23: `clientes_routes.py` foi dividido em subrouters dedicados para financeiro/historicos, pets, credito, parceiros/entregadores e duplicidades/fusao (`backend/app/clientes/*_routes.py`), preservando paths e reexports no router principal. O arquivo principal caiu de 2661 para 903 linhas e saiu da lista de arquivos grandes; restam 77 arquivos de aplicacao com 1000+ linhas.
- 2026-06-23: `dre_canais_routes.py` virou uma fachada de compatibilidade e a implementacao da DRE por canal foi dividida em `backend/app/dre_canais/schemas.py`, `base.py`, `agregacao.py`, `linhas.py`, `detalhes.py` e `routes.py`. O arquivo principal caiu de 2485 para 72 linhas, o codigo morto apos o retorno do endpoint principal foi removido e todos os modulos novos ficaram abaixo de 1000 linhas; restam 76 arquivos de aplicacao com 1000+ linhas.
- 2026-06-23: `backend/app/nfe/listagem.py` virou uma fachada de compatibilidade e a listagem/sincronizacao de NF-e/NFC-e foi dividida em `listagem_base.py`, `listagem_cache.py`, `listagem_xml.py`, `listagem_normalizacao.py`, `listagem_detalhes.py`, `listagem_pedidos.py` e `listagem_sync.py`. O arquivo principal caiu de 2315 para 117 linhas e saiu da lista de arquivos grandes; restam 75 arquivos de aplicacao com 1000+ linhas.
- 2026-06-23: `backend/app/vendas/service.py` teve a criacao de vendas extraida para `backend/app/vendas/criacao.py`, preservando `VendaService.criar_venda` como fachada e os callbacks de numeracao/baixa de estoque usados pelos testes. O service caiu de 2204 para 2029 linhas; na contagem atual de `backend/app` + `frontend/src`, restam 53 arquivos acima de 1000 linhas.
- 2026-06-23: `backend/app/vendas_routes.py` passou a agregar subrouters de pagamentos e devolucoes (`backend/app/vendas/pagamentos_routes.py` e `backend/app/vendas/devolucoes_routes.py`) e helpers compartilhados em `backend/app/vendas/routes_common.py`, preservando os nomes antigos reexportados pelo router. O arquivo principal caiu de 2400 para 1655 linhas fisicas; na contagem fisica atual de `backend/app` + `frontend/src`, restam 69 arquivos acima de 1000 linhas e 9 acima de 2000.

### Nao fazer nesta onda

- Nao reescrever arquivos gigantes inteiros.
- Nao mexer em regra de negocio junto com refator visual grande.
- Nao trocar todos os botoes do sistema em massa sem validar por modulo.
- Nao criar mais um componente se `ActionButton`, `Panel`, `StatusBadge`, `MetricCard` ou `TutorPetSelector` ja resolverem.

## Onda 2 - Regras centrais auditaveis

Depois da fundacao visual, atacar a logica sensivel com pouco ruido visual.

| Dominio | Primeira entrega concreta |
| --- | --- |
| Campanhas | Extrato/ledger geral: credito, debito, conversao, estorno, origem, saldo |
| Carimbos/cupons | Reconciliador: parametro X carimbos = 1 cupom, independente do caminho |
| Comissoes | Reconciliador por venda: se tem comissao configurada, gera/atualiza/estorna |
| Estoque | Extrato unico por produto: venda, compra, ajuste, cancelamento, NF, kit |
| Financeiro/caixa | Evento unico para venda criada/editada/cancelada/reaberta/baixada |
| DRE | Snapshot/recalculo auditavel por periodo e origem |

### Nome tecnico interno

Usar o termo **orquestradores/reconciliadores de dominio com ledger**.

Na pratica:

- Orquestrador: decide o que precisa acontecer quando uma entidade muda.
- Reconciliador: confere e corrige o estado final esperado.
- Ledger/extrato: registra por que houve credito, debito, estorno, cupom, comissao ou ajuste.

## Proximo passo recomendado

Ao retomar, antes de abrir nova frente grande, fazer uma rodada curta de go-live:

1. Rodar `scripts/smoke_golive.py` em modo publico com `GOLIVE_PUBLIC_ONLY=true`.
2. Rodar `scripts/smoke_golive.py` em modo autenticado com credenciais seguras de operador.
3. Testar permissoes por perfil real (`admin`, `vendedor`, `financeiro`, `entregador`) nas telas criticas.
4. Validar webhooks publicos/externos com segredo, assinatura ou token quando o provedor permitir.
5. Confirmar onboarding de novo tenant: cadastro, confirmacao de e-mail, aceite LGPD/termos, primeiro login e selecao de tenant.
6. Confirmar manualmente `/ops/tenants` em producao e rodar somente simulacao do catalogo base para um tenant real antes de liberar aplicacao.
7. Depois disso, voltar para a refatoracao visual/padronizacao da Onda 1.

Continuar a **Onda 1** com uma destas frentes, conforme prioridade operacional:

- **Financeiro/Vendas**: seguir a padronizacao de tabelas, filtros e status.
- **Pessoas/Pets/PDV**: transformar os blocos de cliente/pet/produto em `EntityCard` reutilizavel.
- **Banho & Tosa**: proxima etapa deve ser funcional, nao visual: validar regra de entrega -> venda PDV, pacotes/creditos, reagendamento e relatorios com dados reais.

Entrega esperada:

1. Levar `MoneyCell`/`NumberCell` para DRE, contas a pagar/receber e compras.
2. Levar `FilterBar` para Financeiro/Vendas, Produtos e Compras.
3. Preparar `DataTable` sem reescrever a tela inteira.
4. Padronizar `StatusBadge` em vendas, contas e compras.
5. Rodar build e validar visual local a cada fatia.

---

<!-- Origem consolidada: docs/DESIGN_SYSTEM_UI.md -->

# Design System UI - Sistema Pet

Este documento define regras visuais obrigatorias para novas telas, refactors e componentes reutilizaveis do frontend.

## Principios

- Antes de criar um componente novo, procurar componente existente em `frontend/src/components`.
- Regras de negocio nao devem ficar presas na tela; a tela coleta dados e chama uma regra/servico central.
- Componentes compartilhados devem manter o mesmo comportamento, cor, fonte, espacamento e estados em todos os modulos.
- Evitar cor por modulo quando a cor representa acao. A cor da acao deve ter o mesmo significado em todo o sistema.
- Usar icone quando a acao for reconhecivel, com texto quando a acao precisar ser explicitada.
- Manter botoes, campos e cards com densidade operacional: profissional, legivel e sem excesso decorativo.

## Regra de cores por acao

| Acao semantica | Uso | Cor padrao |
| --- | --- | --- |
| `create` | Novo, adicionar, cadastrar, incluir | verde/emerald |
| `edit` | Editar, salvar alteracao, atualizar cadastro | azul |
| `delete` | Excluir, remover, cancelar destrutivo | vermelho |
| `neutral` | Fechar, voltar, limpar, atualizar lista, navegar | slate/cinza |
| `warning` | Alerta, conflito, pendencia, acao sensivel reversivel | amber |

Exemplos:

- `+ Novo pet` usa `create`, portanto sempre verde.
- `Editar pessoa` usa `edit`, portanto sempre azul.
- `Excluir venda` usa `delete`, portanto sempre vermelho.
- `Atualizar` usa `neutral`, exceto quando for uma acao de gravacao.
- `Cancelar venda` usa `delete` se muda estado de negocio de forma destrutiva.
- `Cancelar modal` usa `neutral`, porque apenas fecha a interface.

## Implementacao no codigo

A fonte inicial de classes semanticas fica em:

`frontend/src/components/ui/actionStyles.js`

Use `actionButtonClasses` em novos botoes e em refactors graduais:

```jsx
import { actionButtonClasses } from "../ui/actionStyles";

<button className={actionButtonClasses({ intent: "create", tone: "soft", size: "sm" })}>
  Novo pet
</button>
```

Evite classes diretas como `bg-orange-600`, `text-cyan-700` ou `border-blue-200` em botoes de acao quando existir uma intencao semantica clara.

## Checklist para novas alteracoes frontend

- O componente existente foi procurado antes de criar outro?
- A cor do botao vem da intencao da acao, nao do gosto da tela?
- O mesmo componente fica igual em Consulta, Banho & Tosa, PDV e demais modulos?
- Estados `disabled`, `hover`, carregamento e erro estao previstos?
- O texto cabe no mobile e no desktop?
- A tela ficou operacional e escaneavel, sem estilo de landing page?

---

<!-- Origem consolidada: docs/AUDITORIA_ENTERPRISE_SISTEMA_2026-03-29.md -->

# Auditoria Enterprise do Sistema Pet

Data: 29/03/2026  
Responsável pela análise: Codex + MCP (SSH, health checks, Chrome DevTools, Lighthouse)

## 1. Resumo executivo

O sistema já tem amplitude de ERP real: operação, estoque, fiscal, Bling, veterinário, financeiro, entregas, campanhas, e-commerce, IA e administração em uma única base. A estrutura funcional é rica, mas a sustentação técnica ainda mistura peças enterprise com heranças de crescimento rápido.

Diagnóstico direto:

- O produto já tem valor de negócio e profundidade operacional.
- O frontend e o backend cresceram com alta velocidade, mas vários módulos ficaram grandes demais e acoplados demais.
- A plataforma precisa agora de uma fase explícita de consolidação: observabilidade, padronização de UI, redução de arquivos monolíticos, estratégia de testes por fluxo crítico e pipeline de release mais previsível.
- Se essa fase não vier agora, o custo de mudança vai subir rápido principalmente em PDV, produtos, campanhas, compras/XML, comissões e financeiro.

## 2. O que aconteceu no Monitor Bling e o que foi corrigido

### Problema real

O sistema estava "vivendo no futuro" porque os eventos do monitor estavam sendo gravados e entregues como horário UTC sem contexto visual claro. Na prática:

- O banco guardava `processed_at` sem timezone explícito.
- A API devolvia esse valor sem offset.
- O frontend exibia a data como se ela já fosse horário local.
- Resultado: um evento processado às `20:22 UTC` parecia `20:22` na interface, quando em Brasília o correto seria `17:22`.

### Correção aplicada

A correção entrou em duas pontas:

- Backend: o monitor agora serializa `processed_at` com offset explícito em UTC, por exemplo `2026-03-29T20:22:57.353865+00:00`.
- Frontend: a tela do monitor converte sempre para `America/Sao_Paulo` antes de exibir.
- Fluxo Bling: foi adicionado o evento `invoice.linked_to_order`, registrando explicitamente o vínculo pedido/NF quando a relação é confirmada.
- UX do monitor: a timeline agora explica melhor o que aconteceu, o resultado, as referências do evento e ganhou tooltips para reduzir ambiguidade operacional.

### Deploy em produção

Status do deploy feito hoje:

- Commit publicado em produção: `0f4c1c5d feat: improve bling monitor timeline and event clarity`
- Backend reconstruído via Docker Compose
- Migração executada com `alembic upgrade head`
- Frontend rebuildado no próprio servidor
- `nginx` reiniciado
- Container órfão `petshop-prod-frontend` removido
- Health check validado em `https://mlprohub.com.br/api/health`

Validação técnica da correção:

- O backend em produção agora serializa o evento recente `order.updated` como `2026-03-29T20:22:57.353865+00:00`
- A mesma data, convertida para `America/Sao_Paulo`, vira `29/03/2026, 17:22`
- Isso elimina o efeito de "horário no futuro"

Observação operacional:

- Se algum navegador mantiver JavaScript antigo em cache, um `Ctrl+F5` ainda pode ser necessário em estações que estavam abertas durante o deploy.

## 3. Método da auditoria

Esta auditoria foi montada combinando:

- leitura estrutural de rotas em `frontend/src/App.jsx`
- leitura do menu real em `frontend/src/components/Layout.jsx`
- leitura de tours guiados em `frontend/src/tours/tourDefinitions.js`
- inspeção pública da landing page com Chrome DevTools MCP
- Lighthouse na landing page publicada
- inspeção de produção via SSH MCP
- leitura de arquivos críticos de backend, frontend e testes

Escopo técnico contado nesta análise:

- `543` arquivos Python em `backend/app`
- `182.154` linhas aproximadas no backend
- `262` arquivos JS/JSX/TS/TSX em `frontend/src`
- `133.088` linhas aproximadas no frontend
- `58` arquivos de teste
- `17.651` linhas aproximadas de testes
- `113` rotas declaradas no frontend
- `103` lazy imports declarados no frontend

Observação importante:

Este documento mapeia telas, rotas e CTAs principais de negócio. Ele cobre bem o sistema em nível operacional e arquitetural. Para um inventário literal de "todo microbotão de toda tela autenticada", o próximo passo ideal é um crawler autenticado com Playwright gravando DOM, screenshot e eventos por rota.

## 4. Mapa funcional do sistema

### 4.1 Público, entrada e jornada comercial

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Público | `/landing` | `Quero uma demonstração`, `Ver funcionalidades`, `Falar com vendas`, `Já sou cliente` | Boa porta comercial; precisa SEO e acessibilidade melhores |
| Público | `/login` | `Entrar`, seleção de tenant | Fluxo central para multi-tenant; merece telemetria de falhas por etapa |
| Público | `/register` | `Cadastrar` | Útil, mas precisa política clara de quem pode auto-registrar |
| Público | `/rastreio/:token` | consulta de status de entrega | Boa vitrine operacional; ideal ter analytics e fallback amigável |
| Público | `/ecommerce`, `/:tenantId` | navegação da loja, compra, vitrine | Deve ser tratado como produto separado de storefront |

### 4.2 Operação geral

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Operação | `/dashboard` | atalhos de venda, cadastro de cliente, cadastro de produto | Dashboard bom para operação; precisa contrato claro de KPIs |
| Operação | `/dashboard-gerencial` | filtros, leitura de indicadores, visão executiva | Deve virar cockpit executivo padronizado |
| Operação | `/lembretes` | `Novo Lembrete`, filtros, lista | Bom para rotina; precisa regras de prioridade e SLA |
| Operação | `/calculadora-racao` | cálculo, busca de perfil, recomendação | Diferencial de produto; merece camada própria de domínio |
| Operação | `/ajuda` | navegação de ajuda, abertura de suporte | Deve integrar base de conhecimento versionada |
| Operação interna | `/organizador-bradesco` | caso especial / ferramenta interna | Hoje parece rota de exceção; ideal esconder atrás de feature flag |

### 4.3 Clientes, pets e veterinário

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Clientes | `/clientes` | `Cadastrar Nova Pessoa`, `Importação em Massa`, busca, filtros, editar | Tela central e crítica; merece service layer e tabela padronizada |
| Clientes | `/clientes/:clienteId/financeiro` | ver histórico financeiro do cliente | Precisa acoplamento formal com contas a receber e crédito |
| Clientes | `/clientes/:clienteId/timeline` | navegar eventos do cliente | Bom conceito; precisa links profundos por tipo de evento |
| Pets | `/pets` | listar, buscar, abrir ficha, criar | Fluxo bom; pode evoluir para visão CRM pet-centric |
| Pets | `/pets/novo`, `/pets/:petId`, `/pets/:petId/editar` | salvar, editar, anexar histórico | Precisa contratos de saúde e histórico mais coesos |
| Veterinário | `/veterinario` | cards executivos, atalhos para agenda, vacinas, internações, catálogos | Excelente base para vertical clínica |
| Veterinário | `/veterinario/agenda` | agenda, filtro, abrir consulta | Ideal ter calendário compartilhado e capacidade/slotting |
| Veterinário | `/veterinario/consultas`, `/veterinario/consultas/nova`, `/veterinario/consultas/:consultaId` | listar, nova consulta, editar prontuário | Merece domínio próprio de prontuário e templates clínicos |
| Veterinário | `/veterinario/exames` | anexar, filtrar por período, revisar | Precisa storage, preview e trilha de auditoria por arquivo |
| Veterinário | `/veterinario/ia` | apoio clínico por IA | Deve ter guardrails e rastreabilidade por resposta |
| Veterinário | `/veterinario/calculadora-doses` | cálculo de dose | Alto valor; precisa validação farmacológica formal |
| Veterinário | `/veterinario/vacinas` | abas `Por pet`, `A vencer`, `Calendário Preventivo` | Muito bom; merece automação com lembretes/campanhas |
| Veterinário | `/veterinario/internacoes` | abas `Ativas`, `Histórico`; visões `Widget`, `Mapa`, `Lista`, `Agenda` | Forte diferencial; componente grande demais para manter assim |
| Veterinário | `/veterinario/catalogo` | gerir catálogos clínicos | Deve migrar para master data estruturado |
| Veterinário | `/veterinario/configuracoes` | parametrizações clínicas | Precisa versionamento e trilha de mudança |
| Veterinário | `/veterinario/repasse` | acompanhar repasses parceiros | Bom módulo financeiro vertical; pede integração com comissões |

### 4.4 Produtos, estoque, compras e Bling

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Produtos | `/produtos` | `Novo Produto`, `Importar do Excel`, busca, filtros, editar, ajustar estoque | Núcleo crítico; precisa quebrar tela e API por contexto |
| Produtos | `/produtos/novo`, `/produtos/:id/editar` | salvar, cancelar, dados fiscais/comerciais | Cadastro precisa schemas compartilhados frontend/backend |
| Estoque | `/produtos/:id/movimentacoes` | `Incluir lançamento`, `Forçar sync no Bling`, `Abrir painel Bling` | Tela importante e já melhorou; merece trilha de eventos mais rica |
| Estoque | `/produtos/relatorio` | filtros e relatório de movimentações | Ideal consolidar em read model próprio |
| Estoque | `/produtos/balanco` | balanço e inventário | Fluxo sensível; precisa operação em lote e reconciliação auditável |
| Estoque | `/estoque/alertas` | dashboard, filtros, revisão de alertas | Ótimo para operação; precisa ranking de criticidade |
| Estoque | `/estoque/full-nf` | visão de movimentação completa por NF | Deve ser a base de auditoria fiscal-operacional |
| Bling | `/produtos/sinc-bling` | sincronizar produtos/estoque/cadastro | Integração estratégica; precisa fila, retry e painel técnico |
| Compras | `/compras/pedidos` | criar pedido, sugestão de compra, aprovar itens | Forte, mas componente grande demais |
| Compras | `/compras/entrada-xml` | upload XML, upload em lote, vincular produto, rateio, quantidade online | Fluxo potente e muito sensível; precisa divisão em submódulos |
| Bling Vendas | `/vendas/bling-pedidos` | revisar pedidos, sincronizar, inspecionar origem | Ideal separar operação assistida de operação automática |
| Bling Monitor | `/vendas/bling-monitor` | `Atualizar`, `Rodar auditoria`, leitura de incidentes e eventos | Agora está melhor; pode evoluir para observabilidade operacional de integração |
| Compras legado | `/compras/bling` | redirect para sinc de Bling | Redirect útil, mas é sinal de IA/API velha ainda convivendo |

### 4.5 PDV, caixas e fiscal

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| PDV | `/pdv` | buscar cliente, buscar produto, gerenciar carrinho, aplicar desconto, `Finalizar Venda` | Um dos maiores riscos de manutenção por volume e criticidade |
| Caixas | `/meus-caixas` | `Abrir Caixa`, registrar entradas/saídas, histórico | Precisa fechamento operacional e auditoria mais explícitos |
| Fiscal | `/notas-fiscais/saida` | filtrar, visualizar detalhe, imprimir, baixar, inspecionar NF | Ideal ter estados fiscais mais consistentes e timeline por NF |
| Fiscal | `/notas-fiscais/entrada` | consultar/importar entradas | Deve conversar melhor com XML/estoque/custos |
| Fiscal | `/notas-fiscais`, `/notas-fiscais/vendas` | redirects para saída | Bom para usabilidade, mas indica rotas históricas acumuladas |
| Fiscal | `/fiscal/sefaz` | redirect para entrada XML | Melhor renomear ou consolidar nomenclatura |

### 4.6 Financeiro

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Financeiro | `/financeiro` | dashboard executivo financeiro | Deve ser a home financeira padronizada |
| Financeiro | `/financeiro/vendas` | filtros, análise de venda líquida, margem, exportação | Muito importante; precisa contratos de KPI e performance |
| Financeiro | `/financeiro/relatorio-vendas` | análise / exportação | Pode ser consolidado com `financeiro/vendas` |
| Financeiro | `/financeiro/contas-pagar` | criar conta, classificar, registrar pagamento | Fluxo forte, mas merece wizard e validações padronizadas |
| Financeiro | `/financeiro/contas-receber` | criar conta, filtrar, registrar recebimento | Precisa melhor conciliação com crédito e cliente |
| Financeiro | `/financeiro/conciliacao-3abas` | conciliar vendas, recebimentos e amarração | Domínio importante; deveria ser produto interno isolado |
| Financeiro | `/financeiro/historico-conciliacoes` | revisar históricos | Precisa rastreabilidade por ação/usuário |
| Financeiro | `/financeiro/conciliacao-bancaria` | upload OFX, classificar, estatísticas, regras | Alto valor; merece motor de regras versionado |
| Financeiro | `/financeiro/fluxo-caixa` | visão de entradas e saídas | Pode ser read model consolidado |
| Financeiro | `/financeiro/dre` | análise DRE, exportação | Precisa camada contábil mais formal |

### 4.7 Comissões

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Comissões | `/comissoes` | configurar regras, duplicar configuração, salvar | Tela sensível e extensa; precisa motor declarativo |
| Comissões | `/comissoes/demonstrativo` | listar e filtrar demonstrativos | Ideal como read model estável |
| Comissões | `/comissoes/abertas` | revisar comissões em aberto | Boa operação; precisa SLA e alertas |
| Comissões | `/comissoes/fechamento/:funcionario_id` | conferência avançada, ajustes | Fluxo crítico, merece testes E2E dedicados |
| Comissões | `/comissoes/fechamentos` | histórico de fechamentos | Precisa snapshot imutável mais explícito |
| Comissões | `/comissoes/fechamentos/detalhe` | detalhe de fechamento | Boa transparência; merece deep links |
| Comissões | `/comissoes/relatorios` | relatórios analíticos e exportação | Excelente para gestão; pede cache e agregações |

### 4.8 Campanhas, e-commerce e entregas

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Campanhas | `/campanhas` | criar, ativar, pausar, acompanhar | Diferencial comercial; precisa runtime configurável sem deploy |
| Campanhas | `/campanhas/canais` | configurar canais e descontos | Precisa governança por tenant e por canal |
| E-commerce | `/ecommerce/aparencia` | editar vitrine/aparência | Deve convergir para CMS leve ou theme system |
| E-commerce | `/ecommerce/configuracoes` | parâmetros da loja | Precisa feature flags e preview |
| E-commerce | `/ecommerce/analytics` | analytics da loja | Ideal ligar com eventos padronizados |
| Entregas | `/entregas/abertas` | listar entregas, filtrar, iniciar rota | Fluxo operacional direto |
| Entregas | `/entregas/rotas` | montar rota, acompanhar paradas | Merece otimização e telemetria de rota |
| Entregas | `/entregas/historico` | histórico e consulta | Precisa indicadores por entregador/rota |
| Entregas | `/entregas/financeiro` | dashboard financeiro de entregas | Ótimo para custo real da operação |

### 4.9 Cadastros, RH, IA, administração e configurações

| Módulo | Tela / rota | Botões / ações principais | Leitura enterprise |
|---|---|---|---|
| Cadastros | `/cadastros/cargos` | criar, editar, ordenar | Master data precisa padrão único |
| Cadastros | `/cadastros/departamentos` | criar, editar, pesquisar | Base de governança organizacional |
| Cadastros | `/cadastros/categorias` | criar, hierarquizar, editar | Precisa taxonomia central versionada |
| Cadastros | `/cadastros/categorias-financeiras` | criar e relacionar categorias | Fundamental para DRE e conciliação |
| Cadastros | `/cadastros/especies-racas` | gerenciar espécies/raças | Ideal como catálogo reutilizável |
| Cadastros | `/cadastros/opcoes-racao` | gerir linhas, portes, fases, tratamentos, sabores, apresentações | Diferencial forte, pede administração orientada a domínio |
| Cadastros financeiros | `/cadastros/financeiro/bancos`, `/formas-pagamento`, `/operadoras` | criar, editar, ativar | Deve ser governado por tabelas de referência |
| RH | `/rh/funcionarios` | cadastro, eventos e movimentações | Precisa trilha documental e integrações futuras |
| IA | `/ia/chat` | conversar com assistente | Precisa observabilidade, custo e guardrails |
| IA | `/ia/fluxo-caixa` | análise preditiva | Ótimo piloto; precisa medição de acurácia |
| IA | `/ia/whatsapp` | painel do bot, fila, handoff | Domínio forte; precisa observabilidade de sessão |
| IA | `/ia/alertas-racao` | alertas e insights de ração | Bom caso de uso de IA aplicada |
| Administração | `/admin/usuarios` | criar usuário, ativar, revisar acesso | Precisa RBAC formal com auditoria |
| Administração | `/admin/roles` | criar e editar permissões | Bom pilar de enterprise readiness |
| Configurações | `/configuracoes` | cards de acesso às configurações | Pode virar portal administrativo único |
| Configurações | `/configuracoes/fiscal` | parametrização fiscal | Precisa versionamento e validação de consistência |
| Configurações | `/configuracoes/geral` | margens, metas, mensagens | Precisa histórico de alterações |
| Configurações | `/configuracoes/entregas` | parâmetros de entregas | Deve alimentar simulação e custo real |
| Configurações | `/configuracoes/custos-moto` | custos operacionais | Fundamental para margem por entrega |
| Configurações | `/configuracoes/estoque` | parâmetros de estoque | Precisa impacto auditável |
| Configurações | `/configuracoes/integracoes` | Stone, Bling e integrações | Merece health por conector e token status |
| Configurações | `/configuracoes/simples/fechamento` | rota ainda não consolidada | Deve virar feature formal ou ser removida |
| Apoio | `/auditoria/provisoes`, `/projecao-caixa`, `/simulacao-contratacao` | auditoria, simulação, projeção | Bom material de inteligência gerencial |

## 5. Principais warnings e sinais de dívida técnica

### 5.1 Estrutura e manutenibilidade

- Existem arquivos extremamente grandes e de alto risco de manutenção:
  - `frontend/src/pages/Campanhas.jsx` com `6134` linhas
  - `frontend/src/pages/PDV.jsx` com `6112` linhas
  - `frontend/src/pages/ClientesNovo.jsx` com `4197` linhas
  - `frontend/src/pages/ProdutosNovo.jsx` com `4032` linhas
  - `backend/app/veterinario_routes.py` com `4780` linhas
  - `backend/app/produtos_routes.py` com `4677` linhas
  - `backend/app/campaigns/routes.py` com `3445` linhas
  - `backend/app/notas_entrada_routes.py` com `3184` linhas

- Há mistura forte de estilos e tecnologias no frontend:
  - `208` arquivos `.jsx`
  - `25` arquivos `.js`
  - `17` arquivos `.tsx`
  - `12` arquivos `.ts`

- Há sinais de rotas duplicadas ou históricas convivendo no mesmo arquivo:
  - `produtos` duplicada
  - `produtos/novo` duplicada
  - `produtos/:id/editar` duplicada
  - `subcategorias` duplicada

- Há arquivos legados ou backups dentro da árvore principal de código:
  - `frontend/src/components/DRE.jsx.backup`
  - `frontend/src/components/DRE.jsx.original`
  - `frontend/src/components/DRE_temp.jsx`
  - `frontend/src/pages/ConciliacaoCartoes_backup_pre_6ajustes.jsx`
  - `backend/app/conciliacao_routes_old.py`
  - `backend/app/notas_entrada_routes_backup_20260205_181349.py`
  - `backend/app/vendas_routes.py.backup_indent`
  - `backend/app/whatsapp/analytics_backup.py`

### 5.2 Observabilidade e ruído operacional

- Foram encontrados `927` usos de `console.*` no frontend/backend/testes analisados.
- Foram encontrados `143` `TODO`s espalhados no código.
- Há páginas com logs de debug em produção em excesso, principalmente:
  - XML/entrada
  - comissões
  - conciliação
  - clientes
  - sockets/WhatsApp

Recomendação:

- classificar logs em `debug`, `info`, `warn`, `error`
- remover `console.log` de fluxo feliz em produção
- adotar logger com correlação por request e tenant no frontend também

### 5.3 Release e build

- O deploy do frontend é frágil porque `frontend/dist/index.html` está versionado, mas `frontend/dist/assets` está ignorado. Isso favorece cenários de `index.html` apontando para chunks inexistentes.
- Em produção havia um container órfão `petshop-prod-frontend`, já removido hoje.
- Existe artefato temporário no frontend:
  - `frontend/vite.config.js.timestamp-1772152671678-80b7d14fdf2a.mjs`

Recomendação:

- escolher um único modelo de entrega do frontend:
  - ou versionar `dist` completo
  - ou nunca versionar `dist` e sempre buildar no servidor/CI
  - ou gerar artefato imutável no CI e publicar por release

### 5.4 Performance percebida

Pontos observados:

- Muitos lazy imports ajudam, mas a base ainda gera chunks grandes.
- A build recente mostrou bundles pesados em módulos específicos.
- O sistema tem telas enormes que provavelmente re-renderizam demais e acumulam estado demais.

Risco prático:

- páginas como PDV, Campanhas, XML e Produtos tendem a concentrar bugs de regressão visual, lentidão, memória e acoplamento.

### 5.5 Qualidade de documentação e contrato

- O `README.md` da raiz afirma `React 19`, mas `frontend/package.json` está em `React 18.2.0`.
- Há documentação muito rica, mas parcialmente divergente da implementação.
- Falta um "source of truth" curto para:
  - rotas oficiais
  - fluxos críticos
  - padrões de UI
  - arquitetura por domínio
  - política de observabilidade

## 6. Resultado da landing page pública

Auditoria Lighthouse na landing publicada:

- Accessibility: `87`
- Best Practices: `100`
- SEO: `82`

Falhas objetivas registradas:

- contraste insuficiente em alguns textos
- ausência de landmark `main`
- ausência de meta description
- `robots.txt` inválido

Leitura:

- a landing é boa comercialmente, mas ainda não está com acabamento SEO/acessibilidade de primeira linha

## 7. Como eu remodelaria a estrutura para padrão enterprise

### 7.1 Backend

Remodelagem proposta:

- quebrar rotas gigantes por domínio e por caso de uso
- mover lógica de negócio crítica para services/use-cases explícitos
- consolidar contratos de entrada/saída com schemas dedicados
- separar read models pesados de endpoints transacionais
- padronizar eventos de domínio para fiscal, estoque, vendas, campanhas e entregas

Estrutura alvo:

- `app/domains/<dominio>/routes.py`
- `app/domains/<dominio>/services/`
- `app/domains/<dominio>/use_cases/`
- `app/domains/<dominio>/repositories/`
- `app/domains/<dominio>/schemas/`
- `app/domains/<dominio>/events/`

Domínios que mais pedem esse redesenho:

- PDV/Vendas
- Produtos/Estoque
- Compras/XML
- Campanhas
- Comissões
- Financeiro/Conciliação
- Veterinário

### 7.2 Frontend

Remodelagem proposta:

- migrar páginas monolíticas para feature folders
- definir design system próprio com componentes de tabela, formulário, filtros, modal, badge, estado vazio e timeline
- centralizar fetch, cache e invalidação por domínio
- padronizar tabela/paginação/exportação/filtro
- padronizar loading, erro, retry, empty state e skeletons

Estrutura alvo:

- `src/features/<dominio>/pages`
- `src/features/<dominio>/components`
- `src/features/<dominio>/api`
- `src/features/<dominio>/hooks`
- `src/features/<dominio>/schemas`
- `src/shared/ui`
- `src/shared/layout`
- `src/shared/lib`

### 7.3 Dados e integrações

Remodelagem proposta:

- criar trilha de eventos unificada para pedidos, NFs, estoque e financeiro
- manter IDs externos e internos normalizados em uma camada de integração
- diferenciar claramente:
  - evento recebido
  - evento processado
  - vínculo confirmado
  - side effect executado
  - erro e retry

Para Bling especificamente:

- cada timeline deve mostrar `recebido`, `correlacionado`, `vinculado`, `persistido`, `baixa de estoque`, `resultado final`
- incidentes precisam `causa`, `última tentativa`, `próxima tentativa`, `ação recomendada`

## 8. Prioridades práticas de melhoria

### Prioridade 1 - próximos 15 dias

- estabilizar pipeline de deploy do frontend e eliminar o risco `index.html` vs `assets`
- quebrar `PDV.jsx`, `Campanhas.jsx`, `ClientesNovo.jsx` e `ProdutosNovo.jsx`
- remover backups e arquivos legados da árvore principal
- reduzir `console.log` de produção nos módulos críticos
- criar contrato visual padrão para tabelas, filtros, ações e páginas de detalhe
- adicionar monitoramento de erro de frontend e backend

### Prioridade 2 - próximos 30 a 45 dias

- criar suite E2E dos fluxos críticos:
  - login
  - venda PDV
  - entrada XML
  - emissão/consulta NF
  - pedido Bling
  - monitor Bling
  - contas a pagar/receber
  - fechamento de comissões
- criar telemetria de negócio por tenant
- criar catálogo de eventos operacionais
- transformar conciliação, campanhas e compras/XML em features mais modulares

### Prioridade 3 - próximos 60 a 90 dias

- formalizar design system e documentação viva
- adotar feature flags por tenant e por módulo
- criar observabilidade distribuída ponta a ponta
- introduzir validação de performance e budget de bundles no CI
- separar storefront e painel administrativo em fronteiras mais claras

### 8.4 Plano vivo de execucao

Status desta trilha: em andamento

Itens ja executados:

- [x] corrigir timezone do Monitor Bling para exibir horario de Brasilia
- [x] explicar melhor os eventos do monitor com resultado, referencias e tooltips
- [x] registrar o vinculo pedido/NF no momento do evento com `invoice.linked_to_order`
- [x] restaurar rota e item de menu do Monitor Bling na sidebar
- [x] compactar a coluna de eventos recentes para mostrar so os 3 ultimos por padrao
- [x] corrigir a confirmacao do pedido Bling que impedia a baixa automatica de estoque em casos como a NF `010985`

Itens executados nesta etapa:

- [x] remover arquivos backup/legado da arvore principal:
  - `frontend/src/components/DRE.jsx.backup`
  - `frontend/src/components/DRE.jsx.original`
  - `frontend/src/components/DRE_temp.jsx`
  - `frontend/src/pages/ConciliacaoCartoes_backup_pre_6ajustes.jsx`
  - `backend/app/conciliacao_routes_old.py`
  - `backend/app/notas_entrada_routes_backup_20260205_181349.py`
- [x] melhorar a landing publica com:
  - `meta description`
  - landmark `main`
  - link de "pular para o conteudo"
  - `robots.txt` valido
  - `sitemap.xml` inicial
- [x] reduzir logs de debug em producao nos modulos criticos do frontend:
  - `PDV.jsx`
  - `ClientesNovo.jsx`
  - `ProdutosNovo.jsx`
  - `Campanhas.jsx` revisado sem necessidade de troca nesta etapa
  - helper central `frontend/src/utils/debug.js` criado para manter logs so em ambiente de desenvolvimento ou com `VITE_DEBUG_UI=true`
- [x] iniciar a decomposicao do `PDV.jsx` com uma extracao segura:
  - modal de cadastro rapido movido para `frontend/src/components/pdv/ModalCadastroCliente.jsx`
  - persistencia de paineis movida para `frontend/src/hooks/usePersistentBooleanState.js`
  - `PDV.jsx` reduzido sem alterar o fluxo principal de venda
- [x] continuar a decomposicao do `PDV.jsx` sem alterar a interface:
  - sidebar de vendas recentes movida para `frontend/src/components/pdv/PDVVendasRecentesSidebar.jsx`
  - `PDV.jsx` ficou responsavel apenas pelo estado e pelos handlers da sidebar
- [x] seguir a decomposicao do `PDV.jsx` sem alterar a interface:
  - painel lateral do cliente movido para `frontend/src/components/pdv/PDVClienteSidebar.jsx`
  - painel de oportunidades movido para `frontend/src/components/pdv/PDVOportunidadesSidebar.jsx`
  - `PDV.jsx` ficou mais focado na orquestracao dos estados e callbacks desses paineis
- [x] avancar na decomposicao do `PDV.jsx` sem alterar a interface:
  - painel do assistente movido para `frontend/src/components/pdv/PDVAssistenteSidebar.jsx`
  - `PDV.jsx` ficou responsavel apenas por passar o estado da conversa e o handler de envio
- [x] seguir limpando o `PDV.jsx` sem alterar a interface:
  - faixa de modo visualizacao movida para `frontend/src/components/pdv/PDVModoVisualizacaoBanner.jsx`
  - `PDV.jsx` ficou responsavel apenas pelos handlers de voltar, emitir NF, reabrir e editar
- [x] continuar a decomposicao do `PDV.jsx` sem alterar a interface:
  - modal de endereco movido para `frontend/src/components/pdv/PDVEnderecoModal.jsx`
  - modal de desconto por item movido para `frontend/src/components/pdv/PDVDescontoItemModal.jsx`
  - modal de desconto total movido para `frontend/src/components/pdv/PDVDescontoTotalModal.jsx`
  - `PDV.jsx` ficou mais focado na orquestracao do estado e dos callbacks desses modais
- [x] avancar no corpo principal do `PDV.jsx` sem alterar a interface:
  - card de cliente movido para `frontend/src/components/pdv/PDVClienteCard.jsx`
  - `PDV.jsx` ficou responsavel apenas por passar o estado, os handlers e as acoes desse fluxo
- [x] seguir reduzindo o corpo principal do `PDV.jsx` sem alterar a interface:
  - card de produtos/carrinho movido para `frontend/src/components/pdv/PDVProdutosCard.jsx`
  - `PDV.jsx` ficou mais focado em estado, callbacks e orquestracao do fluxo de itens
- [x] continuar a reducao do corpo principal do `PDV.jsx` sem alterar a interface:
  - resumo financeiro do carrinho movido para `frontend/src/components/pdv/PDVResumoFinanceiroCard.jsx`
  - `PDV.jsx` ficou responsavel apenas pelos estados e handlers de cupom, desconto e totais
- [x] seguir reduzindo o corpo principal do `PDV.jsx` sem alterar a interface:
  - card de comissao movido para `frontend/src/components/pdv/PDVComissaoCard.jsx`
  - bloco final de acoes movido para `frontend/src/components/pdv/PDVAcoesFooterCard.jsx`
  - `PDV.jsx` ficou mais focado na orquestracao dos handlers desses fluxos
- [x] continuar a reducao do corpo principal do `PDV.jsx` sem alterar a interface:
  - card de entrega movido para `frontend/src/components/pdv/PDVEntregaCard.jsx`
  - `PDV.jsx` ficou responsavel pelos handlers de endereco, entregador e taxas, sem manter o JSX detalhado desse fluxo
- [x] seguir limpando a estrutura do `PDV.jsx` sem alterar a interface:
  - alerta de drive movido para `frontend/src/components/pdv/PDVDriveAlertBanner.jsx`
  - cabecalho operacional movido para `frontend/src/components/pdv/PDVHeaderBar.jsx`
  - banners de caixa fechado e numero da venda movidos para `frontend/src/components/pdv/PDVInfoBanners.jsx`
  - card de observacoes movido para `frontend/src/components/pdv/PDVObservacoesCard.jsx`
  - camada restante de modais consolidada em `frontend/src/components/pdv/PDVModalsLayer.jsx`
  - `PDV.jsx` deixou de carregar JSX duplicado escondido e ficou mais focado em estado e callbacks
- [x] iniciar a extracao de hooks por fluxo no `PDV.jsx`:
  - logica do assistente IA e dos alertas de carrinho movida para `frontend/src/hooks/usePDVAssistente.js`
  - `PDV.jsx` deixou de concentrar estados, efeitos e chamadas de API desse fluxo
  - a abertura do painel do assistente passou a usar um handler unico de orquestracao
- [x] continuar a extracao de hooks por fluxo no `PDV.jsx`:
  - logica de oportunidades inteligentes movida para `frontend/src/hooks/usePDVOportunidades.js`
  - `PDV.jsx` deixou de concentrar busca, tracking e acoes do painel lateral de oportunidades
  - a abertura do painel de oportunidades passou a usar um handler unico de orquestracao
- [x] seguir tirando logica operacional de dentro do `PDV.jsx`:
  - fluxo de entrega movido para `frontend/src/hooks/usePDVEntrega.js`
  - `PDV.jsx` deixou de concentrar carregamento de entregadores, calculo de custo operacional e handlers de entrega
  - a sincronizacao do entregador ao carregar uma venda passou a ficar centralizada no hook
- [x] continuar a extracao de hooks operacionais do `PDV.jsx`:
  - fluxo de comissao movido para `frontend/src/hooks/usePDVComissao.js`
  - `PDV.jsx` deixou de concentrar busca de funcionarios com comissao, handlers do card e sincronizacao da venda carregada
  - a limpeza e reaplicacao do estado de comissao passaram a ficar centralizadas no hook
- [x] seguir tirando ciclo de vida da venda de dentro do `PDV.jsx`:
  - fluxo de carregar venda, buscar por numero, abrir pagamento, limpar PDV e reabrir venda movido para `frontend/src/hooks/usePDVVendaAtual.js`
  - `PDV.jsx` deixou de concentrar chamadas de API e montagem de estado desse fluxo
  - `PDV.jsx` caiu para `2005` linhas, mantendo a mesma interface operacional
- [x] continuar tirando persistencia da venda de dentro do `PDV.jsx`:
  - fluxo de salvar e atualizar venda movido para `frontend/src/hooks/usePDVSalvarVenda.js`
  - `PDV.jsx` deixou de concentrar payloads operacionais, sincronizacao de status por pagamento e logs de persistencia
  - `PDV.jsx` caiu para `1846` linhas, mantendo a mesma interface operacional
- [x] concluir a extracao do fluxo de analise e pagamento do `PDV.jsx`:
  - hook `frontend/src/hooks/usePDVAnalisePagamento.js` passou a ser a fonte unica dos handlers de analise, reabertura, exclusao, emissao de NF e recarga apos pagamento
  - `PDVModalsLayer`, `PDVHeaderBar` e `PDVModoVisualizacaoBanner` deixaram de depender do bloco legado inline da pagina
  - `PDV.jsx` caiu para `1715` linhas, mantendo a mesma interface operacional
- [x] extrair o fluxo de descontos, cupom e recalculo de totais do `PDV.jsx`:
  - hook `frontend/src/hooks/usePDVDescontos.js` criado para centralizar desconto por item, desconto total, cupom e recalculo financeiro do carrinho
  - `PDVResumoFinanceiroCard` e `PDVModalsLayer` passaram a consumir esse fluxo via hook, em vez de depender da logica inline da pagina
  - `PDV.jsx` caiu para `1499` linhas, mantendo a mesma interface operacional
- [x] extrair o fluxo de vendas recentes e drive do `PDV.jsx`:
  - hook `frontend/src/hooks/usePDVVendasRecentes.js` criado para centralizar filtros, listagem de vendas recentes, confirmacao de retirada e polling do drive
  - `PDVDriveAlertBanner` e `PDVVendasRecentesSidebar` passaram a consumir esse fluxo via hook, em vez de depender de efeitos e chamadas de API inline na pagina
  - `PDV.jsx` caiu para `1409` linhas, mantendo a mesma interface operacional
- [x] extrair o fluxo de cliente do `PDV.jsx`:
  - hook `frontend/src/hooks/usePDVCliente.js` criado para centralizar busca de cliente, selecao, pet, campanhas, vendas em aberto e copias operacionais
  - `PDVClienteCard`, o cadastro rapido e o refresh de vendas em aberto passaram a consumir esse fluxo via hook, em vez de depender de busca e chamadas de API inline na pagina
  - `PDV.jsx` caiu para `1296` linhas, mantendo a mesma interface operacional
- [x] extrair o fluxo de produtos e carrinho do `PDV.jsx`:
  - hook `frontend/src/hooks/usePDVProdutos.js` criado para centralizar busca de produto, sugestoes, leitura por scanner, adicao ao carrinho, quantidade, pet por item, remocao e expansao de KIT
  - `PDVProdutosCard` e a acao de lista de espera rapida passaram a consumir esse fluxo via hook, em vez de depender do bloco inline da pagina
  - `PDV.jsx` caiu para `968` linhas, mantendo a mesma interface operacional
- [x] extrair o bloco auxiliar restante do `PDV.jsx` para hooks de suporte:
  - hooks `frontend/src/hooks/usePDVEstoqueFiscal.js`, `frontend/src/hooks/usePDVEndereco.js` e `frontend/src/hooks/usePDVCaixaRacao.js` passaram a centralizar pendencias de estoque, calculo fiscal, modal de endereco, calculadora de racao e estado operacional do caixa
  - hooks `frontend/src/hooks/usePDVUIState.js` e `frontend/src/hooks/usePDVInicializacao.js` passaram a centralizar estado visual, restauracao de venda via URL/sessionStorage e handlers auxiliares do fluxo
  - `PDV.jsx` caiu para `631` linhas, mantendo a mesma interface operacional
- [x] extrair a montagem visual do `PDV.jsx` para componentes de composicao:
  - `frontend/src/components/pdv/PDVMainArea.jsx` passou a concentrar header, cards e rodape operacional do PDV
  - `frontend/src/components/pdv/PDVOverlays.jsx` passou a concentrar sidebars e camada de modais
  - `PDV.jsx` caiu para `561` linhas, mantendo a mesma interface operacional
- [x] persistir a listagem de NF do Bling em cache local no banco:
  - tabela `bling_notas_fiscais_cache` criada para armazenar resumos e detalhes de NF/NFC-e ja vistos
  - `GET /nfe/` passa a usar o cache persistente como fonte principal e sincroniza apenas uma janela incremental recente do Bling
  - NFs ja vinculadas em `vendas` e `pedidos_integrados` passam a alimentar o cache para evitar depender de trazer tudo do Bling a cada carregamento
- [x] acompanhar a mudanca de status das NFs do Bling sem engessar o fluxo:
  - o webhook de NF deixa de ignorar status intermediarios e passa a registrar `invoice.status_updated`
  - o cache local da NF passa a ser atualizado mesmo quando a nota ainda nao esta em status final
  - o pedido continua vinculado a NF ao longo da evolucao do status, e nao apenas no momento final
- [x] parar de perder dados da NF quando o payload do Bling chega incompleto:
  - `ultima_nf` passa a ser mesclada em vez de sobrescrita, preservando `numero`, `serie`, `chave` e `data_emissao`
  - a reconciliacao via detalhe da NF agora preenche `numero`, `serie` e `data_emissao` no cache local
  - notas que antes apareciam sem numero passam a ser corrigidas na proxima reconciliacao
- [x] tratar cancelamento de NF com efeito real no estoque:
  - cancelamento agora estorna a baixa de estoque ja feita para `pedido_integrado`
  - lotes consumidos por FIFO sao reabertos no cancelamento, devolvendo a quantidade ao lote correto
  - movimentacoes antigas ficam marcadas como `cancelado`, evitando estorno duplicado
- [x] fazer lote e validade do balanco refletirem no cadastro do produto:
  - entrada de estoque via balanco passa a ativar `controle_lote` automaticamente
  - lote existente recebe atualizacao de quantidade inicial, quantidade disponivel, custo e validade
  - a tela de edicao do produto passa a carregar os lotes mesmo em cadastros antigos onde o flag ainda estava desligado
- [x] criar reconciliacao automatica para NFs recentes ainda pendentes:
  - o botao `Atualizar` continua forçando `force_refresh=true` na tela de NF de saida
  - o cliente do Bling passa a renovar o token e repetir a consulta automaticamente em caso de `401 invalid_token`
  - o backend agora roda um job periodico para revisar NFs recentes em `Pendente` ou `Emitida DANFE`
  - foi criado um endpoint manual de reconciliacao para diagnostico operacional rapido

- [x] tornar a integracao de venda Bling estritamente dependente da NF:
  - confirmacao de pedido via webhook ou pela tela deixa de baixar estoque e deixa de marcar item como vendido
  - a consolidacao da venda passa a acontecer apenas quando a NF chega e e processada como fonte deterministica
  - a auditoria do fluxo deixa de reaplicar baixa de estoque em pedido confirmado quando ainda nao existe NF valida
  - a tela de movimentacoes do produto oculta saidas de `pedido_integrado` que nao tenham NF resolvida
- [x] endurecer a listagem de `Pedidos Bling` para evitar quebra operacional:
  - a rota passa a aceitar o alias `pedido` na URL alem de `busca`
  - um pedido com payload ruim nao derruba mais a listagem inteira durante a serializacao
  - a interface de confirmacao manual passa a explicar corretamente que o estoque aguardara a NF
- [x] blindar a auditoria automatica do Monitor Bling contra falhas de registry do SQLAlchemy:
  - o servico de auditoria agora bootstrapa explicitamente os modelos com relacionamentos por string antes de rodar
  - a execucao manual e automatica da auditoria deixa de depender de import indireto do `app.main`
  - foi adicionada validacao especifica para garantir esse bootstrap em processo isolado
- [x] reconciliar automaticamente NFs autorizadas que chegaram ao sistema mas nao consolidaram a baixa:
  - o backend agora cruza NFs autorizadas recentes do cache local com pedidos locais por `pedido_bling_id`, `pedido_bling_numero` e `numero_pedido_loja`
  - se a NF existir, o pedido existir e ainda houver item reservado sem `vendido_em`, a reconciliacao religa o vinculo e reaplica a baixa usando a NF como fonte de verdade
  - o scheduler passa a revisar esse cenario a cada 15 minutos, sem depender da API do Bling para enxergar uma NF que ja esta salva localmente
- [x] fazer o Monitor Bling mostrar o numero humano da NF tambem em incidentes sem pedido vinculado:
  - a API do monitor agora enriquece incidentes e eventos pelo cache local de NFs usando `nf_bling_id`
  - quando a nota ja esta no sistema, a tela consegue exibir `NF numero` mesmo antes do pedido estar 100% reconciliado
- [x] blindar o sistema contra duplicidade historica de pedidos por `numeroPedidoLoja`:
  - foi criado um servico de revisao operacional para listar grupos duplicados, escolher pedido canonico e separar o que e seguro do que ainda exige revisao manual
  - `Pedidos Bling` passa a exibir o contexto de duplicidade do pedido, incluindo canonico, duplicados e bloqueios operacionais
  - o backend ganhou uma acao dedicada para consolidar duplicidades seguras sem misturar pedidos que ja tiveram venda ou movimentacao de estoque
- [x] criar acoes operacionais por linha para a equipe resolver fluxo sem depender de ajuste manual no banco:
  - `Pedidos Bling` passa a oferecer `Consolidar` e `Reconciliar` por pedido quando houver acao segura disponivel
  - `Monitor Bling` passa a mostrar o contexto de duplicidade e os botoes operacionais de consolidacao/reconciliacao por incidente
  - `NF de Saida` passa a oferecer um botao por nota para forcar reconciliacao do fluxo daquela NF especifica
- [x] enriquecer o Monitor Bling com o pedido canônico e a classe de incidente operacional de duplicidade:
  - a auditoria agora abre `PEDIDO_DUPLICADO_POR_NUMERO_LOJA` quando encontra mais de um pedido local ativo para o mesmo numero de pedido da loja
  - incidentes e eventos passam a receber contexto de duplicidade, incluindo pedido canonico, duplicados seguros e duplicados bloqueados
  - as respostas do monitor agora tambem devolvem `acoes_disponiveis`, facilitando a operacao na tela sem adivinhacao

- [x] blindar o espelhamento de status do pedido do Bling para o sistema local:
  - o backend agora roda uma reconciliacao periodica dos pedidos recentes para reaplicar cancelamento ou confirmacao quando o webhook falhar
  - pedidos que ja estavam `confirmado` localmente voltam a aceitar cancelamento vindo do Bling, liberando a reserva pendente
  - foi criado um endpoint manual para reconciliar status de pedidos recentes por tenant sem depender de ajuste em banco
- [x] blindar tambem as duplicidades recentes de pedidos por `numeroPedidoLoja`:
  - o backend agora roda uma reconciliacao periodica das duplicidades recentes e consolida automaticamente apenas os grupos ja classificados como seguros
  - foi criado um endpoint manual por tenant para revisar e consolidar duplicidades recentes sem precisar esperar o scheduler
  - o scheduler deixa de depender so do monitor/autofix para evitar que duplicidade recente vire ruido operacional ou reserva paralela
- [x] alinhar o detalhe de reservas do produto com a mesma regra do contador:
  - o modal de reservas ativas deixa de esconder pedidos `confirmado` que ainda seguram estoque
  - a operacao passa a enxergar exatamente quais pedidos estao compondo a reserva daquele SKU
- [x] comecar a quebrar os hooks mais pesados do PDV sem alterar a interface:
  - `frontend/src/hooks/usePDVProdutos.js` virou um hook de composicao, mantendo a mesma API publica para a pagina
  - a busca de produto, sugestoes e leitura por scanner foram movidas para `frontend/src/hooks/usePDVProdutoBusca.js`
  - a mutacao dos itens do carrinho, copia de codigo, KIT e quantidade foram movidas para `frontend/src/hooks/usePDVCarrinhoItens.js`
- [x] seguir quebrando os hooks mais pesados do PDV sem alterar a interface:
  - `frontend/src/hooks/usePDVAnalisePagamento.js` virou um hook de composicao, mantendo a mesma API publica para a pagina
  - a logica de analise da venda foi movida para `frontend/src/hooks/usePDVVendaAnalise.js`
  - a logica de exclusao, reabertura, emissao de NF e pos-pagamento foi movida para `frontend/src/hooks/usePDVVendaFinalizacao.js`
- [x] continuar quebrando os hooks mais pesados do PDV pelo fluxo de entrega:
  - `frontend/src/hooks/usePDVEntrega.js` virou um hook de composicao, mantendo a mesma API publica para a pagina
  - o carregamento de entregadores, sincronizacao e custo operacional foram movidos para `frontend/src/hooks/usePDVEntregadores.js`
  - as mutacoes do formulario de entrega foram movidas para `frontend/src/hooks/usePDVEntregaForm.js`
- [x] continuar quebrando os hooks mais pesados do PDV pelo ciclo de vida da venda atual:
  - `frontend/src/hooks/usePDVVendaAtual.js` virou um hook de composicao, mantendo a mesma API publica para a pagina
  - a logica de carregar, buscar e reabrir venda foi movida para `frontend/src/hooks/usePDVVendaCarregamento.js`
  - as acoes locais de limpar venda e abrir o modal de pagamento foram movidas para `frontend/src/hooks/usePDVVendaAcoes.js`
- [x] continuar quebrando os hooks mais pesados do PDV pelo fluxo de cliente:
  - `frontend/src/hooks/usePDVCliente.js` virou um hook de composicao, mantendo a mesma API publica para a pagina
  - o estado derivado do cliente atual, vendas em aberto, saldo de campanhas e copia de dados foram movidos para `frontend/src/hooks/usePDVClienteContexto.js`
  - a busca de clientes, sugestoes e selecao do cliente foram movidas para `frontend/src/hooks/usePDVClienteBusca.js`
- [x] continuar quebrando os hooks mais pesados do PDV pelo fluxo de descontos:
  - `frontend/src/hooks/usePDVDescontos.js` virou um hook de composicao, mantendo a mesma API publica para a pagina
  - o desconto por item foi movido para `frontend/src/hooks/usePDVDescontoItens.js`
  - o desconto total foi movido para `frontend/src/hooks/usePDVDescontoTotal.js`
  - a aplicacao de cupom foi movida para `frontend/src/hooks/usePDVCupom.js`
- [x] continuar quebrando os hooks mais pesados do PDV pelo fluxo de comissao:
  - `frontend/src/hooks/usePDVComissao.js` virou um hook de composicao, mantendo a mesma API publica para a pagina
  - a busca e sugestao de funcionarios foi movida para `frontend/src/hooks/usePDVFuncionariosBusca.js`
  - o estado derivado de comissao e a sincronizacao com a venda foram movidos para `frontend/src/hooks/usePDVComissaoEstado.js`
- [x] fazer a reducao final de orquestracao do PDV antes de migrar para outro modulo:
  - a montagem de props de `PDVDriveAlertBanner`, `PDVMainArea` e `PDVOverlays` foi movida para `frontend/src/hooks/usePDVPageComposition.js`
  - `PDV.jsx` ficou concentrado na inicializacao dos hooks de dominio e na composicao final da pagina
  - a proxima frente principal de decomposicao recomendada passa a ser `ProdutosNovo.jsx`
- [x] iniciar a decomposicao de `ProdutosNovo.jsx` pelo carregamento e fiscal:
  - a logica de carregar dados auxiliares, opcoes de racao, produto, predecessor/sucessor, imagens, lotes e fornecedores foi movida para `frontend/src/hooks/useProdutosNovoCarregamento.js`
  - o carregamento e a persistencia fiscal passaram a sair da pagina e ficar concentrados no mesmo hook
  - `ProdutosNovo.jsx` caiu de `4039` para `3761` linhas sem mudar a interface da tela
- [x] continuar a decomposicao de `ProdutosNovo.jsx` pelos fluxos de lotes e fornecedores:
  - o CRUD de lotes foi movido para `frontend/src/hooks/useProdutosNovoLotes.js`, incluindo modais, estados e recarga da grade
  - o CRUD de fornecedores foi movido para `frontend/src/hooks/useProdutosNovoFornecedores.js`, incluindo modal, formulario e recarga da lista
  - `ProdutosNovo.jsx` caiu de `3761` para `3571` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `ProdutosNovo.jsx` pelos fluxos de imagens e kit:
  - o upload, exclusao e definicao de imagem principal foram movidos para `frontend/src/hooks/useProdutosNovoImagens.js`
  - a busca de componentes, composicao do kit e calculo de estoque virtual foram movidos para `frontend/src/hooks/useProdutosNovoKit.js`
  - `ProdutosNovo.jsx` caiu de `3571` para `3278` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `ProdutosNovo.jsx` pelos fluxos de variacoes e predecessor/sucessor:
  - o fluxo de busca, selecao e limpeza de predecessor foi movido para `frontend/src/hooks/useProdutosNovoPredecessor.js`
  - o fluxo de carregamento, criacao e exclusao de variacoes foi movido para `frontend/src/hooks/useProdutosNovoVariacoes.js`
  - `ProdutosNovo.jsx` caiu de `3278` para `3160` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `ProdutosNovo.jsx` pelos fluxos de submissao e pelas abas mais densas (`recorrencia`, `racao` e `tributacao`):
  - o fluxo de submissao e persistencia do produto foi movido para `frontend/src/hooks/useProdutosNovoSubmit.js`
  - os handlers de fiscal do formulario foram movidos para `frontend/src/hooks/useProdutosNovoTributacao.js`
  - os handlers de recorrencia foram movidos para `frontend/src/hooks/useProdutosNovoRecorrencia.js`
  - os handlers de classificacao, fase e apresentacao de racao foram movidos para `frontend/src/hooks/useProdutosNovoRacao.js`
  - `ProdutosNovo.jsx` caiu de `3160` para `3012` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `ProdutosNovo.jsx` pelos fluxos residuais de acao/toolbar e pela componentizacao das abas densas:
  - a geracao de SKU e codigo de barras foi movida para `frontend/src/hooks/useProdutosNovoCodigos.js`
  - o cabecalho, a navegacao entre abas e o rodape de acoes foram extraidos para `frontend/src/components/produto/ProdutosNovoHeader.jsx`, `frontend/src/components/produto/ProdutosNovoTabs.jsx` e `frontend/src/components/produto/ProdutosNovoFooterActions.jsx`
  - as abas de tributacao, recorrencia e racao passaram a usar os componentes `frontend/src/components/produto/ProdutosNovoTributacaoTab.jsx`, `frontend/src/components/produto/ProdutosNovoRecorrenciaTab.jsx` e `frontend/src/components/produto/ProdutosNovoRacaoTab.jsx`
  - `ProdutosNovo.jsx` caiu de `3012` para `2361` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `ProdutosNovo.jsx` pelas abas restantes e pelos modais residuais:
  - a aba de variacoes passou a usar `frontend/src/components/produto/ProdutosNovoVariacoesTab.jsx`
  - a aba de composicao passou a usar `frontend/src/components/produto/ProdutosNovoComposicaoTab.jsx`
  - os modais residuais de entrada, lote e fornecedor foram extraidos para `frontend/src/components/produto/ProdutosNovoEntradaModal.jsx`, `frontend/src/components/produto/ProdutosNovoLoteModal.jsx` e `frontend/src/components/produto/ProdutosNovoFornecedorModal.jsx`
  - `ProdutosNovo.jsx` caiu de `2361` para `1603` linhas sem alterar a experiencia da tela
- [x] iniciar a decomposicao de `Campanhas.jsx` pelo fluxo de consultas e efeitos de carregamento:
  - a carga de dashboard, campanhas, ranking, cupons, destaque, sorteios, sugestoes, relatorios, retencao e configuracoes foi movida para `frontend/src/hooks/useCampanhasConsultas.js`
  - os `useEffect` e loaders principais sairam da pagina e passaram a ficar centralizados em um hook de consulta/composicao
  - `Campanhas.jsx` caiu de `6134` para `5959` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `Campanhas.jsx` pelos blocos visuais mais densos do topo da pagina:
  - a barra de abas foi movida para `frontend/src/components/campanhas/CampanhasTabsBar.jsx`
  - a aba de dashboard foi movida para `frontend/src/components/campanhas/CampanhasDashboardTab.jsx`
  - `Campanhas.jsx` caiu de `5959` para `5558` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `Campanhas.jsx` pela listagem principal de campanhas:
  - a aba de campanhas cadastradas foi movida para `frontend/src/components/campanhas/CampanhasListTab.jsx`
  - `Campanhas.jsx` caiu de `5558` para `5464` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `Campanhas.jsx` pela aba de retencao:
  - a aba de retencao foi movida para `frontend/src/components/campanhas/CampanhasRetencaoTab.jsx`
  - o formulario de criacao/edicao foi movido para `frontend/src/components/campanhas/CampanhasRetencaoForm.jsx`
  - `Campanhas.jsx` caiu de `5464` para `5240` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `Campanhas.jsx` pela aba de destaque mensal:
  - a aba de destaque foi movida para `frontend/src/components/campanhas/CampanhasDestaqueTab.jsx`
  - `Campanhas.jsx` caiu de `5240` para `4884` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `Campanhas.jsx` pelas abas de sorteios e ranking:
  - a aba de sorteios foi movida para `frontend/src/components/campanhas/CampanhasSorteiosTab.jsx`
  - a aba de ranking foi movida para `frontend/src/components/campanhas/CampanhasRankingTab.jsx`
  - `Campanhas.jsx` caiu de `4884` para `3878` linhas sem alterar a experiencia da tela
- [x] continuar a decomposicao de `Campanhas.jsx` pelas abas residuais de relatorios, unificacao, gestor e configuracoes
  - as abas foram movidas para `frontend/src/components/campanhas/CampanhasRelatoriosTab.jsx`, `CampanhasUnificacaoTab.jsx`, `CampanhasGestorTab.jsx` e `CampanhasConfigTab.jsx`
  - `Campanhas.jsx` caiu para `2713` linhas, concentrando menos JSX inline nas areas operacionais e administrativas
- [x] extrair a camada de modais de `Campanhas.jsx` para composicao propria
  - os modais de envio para inativos, sorteio, codigos offline, carimbo manual, envio em lote, nova campanha e cupom manual foram movidos para `frontend/src/components/campanhas/CampanhasModalsLayer.jsx`
  - `Campanhas.jsx` caiu de `2713` para `1981` linhas e ficou mais focado na orquestracao das abas e estados de dominio
- [x] concluir a quebra interna de `CampanhasModalsLayer.jsx` em modais dedicados
  - os modais foram separados em `frontend/src/components/campanhas/CampanhasEnvioInativosModal.jsx`, `CampanhasSorteioModal.jsx`, `CampanhasCodigosOfflineModal.jsx`, `CampanhasCarimboManualModal.jsx`, `CampanhasLoteModal.jsx`, `CampanhasNovaCampanhaModal.jsx` e `CampanhasCupomManualModal.jsx`
  - `CampanhasModalsLayer.jsx` deixou de concentrar JSX pesado e virou apenas uma camada de composicao entre os estados de dominio e os modais visuais

Itens deliberadamente adiados por agora:

- [ ] Sentry
- [ ] OpenTelemetry
- [ ] Loki/Grafana

Proximas tarefas sugeridas para execucao continua:

- [x] continuar a decomposicao de `ProdutosNovo.jsx` pela componentizacao dos blocos residuais da aba de caracteristicas e pela reducao do acoplamento de props entre a pagina e os hooks/componentes:
  - a aba de caracteristicas passou a usar `frontend/src/components/produto/ProdutosNovoCaracteristicasTab.jsx`
  - as abas residuais iniciais ficaram unificadas em componentes dedicados: `ProdutosNovoCaracteristicasTab.jsx`, `ProdutosNovoImagensTab.jsx`, `ProdutosNovoEstoqueTab.jsx` e `ProdutosNovoFornecedoresTab.jsx`
  - `ProdutosNovo.jsx` caiu de `1603` para `692` linhas sem alterar a experiencia da tela
- [ ] revisar contratos e agrupamentos de props residuais entre `PDVMainArea.jsx` e `PDVOverlays.jsx` apenas se surgir necessidade pratica
- [x] iniciar a decomposicao de `PedidosBling.jsx` pelos componentes inline e pela listagem/acoes da pagina
  - os elementos inline foram extraidos para `frontend/src/components/pedidosBling/PedidoBlingStatusBadge.jsx`, `frontend/src/components/pedidosBling/PedidoBlingCampoInfo.jsx`, `frontend/src/components/pedidosBling/PedidoBlingLinhaItem.jsx` e `frontend/src/components/pedidosBling/PedidoBlingCard.jsx`
  - a listagem, os filtros, a paginacao e as acoes de consolidar/reconciliar foram movidos para `frontend/src/hooks/usePedidosBlingListagem.js`
  - `PedidosBling.jsx` deixou de concentrar helpers visuais, effects de carregamento e chamadas de acao, ficando focado na composicao da tela
- [x] iniciar a decomposicao de `OperadorasCartao.jsx` pelos fluxos de cadastro/listagem e pela quebra dos blocos visuais
  - a carga, a selecao, o formulario e a persistencia foram movidos para `frontend/src/hooks/useOperadorasCartaoPage.js`
  - a interface foi separada em `frontend/src/components/operadorasCartao/OperadoraCartaoCard.jsx`, `frontend/src/components/operadorasCartao/OperadoraCartaoPadraoInfo.jsx`, `frontend/src/components/operadorasCartao/OperadoraCartaoEmptyState.jsx` e `frontend/src/components/operadorasCartao/OperadoraCartaoModal.jsx`
  - `OperadorasCartao.jsx` deixou de concentrar o CRUD inteiro e ficou focado em composicao e introducao guiada
- [x] reduzir o acoplamento de props residuais em `ProdutosNovo.jsx` criando um hook/compositor de pagina para as abas e modais
  - a montagem de props das abas, banners e modais foi movida para `frontend/src/hooks/useProdutosNovoPageComposition.js`
  - os banners de predecessor/sucessor foram extraidos para `frontend/src/components/produto/ProdutosNovoStatusBanners.jsx`
  - `ProdutosNovo.jsx` caiu de `692` para `569` linhas sem alterar a experiencia da tela
- [x] quebrar a aba de caracteristicas do `ProdutosNovo` em secoes menores e reutilizaveis
  - os blocos de dados basicos, precos e estrutura foram extraidos para `frontend/src/components/produto/ProdutosNovoDadosBasicosSection.jsx`, `frontend/src/components/produto/ProdutosNovoPrecosSection.jsx` e `frontend/src/components/produto/ProdutosNovoEstruturaSection.jsx`
  - `ProdutosNovoCaracteristicasTab.jsx` caiu de `744` para `67` linhas, mantendo o mesmo contrato da aba
- [x] separar a composicao visual restante do `ProdutosNovo.jsx` em corpo principal e camada de modais
  - a montagem visual principal foi movida para `frontend/src/components/produto/ProdutosNovoMainContent.jsx`
  - a camada de modais foi movida para `frontend/src/components/produto/ProdutosNovoModalsLayer.jsx`
  - `ProdutosNovo.jsx` caiu de `569` para `555` linhas e ficou mais focado em hooks e orquestracao
- [x] iniciar a decomposicao de `ClientesNovo.jsx` pelos fluxos mais seguros de listagem e enderecos
  - a listagem, busca e paginacao foram movidas para `frontend/src/hooks/useClientesNovoListagem.js`
  - o fluxo de enderecos adicionais e CEP do modal foi movido para `frontend/src/hooks/useClientesNovoEnderecos.js`
  - os componentes inline `ClienteSegmentoBadgeWrapper` e `WhatsAppHistorico` passaram para `frontend/src/components/ClienteSegmentoBadgeWrapper.jsx` e `frontend/src/components/WhatsAppHistorico.jsx`
  - `ClientesNovo.jsx` caiu de `4198` para `3937` linhas sem alterar a experiencia da tela
- [x] revisar contratos de props residuais entre as abas/componentes de `ProdutosNovo` e agrupar blocos repetidos de callbacks/estado onde isso reduzir ruido real de manutencao
  - o hook `frontend/src/hooks/useProdutosNovoPageComposition.js` passou a receber blocos de dominio (`pageState`, `catalogos`, `fornecedoresState`, `imagensState`, `kitState`, `lotesState`, `navigationState`, `predecessorState`, `racaoState`, `recorrenciaState`, `tributacaoState`, `utilsState` e `variacoesState`) em vez de uma lista extensa de props soltas
  - a composicao agora devolve `mainContentProps` e `modalsLayerProps`, reduzindo o fio espalhado entre a pagina e os componentes de tela
  - `ProdutosNovo.jsx` caiu de `555` para `544` linhas e ficou mais focado em orquestracao dos hooks
- [ ] criar contrato visual padrao para tabelas, filtros, paginas de detalhe e estados vazios
- [ ] criar uma suite minima E2E para login, Monitor Bling e NF de saida
- [ ] tratar os grupos historicos de duplicidade que ainda ficaram bloqueados por terem movimentacao ou item vendido
- [ ] revisar a politica de cancelamento de NF por canal para os casos em que o produto nao deve voltar automaticamente ao estoque
- [x] iniciar a decomposicao de `ProdutosBalanco.jsx` pelos fluxos de carregamento/filtros e pela grade de lancamentos
  - o carregamento, a paginacao, os filtros e os handlers de lancamento foram movidos para `frontend/src/hooks/useProdutosBalancoPage.js`
  - a tela passou a usar `frontend/src/components/produtoBalanco/ProdutosBalancoFiltros.jsx`, `ProdutosBalancoTabela.jsx` e `ProdutosBalancoPaginacao.jsx`
  - `ProdutosBalanco.jsx` deixou de concentrar a operacao inteira e ficou focado na composicao da pagina
- [x] iniciar a decomposicao de `Produtos.jsx` pela separacao da composicao visual da listagem e da camada de modais
  - a composicao principal da tela foi movida para `frontend/src/components/produtos/ProdutosMainContent.jsx`
  - a camada de modais foi movida para `frontend/src/components/produtos/ProdutosModalsLayer.jsx`
  - a montagem das props da tela foi centralizada em `frontend/src/hooks/useProdutosPageComposition.js`
  - `Produtos.jsx` caiu para `2014` linhas e ficou mais focado na orquestracao da pagina
- [x] extrair a listagem, filtros, selecao e paginacao de `Produtos.jsx` para um hook de pagina
  - a carga da listagem, a persistencia da busca, a selecao em massa e a paginacao foram movidas para `frontend/src/hooks/useProdutosListagem.js`
  - `Produtos.jsx` deixou de concentrar efeitos de carregamento e handlers de listagem, ficando mais focado nas acoes de negocio da tela
- [x] extrair o fluxo de relatorios de `Produtos.jsx` para um hook dedicado
  - a geracao de CSV, a ordenacao do relatorio, a selecao de colunas e o controle do menu/modal foram movidos para `frontend/src/hooks/useProdutosRelatorios.js`
  - `Produtos.jsx` deixou de concentrar os helpers de exportacao e avancou na separacao entre listagem, relatorios e composicao da pagina
- [x] extrair catalogos, edicao em lote/preco e exclusao com conflito de `Produtos.jsx` para hooks dedicados
  - os catalogos auxiliares foram movidos para `frontend/src/hooks/useProdutosCatalogos.js`
  - a edicao de preco e a edicao em lote foram movidas para `frontend/src/hooks/useProdutosEdicao.js`
  - a exclusao, resolucao de conflitos 409 e alternancia ativo/inativo foram movidas para `frontend/src/hooks/useProdutosExclusao.js`
  - `Produtos.jsx` caiu para `1064` linhas e ficou mais focado na composicao da tela e nos helpers visuais restantes
- [x] extrair os utilitarios visuais e o estado da tabela/colunas de `Produtos.jsx`
  - os utilitarios de busca, composicao de kit, texto quebrado e estoque visual foram movidos para `frontend/src/components/produtos/produtosUtils.js`
  - o estado de expansao da tabela e a configuracao de colunas visiveis foram movidos para `frontend/src/hooks/useProdutosTabela.js`
  - `Produtos.jsx` caiu para `860` linhas e ficou concentrado em hooks de dominio, composicao e a definicao das colunas da grade
- [x] extrair a definicao de colunas da grade de `Produtos.jsx` para um modulo dedicado
  - a configuracao de colunas da listagem foi movida para `frontend/src/components/produtos/produtosColumns.jsx`
  - `Produtos.jsx` deixou de concentrar renderizacao de celulas e caiu para `275` linhas
  - a pagina ficou focada em hooks, composicao e orquestracao da tela, sem carregar a definicao inteira da tabela
- [x] extrair os blocos visuais residuais da tela de `Produtos` para componentes proprios
  - o cabecalho de acoes foi movido para `frontend/src/components/produtos/ProdutosHeaderActions.jsx`
  - os filtros foram movidos para `frontend/src/components/produtos/ProdutosFiltrosPanel.jsx`
  - a paginacao foi movida para `frontend/src/components/produtos/ProdutosPaginationControls.jsx`
  - a tabela/listagem foi movida para `frontend/src/components/produtos/ProdutosTabelaSection.jsx`
  - `ProdutosMainContent.jsx` caiu de `566` para `127` linhas e ficou focado em composicao visual
- [x] extrair os modais residuais de `Produtos` para componentes proprios
  - o conflito de exclusao foi movido para `frontend/src/components/produtos/ProdutosConflitoExclusaoModal.jsx`
  - a edicao em lote foi movida para `frontend/src/components/produtos/ProdutosEdicaoLoteModal.jsx`
  - a configuracao de colunas foi movida para `frontend/src/components/produtos/ProdutosColunasModal.jsx`
  - o relatorio personalizado foi movido para `frontend/src/components/produtos/ProdutosRelatorioModal.jsx`
  - `ProdutosModalsLayer.jsx` caiu de `456` para `103` linhas e ficou focado em composicao dos modais
- [x] iniciar a decomposicao de `UsuariosPage.jsx` pela separacao da carga/acoes e dos blocos visuais principais
  - a carga de usuarios/roles, o modal e as acoes de ativar, desativar e forcar logout foram movidos para `frontend/src/hooks/useUsuariosPage.js`
  - a tabela e o modal foram extraidos para `frontend/src/components/usuarios/UsuariosTable.jsx` e `frontend/src/components/usuarios/UsuarioModal.jsx`
  - `UsuariosPage.jsx` caiu de `290` para `55` linhas e ficou focado na composicao da tela
- [x] continuar a decomposicao de `ClientesNovo.jsx` pelos modais e alertas visuais mais isolados
  - o aviso de duplicidade foi movido para `frontend/src/components/clientes/ClientesNovoDuplicadoWarning.jsx`
  - o modal de endereco adicional foi movido para `frontend/src/components/clientes/ClientesNovoEnderecoModal.jsx`
  - `ClientesNovo.jsx` caiu de `3726` para `3389` linhas e ficou com menos JSX inline nos fluxos de cadastro
- [x] continuar a decomposicao de `ClientesNovo.jsx` pelas etapas mais densas do wizard
  - a etapa de pets foi movida para `frontend/src/components/clientes/ClientesNovoPetsStep.jsx`
  - a etapa financeira foi movida para `frontend/src/components/clientes/ClientesNovoFinanceiroStep.jsx`
  - `ClientesNovo.jsx` caiu de `3389` para `2884` linhas e ficou mais focado na orquestracao do cadastro
- [x] continuar a decomposicao de `ClientesNovo.jsx` pelo miolo do wizard
  - a etapa de informacoes do cadastro foi movida para `frontend/src/components/clientes/ClientesNovoCadastroStep.jsx`
  - a etapa de contatos foi movida para `frontend/src/components/clientes/ClientesNovoContatosStep.jsx`
  - `ClientesNovo.jsx` caiu de `2884` para `2089` linhas e passou a concentrar menos JSX inline nas etapas iniciais
- [x] continuar a decomposicao de `ClientesNovo.jsx` pelas etapas intermediarias do wizard
  - a etapa de endereco foi movida para `frontend/src/components/clientes/ClientesNovoEnderecoStep.jsx`
  - a etapa de informacoes complementares foi movida para `frontend/src/components/clientes/ClientesNovoComplementaresStep.jsx`
  - `ClientesNovo.jsx` caiu de `2089` para `1910` linhas e ficou mais focado na orquestracao do wizard
- [x] continuar a decomposicao de `ClientesNovo.jsx` pelo shell do wizard e pela camada de modais
  - o wizard principal foi movido para `frontend/src/components/clientes/ClientesNovoWizardModal.jsx`
  - a composicao dos modais foi movida para `frontend/src/components/clientes/ClientesNovoModalsLayer.jsx`
  - `ClientesNovo.jsx` caiu de `1910` para `1729` linhas e ficou mais focado na listagem, acoes e fluxo de dominio
- [x] continuar a decomposicao de `ClientesNovo.jsx` pela listagem principal
  - a barra de abas foi movida para `frontend/src/components/clientes/ClientesNovoTabsBar.jsx`
  - a barra de acoes da listagem foi movida para `frontend/src/components/clientes/ClientesNovoActionsBar.jsx`
  - a paginacao foi movida para `frontend/src/components/clientes/ClientesNovoPaginationControls.jsx`
  - a tabela principal foi movida para `frontend/src/components/clientes/ClientesNovoTabelaSection.jsx`
  - `ClientesNovo.jsx` caiu de `1729` para `1039` linhas e ficou mais focado na orquestracao da pagina
- [x] concluir a decomposicao do fluxo de cadastro/modal de `ClientesNovo.jsx`
  - o dominio do wizard, duplicidade, CEP, pets e financeiro foi movido para `frontend/src/hooks/useClientesNovoCadastro.js`
  - `ClientesNovo.jsx` caiu de `1039` para `153` linhas e ficou focado so na listagem, exclusoes e composicao da tela
- [x] continuar a decomposicao de `Campanhas.jsx` pelos fluxos operacionais de gestor e configuracoes
  - o dominio do gestor de beneficios foi movido para `frontend/src/hooks/useCampanhasGestor.js`
  - o dominio de ranking/configuracoes de envio foi movido para `frontend/src/hooks/useCampanhasConfiguracoes.js`
  - `Campanhas.jsx` caiu de `1981` para `1771` linhas e ficou mais focado na orquestracao das abas e modais
- [x] concluir a decomposicao dos dominios residuais de `Campanhas.jsx`
  - os fluxos de inativos, retencao, cupons, destaque, sorteios, envio em lote, unificacao e fidelidade foram movidos para hooks dedicados em `frontend/src/hooks/useCampanhasInativos.js`, `useCampanhasRetencao.js`, `useCampanhasCupons.js`, `useCampanhasDestaque.js`, `useCampanhasSorteios.js`, `useCampanhasLote.js`, `useCampanhasUnificacao.js` e `useCampanhasFidelidade.js`
  - `Campanhas.jsx` caiu de `1771` para `473` linhas e ficou basicamente como orquestrador das abas e modais
- [x] extrair a composicao residual das abas de `Campanhas.jsx` para um componente dedicado
  - a renderizacao condicional das abas foi movida para `frontend/src/components/campanhas/CampanhasMainContent.jsx`
  - `Campanhas.jsx` caiu de `473` para `311` linhas e ficou focado em hooks, composicao de dominio e camada de modais
- [x] quebrar internamente `CampanhasGestorTab.jsx` em secoes visuais menores
  - o cabecalho, a lista por campanha, o resumo do cliente e as secoes de carimbos, cashback, cupons e ranking foram separados em componentes dedicados dentro de `frontend/src/components/campanhas/`
  - `CampanhasGestorTab.jsx` deixou de concentrar o miolo operacional do gestor e virou uma composicao mais fina das secoes
- [x] quebrar internamente `CampanhasRankingTab.jsx` e `CampanhasParametrosForm.jsx`
  - o ranking foi separado em componentes dedicados para filtros, clientes, configuracoes, distribuicao, cupons e lote em `frontend/src/components/campanhas/CampanhasRankingFiltrosBar.jsx`, `CampanhasRankingClientesTable.jsx`, `CampanhasRankingConfigPanels.jsx`, `CampanhasRankingDistribuicao.jsx`, `CampanhasRankingCuponsSection.jsx` e `CampanhasRankingLoteCard.jsx`
  - o formulario de parametros foi reorganizado em `frontend/src/components/campanhas/CampanhasParametrosFields.jsx` e `CampanhasParametrosSections.jsx`
  - `CampanhasRankingTab.jsx` e `CampanhasParametrosForm.jsx` viraram componentes de composicao fina
- [x] quebrar internamente `CampanhasConfigTab.jsx` e `CampanhasDashboardTab.jsx`
  - a aba de configuracoes foi separada em `frontend/src/components/campanhas/CampanhasConfigSchedulerHeader.jsx`, `CampanhasConfigBirthdaySection.jsx`, `CampanhasConfigInactivitySection.jsx` e `CampanhasConfigDestaqueSection.jsx`
  - o dashboard foi separado em `frontend/src/components/campanhas/CampanhasDashboardMetricasGrid.jsx`, `CampanhasDashboardAniversariosCard.jsx`, `CampanhasDashboardAlertasSection.jsx` e `CampanhasDashboardProximosEventosSection.jsx`
  - `CampanhasConfigTab.jsx` e `CampanhasDashboardTab.jsx` ficaram focados apenas em loading, estados vazios e composicao das secoes
- [x] reduzir a orquestracao residual de `Campanhas.jsx` com compositor de pagina e grupos de modais
  - a montagem das props de abas e modais foi movida para `frontend/src/hooks/useCampanhasPageComposition.js`
  - a camada de modais foi separada em `frontend/src/components/campanhas/CampanhasOperacionaisModals.jsx` e `CampanhasGestaoModals.jsx`
  - `CampanhasModalsLayer.jsx` caiu para `10` linhas e `Campanhas.jsx` ficou em `274` linhas
- [x] continuar a decomposicao interna das abas residuais de `Campanhas`
  - a aba de unificacao foi quebrada em `frontend/src/components/campanhas/CampanhasUnificacaoResultadoBanner.jsx` e `CampanhasUnificacaoSugestoesTable.jsx`
  - a aba de sorteios foi quebrada em `frontend/src/components/campanhas/CampanhasSorteioResultadoBanner.jsx` e `CampanhasSorteioCard.jsx`
  - `CampanhasUnificacaoTab.jsx` e `CampanhasSorteiosTab.jsx` ficaram focadas em composicao fina
- [x] quebrar internamente `CampanhasDestaqueTab.jsx`
  - a introducao, card de vencedor, desempate, resultado e top 5 foram separados em componentes dedicados
  - `CampanhasDestaqueTab.jsx` virou uma composicao fina da aba de destaque mensal
- [x] continuar a decomposicao interna do formulario de parametros e dos cupons do ranking em `Campanhas`
  - os parametros foram reorganizados em `frontend/src/components/campanhas/CampanhasParametrosProgramaSections.jsx` e `CampanhasParametrosRelacionamentoSections.jsx`, deixando `CampanhasParametrosSections.jsx` como camada fina de reexportacao
  - os filtros e a tabela de cupons do ranking foram separados em `frontend/src/components/campanhas/CampanhasRankingCuponsFiltrosBar.jsx` e `CampanhasRankingCuponsTable.jsx`
  - `CampanhasRankingCuponsSection.jsx` ficou focado apenas na composicao do bloco de cupons

## 9. Ferramentas que melhorariam meu trabalho e o desenvolvimento do sistema

### 9.1 Observabilidade e produção

- **OpenTelemetry** para padronizar traces, métricas e logs do backend, jobs e integrações
  - https://opentelemetry.io/docs/
- **Grafana Loki + Grafana** para centralização de logs e exploração operacional por tenant, request e evento
  - https://grafana.com/docs/loki/latest/
- **Sentry** para erros de frontend React e backend Python com stack, breadcrumbs e regressões por release
  - https://docs.sentry.io/platforms/javascript/guides/react/

### 9.2 Qualidade e testes

- **Playwright** para inventário autenticado de telas, smoke tests e fluxos E2E de negócio
  - https://playwright.dev/docs/intro
- **Storybook** para documentar componentes críticos e estabilizar o design system
  - https://storybook.js.org/docs
- **Ruff** no backend para lint e formatação rápidos
  - https://docs.astral.sh/ruff/

### 9.3 Governança de dependências e release

- **Renovate** para atualização assistida de dependências e redução de dívida de versão
  - https://docs.renovatebot.com/
- pipeline CI com:
  - build frontend
  - pytest por camadas
  - smoke E2E
  - validação de bundles
  - release notes por módulo

### 9.4 MCPs e ferramentas que ajudariam muito no dia a dia

- MCP de banco de dados com leitura segura de schema, planos e consultas de produção
- MCP de observabilidade com logs estruturados e busca por `tenant_id`, `request_id`, `pedido_bling_id`, `nf_bling_id`
- MCP de visual regression para comparar telas antes/depois de mudanças
- MCP de analytics/eventos para validar funis reais por módulo

## 10. Conclusão franca

O sistema já tem material para ser um ERP vertical de primeira linha para pet shop. O que falta agora não é volume de funcionalidade; é consolidar a base para crescimento com previsibilidade.

Se eu estivesse liderando a próxima fase, eu faria nesta ordem:

1. estabilização de release e observabilidade
2. decomposição dos maiores arquivos e fluxos
3. padronização visual e de interação
4. suíte E2E dos fluxos que movimentam dinheiro, estoque e fiscal
5. trilha de eventos e read models melhores para integrações

Com essa sequência, o sistema sai do estágio "muito poderoso, porém artesanal em alguns pontos" para "produto enterprise com governança, segurança de mudança e operação escalável".

## 11. Plano pre-venda app mobile e ecommerce

Atualizacao de 2026-04-24: iniciada a trilha de hardening para liberar o app e o ecommerce para pilotos com clientes reais.

### 11.1 O que ja foi ajustado nesta rodada

- [x] app mobile deixou de depender de URL de producao hardcoded em desenvolvimento:
  - `app-mobile/src/config.ts` agora resolve `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_DEV_API_URL` e `EXPO_PUBLIC_PROD_API_URL`
  - fallback de desenvolvimento passou para `http://localhost:8000/api`
  - release segue apontando para `https://mlprohub.com.br/api`
- [x] app mobile ganhou comandos explicitos de qualidade e release:
  - `npm run typecheck`
  - `npm run check`
  - builds de preview e producao separados no `package.json`
- [x] permissoes do app foram reduzidas para o minimo operacional atual:
  - camera para QR/barcode
  - localizacao foreground para rotas do entregador
  - notificacoes
  - leitura de imagens para foto do pet
  - vibracao
- [x] removidas ou bloqueadas permissoes duplicadas/amplas do manifest mobile:
  - `RECORD_AUDIO` bloqueada via `android.blockedPermissions`
  - `WRITE_EXTERNAL_STORAGE`
  - `RECEIVE_BOOT_COMPLETED`
  - duplicidades de `CAMERA`, `READ_EXTERNAL_STORAGE` e `VIBRATE`
- [x] `.env.example` do app passou a documentar URL local, URL de producao e tenant.
- [x] checkout web e app passaram a tratar o pedido como "recebido/pendente" em vez de "pagamento confirmado", alinhando a UI com o backend atual.
- [x] idempotencia do checkout passou a considerar forma de pagamento, retirada, drive e origem, evitando reaproveitar resposta antiga quando o cliente muda escolhas antes de reenviar.
- [x] contrato de pagamento app/ecommerce registrado e iniciado no codigo:
  - carrinho nao e pedido comercial
  - carrinho nao reserva estoque
  - formas aceitas: PIX, cartao de debito e cartao de credito
  - dinheiro foi removido do checkout app/ecommerce
  - webhook de pagamento tambem recusa boleto, transferencia, voucher ou metodo ausente
  - finalizacao fica bloqueada enquanto a intermediadora de pagamento nao estiver configurada
  - pedido so deve ser liberado para a loja/caixa depois de pagamento aprovado

### 11.2 Proximas melhorias P0 antes de vender

- [ ] criar ambiente de staging/homologacao para backend, frontend e app mobile
- [ ] adicionar testes automatizados para `ecommerce_cart`, `ecommerce_checkout`, `ecommerce_entregador` e rastreio mobile
  - [x] cobertura inicial de idempotencia do `ecommerce_checkout`
  - [x] cobertura inicial de contrato "carrinho nao reserva estoque"
  - [x] cobertura inicial do webhook aceitando somente PIX/cartao
  - [x] cobertura inicial de contrato de entrega/PDV
- [ ] formalizar o vinculo `Pedido -> Venda` em banco, evitando rastreio por texto em `observacoes`
- [ ] definir fluxo operacional unico de pedido:
  - carrinho
  - pagamento enviado para intermediadora
  - pagamento pendente de aprovacao
  - pagamento aprovado
  - pedido/venda gerado para a loja
  - separado
  - em rota ou retirada
  - entregue/cancelado
- [x] alinhar UI de pagamento com a realidade definida:
  - sem dinheiro
  - sem pedido antes de pagamento aprovado
  - carrinho tratado como carrinho
- [x] blindar status de entrega no PDV/app do entregador:
  - atualizar venda no PDV nao reabre entrega ja marcada como `entregue`, `em_rota` ou cancelada
  - marcar parada entregue ficou tolerante a reenvio do app
  - fechar rota concluida ficou tolerante a reenvio
  - teste cobre sincronizacao parada -> venda para a tag de entregue no PDV
- [x] reforcar beneficios do app para piloto:
  - Home leva para Beneficios pelo card de pontos e atalho rapido
  - tela de beneficios normaliza resposta parcial para cliente novo
  - cupons passaram a aceitar o contrato real do backend (`code`, `discount_value`, `discount_percent`)
  - copia de cupom usa `expo-clipboard`
  - sugestao de cashback corrigida para usar `or_` SQLAlchemy
- [ ] integrar intermediadora de pagamento para PIX e cartao antes de liberar pedidos reais
- [ ] implantar Sentry ou ferramenta equivalente para backend, frontend e app mobile
- [x] criar smoke test de release cobrindo vitrine, carrinho, checkout bloqueado sem gateway, entrega e tag de entregue no PDV
  - roteiro criado em `docs/SMOKE_RELEASE_APP_ECOMMERCE.md`
  - pendente transformar o roteiro em E2E automatizado quando staging estiver pronto
- [ ] limpar `console.log`, `TODO`, `FIXME` e artefatos de debug em codigo de producao
- [ ] revisar termos de privacidade, politica de dados, permissao de localizacao e textos de loja do app

### 11.3 Refatoracoes prioritarias desta nova fase

- [ ] `frontend/src/pages/ecommerce/EcommerceMVP.jsx`: separar vitrine, carrinho, conta, checkout, pedidos, analytics e estilos; utilitarios de carrinho/endereco/midia/estoque ja foram extraidos para `ecommerceMvpUtils`, card de produto da vitrine movido para `EcommerceCatalogProductCard`, resumo/filtros movidos para `EcommerceCatalogControls`, sidebar/tela do carrinho movidos para `EcommerceCartPanels` e modal de detalhe movido para `EcommerceProductDetailModal`
- [ ] `app-mobile/src/screens/entregador/DetalheEntregaScreen.tsx`: separar GPS, acoes de parada, recebimento, venda/modal e finalizacao de rota
- [ ] `frontend/src/components/EntradaXML.jsx`: continuar quebra do fluxo de importacao/validacao/conferencia para reduzir bundle e risco de regressao; ja foram extraidos modais operacionais, cabecalho, metricas, paineis SEFAZ, listagem principal, modal de criacao de produto, modal de detalhes/conferencia, card de item da NF, rodape/rateio da conferencia, painel de resumo/conferencia, helpers puros em `entradaXmlUtils`, exportadores de relatorio em `entradaXmlRelatorioCustos`, estado/acoes SEFAZ em `useEntradaXmlSefaz`, upload/lote em `useEntradaXmlUpload`, revisao de precos/processamento em `useEntradaXmlRevisaoPrecos`, busca/vinculacao/criacao de produtos em `useEntradaXmlProdutos`, conferencia em `useEntradaXmlConferencia`, historico de precos em `useEntradaXmlHistoricoPrecos` e rateio/pack em `useEntradaXmlRateio`
- [ ] `backend/app/routes/ecommerce_checkout.py`: extrair servico de checkout e preparar orquestracao `Pedido -> Venda`
- [ ] `backend/app/routes/ecommerce_cart.py`: revisar reserva de estoque com protecao contra corrida em checkout simultaneo
- [ ] `backend/app/api/endpoints/rotas_entrega.py`: separar sincronizacao de venda/rota/parada em servico de dominio testavel

## 12. Radar comercial, veterinario e banho/tosa

Atualizacao de 2026-04-24: novos clientes precisam conseguir experimentar o sistema sem bloqueios de modulos enquanto a politica comercial ainda nao esta fechada.

Pente fino detalhado desta fase:

- `docs/PENTE_FINO_VETERINARIO_BANHO_TOSA_2026-04-24.md`
- `docs/PENTE_FINO_VETERINARIO_CLINICA_PILOTO_2026-04-24.md`
- `docs/BLUEPRINT_BANHO_TOSA_ENTERPRISE_2026-04-24.md`

### 12.1 Liberacao temporaria de modulos

- [x] liberar temporariamente todos os modulos premium para tenants novos e existentes
- [x] manter o controle de modulos no codigo, mas sem travar a operacao por enquanto
- [ ] desenhar pacotes comerciais por perfil de cliente:
  - petshop varejo
  - clinica veterinaria
  - banho e tosa
  - hospital/clinica avancada
  - enterprise completo
- [ ] definir matriz de inclusao por pacote: PDV, estoque, fiscal, financeiro, campanhas, entregas, ecommerce, app, veterinario, banho/tosa, WhatsApp e marketplaces
- [ ] criar fluxo de compra/upgrade/desbloqueio com auditoria, status de pagamento e trilha de alteracao por tenant
- [ ] revisar textos de venda dos modulos bloqueados antes de reativar qualquer paywall

### 12.2 Pente fino do Veterinario antes da implantacao piloto

- [ ] validar jornada completa de clinica: cadastro tutor/pet, agenda, consulta, prontuario, vacinas, exames, internacao, retorno e financeiro
- [x] montar documento de pente fino para implantacao piloto de clinica
- [x] detalhar pente fino tecnico/produto do modulo veterinario para piloto real
- [ ] revisar permissao e escopo por veterinario, recepcao, admin e financeiro
- [ ] conferir usabilidade da agenda veterinaria: filtros, conflito de horario, remarcacao, cancelamento e encaixe
- [ ] padronizar prontuario com templates, campos obrigatorios por tipo de atendimento e historico claro por pet
- [ ] revisar calculadora de doses, catalogos clinicos e guardrails de IA antes de uso real em clinica
- [ ] validar anexos/exames: upload, preview, download, auditoria e privacidade/LGPD
- [ ] amarrar procedimentos, produtos/medicamentos e servicos ao estoque, financeiro e comissoes/repasses
- [ ] montar smoke test especifico do modulo veterinario para a clinica piloto

### 12.3 Novo modulo Banho & Tosa enterprise

- [ ] criar agenda exclusiva de banho e tosa com capacidade por profissional, sala/box, tipo de servico e porte do pet
- [x] registrar blueprint inicial do modulo Banho & Tosa enterprise
- [x] detalhar blueprint enterprise do modulo Banho & Tosa com dados, fluxos, custos e fases
- [ ] permitir agendamento de taxi dog vinculado ao atendimento, com ida/volta, janela de horario, rota e custo
- [ ] registrar check-in, inicio, pausa, termino e entrega do pet para medir tempo real do atendimento
- [ ] parametrizar custos por porte, pelagem, servico e unidade:
  - agua media por atendimento
  - energia por tempo/equipamento
  - produtos usados por tipo de banho
  - toalhas/insumos descartaveis
  - depreciacao/manutencao de equipamentos
- [ ] ratear salario/encargos/comissao do funcionario por tempo ou por servico executado
- [ ] calcular custo real, margem e lucro por atendimento, profissional, pet, porte e servico
- [ ] integrar pacotes/assinaturas de banho, recorrencia, lembretes e campanha de retorno
- [ ] controlar status operacional: agendado, confirmado, a caminho, chegou, em banho, em secagem, em tosa, pronto, entregue, cancelado/no-show
- [ ] gerar dashboards de ocupacao, produtividade, custo medio, ticket medio, margem e gargalos da agenda
- [ ] reaproveitar cadastros ja existentes: clientes, pets, funcionarios, produtos/estoque, financeiro, entregas/taxi dog e campanhas

---

<!-- Origem consolidada: CHANGELOG_PADRONIZACAO.md -->

# 📝 Changelog - Sistema de Padronização de Nomes

## [1.1.0] - 2026-02-14

### 🎉 Adicionado
- **Sistema Completo de Padronização de Nomes**
  - Algoritmo de reconstrução estruturada: `Ração [Marca] [Espécie] [Fase] [Porte] [Sabor] [Tratamento] [Peso]`
  - Inclusão de espécie (Cães/Gatos) usando campo `especies_indicadas`
  - Inclusão de porte com prefixo "Raças" (ex: "Raças Pequenas")
  - Inclusão de tratamento (Light, Hipoalergênico) como campo opcional
  - Sistema de confiança (0-100%) para cada sugestão
  - Sugestões filtradas por confiança mínima (≥50%)

- **Edição de Sugestões Antes de Aplicar**
  - Botão "Editar" para tornar sugestão editável
  - Campo de input com destaque visual (borda azul)
  - Botão "Cancelar Edição" para descartar mudanças
  - Botão "Aplicar Edição" dinâmico (muda texto conforme estado)
  - Estado `nomesEditados` para controlar edições por produto

- **Seleção Visual de Duplicatas**
  - Cards clicáveis para escolher qual produto manter
  - Feedback visual: verde (mantém) vs vermelho (remove)
  - Ícones checkmark (✓) e X nos cards
  - Status badges: "ESTE PRODUTO SERÁ MANTIDO" vs "Este produto será inativado"
  - Botão "Confirmar Mesclagem" só habilitado após seleção
  - Estado `produtosSelecionados` para controlar seleções

- **Persistência de Duplicatas Ignoradas**
  - Nova tabela `duplicatas_ignoradas` no banco
  - Registra pares que usuário marcou como "não são duplicatas"
  - Duplicatas ignoradas não reaparecem ao atualizar
  - Filtro automático na query de detecção

### 🔧 Corrigido
- **Bug Crítico 500 no Endpoint de Atualização**
  - Corrigido erro `NameError: name 'tenant_id' is not defined`
  - Adicionada extração de `tenant_id` de `user_and_tenant`
  - Endpoint PATCH `/produtos/{produto_id}` agora funcional

- **Campo Incorreto de Espécie**
  - Mudado de `especie_compativel` para `especies_indicadas`
  - Agora reflete corretamente o campo da tela de edição

### 🗄️ Banco de Dados
- **Nova Tabela**: `duplicatas_ignoradas`
  - Colunas: id, tenant_id, produto_id_1, produto_id_2, usuario_id, data_ignorado
  - Unique constraint em (tenant_id, produto_id_1, produto_id_2)
  - 4 índices criados para otimização

### 📁 Arquivos Modificados
```
backend/app/sugestoes_racoes_routes.py (linhas 376-480)
backend/app/produtos_routes.py (linha 2197)
backend/app/duplicatas_ignoradas_models.py (novo)
frontend/src/components/SugestoesInteligentesRacoes.jsx (múltiplas seções)
```

### 🎯 Exemplos de Transformação
```
Antes:  "Premier Cães Adultos Raças Médias e Grandes Frango 15kg"
Depois: "Ração Premier Cães Adultos Raças Médias e Grandes Frango 15kg"

Antes:  "Golden Formula Cães Adultos Frango e Arroz 15kg"
Depois: "Ração Golden Cães Adultos Raças Médias e Grandes Frango 15kg"

Antes:  "SPECIAL DOG AD PEQ PORTE 10.1KG"
Depois: "Ração Special Dog Cães Adultos Raças Pequenas Frango 10.1kg"
```

---

## [1.0.0] - 2026-02-14 (Pré-Padronização)

### 🎉 Implementado
- Sistema de Classificação Inteligente de Rações
- Dashboard de Análise Dinâmica
- Integração PDV com Alertas
- Sugestões Inteligentes (duplicatas, gaps de estoque)
- Machine Learning (feedback e previsão de demanda)

---

**Backup Criado**: `backups/backup_pos_padronizacao_nomes_20260214_172530`
