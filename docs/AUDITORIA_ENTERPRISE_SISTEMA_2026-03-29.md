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

Itens deliberadamente adiados por agora:

- [ ] Sentry
- [ ] OpenTelemetry
- [ ] Loki/Grafana

Proximas tarefas sugeridas para execucao continua:

- [ ] continuar quebrando `PDV.jsx` em subcomponentes e hooks por fluxo
- [ ] quebrar `ProdutosNovo.jsx` em feature folders menores
- [ ] criar contrato visual padrao para tabelas, filtros, paginas de detalhe e estados vazios
- [ ] criar uma suite minima E2E para login, Monitor Bling e NF de saida
- [ ] tratar os grupos historicos de duplicidade que ainda ficaram bloqueados por terem movimentacao ou item vendido
- [ ] revisar a politica de cancelamento de NF por canal para os casos em que o produto nao deve voltar automaticamente ao estoque

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
