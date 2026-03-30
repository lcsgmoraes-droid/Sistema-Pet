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

Itens deliberadamente adiados por agora:

- [ ] Sentry
- [ ] OpenTelemetry
- [ ] Loki/Grafana

Proximas tarefas sugeridas para execucao continua:

- [ ] continuar quebrando `PDV.jsx` em subcomponentes e hooks por fluxo
- [ ] quebrar `ProdutosNovo.jsx` em feature folders menores
- [ ] criar contrato visual padrao para tabelas, filtros, paginas de detalhe e estados vazios
- [ ] criar uma suite minima E2E para login, Monitor Bling e NF de saida

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
