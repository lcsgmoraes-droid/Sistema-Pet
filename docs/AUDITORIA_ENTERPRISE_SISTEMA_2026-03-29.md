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
  - `backend/app/produtos_routes.py` com `4212` linhas
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

- [ ] `frontend/src/pages/ecommerce/EcommerceMVP.jsx`: separar vitrine, carrinho, conta, checkout, pedidos, analytics e estilos
- [ ] `app-mobile/src/screens/entregador/DetalheEntregaScreen.tsx`: separar GPS, acoes de parada, recebimento, venda/modal e finalizacao de rota
- [ ] `frontend/src/components/EntradaXML.jsx`: quebrar fluxo de importacao/validacao/conferencia para reduzir bundle e risco de regressao
- [ ] `backend/app/routes/ecommerce_checkout.py`: extrair servico de checkout e preparar orquestracao `Pedido -> Venda`
- [ ] `backend/app/routes/ecommerce_cart.py`: revisar reserva de estoque com protecao contra corrida em checkout simultaneo
- [ ] `backend/app/api/endpoints/rotas_entrega.py`: separar sincronizacao de venda/rota/parada em servico de dominio testavel

## 12. Radar comercial, veterinario e banho/tosa

Atualizacao de 2026-04-24: novos clientes precisam conseguir experimentar o sistema sem bloqueios de modulos enquanto a politica comercial ainda nao esta fechada.

Pente fino detalhado desta fase: `docs/PENTE_FINO_VETERINARIO_BANHO_TOSA_2026-04-24.md`.

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
