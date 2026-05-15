# Auditoria do Plano Basico em Novo Tenant

Documento de controle para registrar o teste tela por tela do plano basico em novo tenant, com foco em isolamento multitenant, permissoes de modulo/plano e erros encontrados/corrigidos.

Nao registrar aqui senhas, tokens, cookies, JWT, URLs sensiveis ou credenciais.

## 0. Como usar este arquivo a partir de agora

Este passa a ser o arquivo vivo do Plano Basico vendavel. A ideia e parar de espalhar auditoria, padronizacao e prontidao em varios documentos pequenos.

Uso pratico:

- Registrar aqui as telas ja testadas no Plano Basico.
- Atualizar o status quando uma tela passar por teste real em tenant novo.
- Marcar claramente o que ainda e P1 antes de vender para novas empresas.
- Usar o checklist como fonte unica para decidir a proxima fatia de padronizacao/refatoracao.
- Manter as auditorias antigas como historico consolidado dentro deste mesmo arquivo, sem criar documentos paralelos.

### 0.1. Escopo comercial do Plano Basico

Promessa comercial:

> Gestao para pet shop com cadastro de clientes e pets, produtos, estoque, PDV/vendas e visao gerencial basica de vendas.

Inclui nesta fase:

- Registro, login, selecao de tenant e onboarding basico.
- Dashboard inicial sem chamadas premium indevidas.
- Pessoas/clientes.
- Pets.
- Produtos.
- Estoque operacional basico.
- PDV e vendas.
- Financeiro apenas para vendas/historico relacionado a vendas.
- Cadastros essenciais: categorias de produto, especies/racas, opcoes de racao, formas de pagamento, operadoras de cartao, departamentos e tipos auxiliares necessarios ao basico.
- Configuracoes essenciais da empresa.
- Usuarios, permissoes basicas e LGPD operacional.

Nao vender ainda como parte do Plano Basico:

- Financeiro ERP completo, DRE operacional, contas a pagar/receber e conciliacoes.
- Compras, entrada XML, pedidos de compra e sugestao inteligente de compras.
- Veterinario completo.
- Banho & Tosa completo.
- Campanhas, WhatsApp, IA avancada, e-commerce, app mobile, entregas, Bling/marketplaces e fiscal/NF.

### 0.2. Criterios de pronto por tela

Uma tela do Plano Basico so fica `Pronta` quando passar pelos 5 eixos abaixo.

| Eixo | Criterio |
|---|---|
| Funcional | Fluxo principal testado em tenant novo, sem erro 500/403 indevido. |
| Tenant | Dados criados no tenant A nao aparecem no tenant B; inserts/updates usam tenant correto. |
| Plano/permissao | Tela basica nao chama modulo premium bloqueado; acesso direto premium cai em bloqueio/venda. |
| UX/padrao | Botoes, estados, tabela/lista, loading, empty/error e campos seguem componentes globais quando ja existem. |
| Refatoracao | Arquivo esta aceitavel ou tem plano claro de quebra sem bloquear venda controlada. |

Status usados:

- `Pronto`: passou nos 5 eixos.
- `Quase pronto`: fluxo principal ok, falta ajuste visual pequeno ou reteste pontual.
- `Pendente P1`: importante antes de escalar venda.
- `Pendente P2`: melhoria posterior; nao bloqueia venda controlada.
- `Nao testado`: ainda precisa passar no fluxo.

### 0.3. Status mestre atual

| Area | Status atual | Proxima acao |
|---|---|---|
| Comercial/auth/onboarding | Quase pronto | Retestar cadastro real, mensagens de erro corrigiveis e login com tenant novo. |
| Dashboard | Quase pronto | Confirmar console limpo, sem chamadas premium em tenant basico. |
| Pessoas/clientes | Pendente P1 | Listagem e financeiro/historico do cliente padronizados visualmente; retestar CRUD completo, financeiro/historico do cliente e isolamento A/B. |
| Pets | Pendente P1 | Listagem padronizada visualmente; retestar CRUD, detalhe do pet, cadastro rapido de especie/raca e premium vet bloqueado. |
| Produtos/estoque | Quase pronto | Retestar lista/cadastro/edicao/entrada com lote e validade no tenant novo. |
| Calculadora de racao | Pendente P1 | Retestar fluxo visual completo depois das correcoes backend. |
| PDV/vendas | Quase pronto | Rodar venda completa A/B: cliente, pet, produto, baixa de estoque e historico. |
| Financeiro de vendas | Quase pronto | Confirmar que nao depende de financeiro ERP premium. |
| Cadastros essenciais | Pendente P1 | Operadoras de cartao e opcoes de racao padronizadas visualmente; retestar CRUD de formas de pagamento, operadoras, especies/racas, opcoes de racao e departamentos. |
| Configuracoes/usuarios/LGPD | Pendente P1 | Testar salvar dados essenciais, criar usuario e permissao basica. |
| Premium bloqueado | Pendente P1 | Smoke de menus e URLs diretas premium em tenant basico. |

## 1. Branch e commits

- Branch: `fix/20260514-2157-corrigir-entrada-estoque-produto-user-id`
- Base observada antes da branch: `a74e82bfb fix: ajustar feedback de rota do entregador`
- Commits desta branch:
  - `cf47be7f9 fix: gravar usuario na entrada de estoque do produto`
  - `2e662a8b9 fix: evitar chamadas premium no plano basico`
- PR:
  - Ainda nao aberto automaticamente nesta maquina.
  - Link para abrir/revisar PR: `https://github.com/lcsgmoraes-droid/Sistema-Pet/pull/new/fix/20260514-2157-corrigir-entrada-estoque-produto-user-id`

## 2. Ambiente testado

- Ambiente: local/staging com Docker local rodando backend, banco e frontend Vite.
- Frontend: `http://localhost:5173`
- Tenant criado para teste: `Pet Basico 20260515002403`
- Usuario usado: `basico.20260515002403@teste.local`
- Senha: nao registrada.
- Comparacao com outro tenant:
  - Nao foi feita comparacao visual A/B completa nesta rodada.
  - O tenant novo iniciou sem dados de clientes/pets/produtos do admin existente, o que foi usado como evidencia parcial de isolamento.
  - Suite multitenant ampla nao foi rodada nesta etapa final; ja havia sido rodada em fases anteriores.
- Data/hora aproximada dos testes: 2026-05-15, madrugada, horario local.

## 3. Checklist tela por tela do plano basico

| Area | Tela/Fluxo | Frontend | Endpoint | Testado | Resultado | Correcao | Status |
|---|---|---|---|---|---|---|---|
| Comercial | Registro com plano basico | `/register?plan=basico` | `POST /auth/register` | Sim | Conta/tenant criados no teste local. Houve erro anterior quando criacao de dados padrao falhava; depois o fluxo voltou a criar tenant. | Correcoes anteriores na trilha de onboarding/templates. Nesta branch apenas ajustei autocomplete dos campos. | OK |
| Autenticacao | Login do novo usuario | `/login` | `POST /auth/login` | Sim | Login do usuario de teste funcionou e redirecionou para area autenticada. | Adicionado `autoComplete` correto para reduzir warnings do navegador. | OK |
| Dashboard | Dashboard inicial do plano basico | `/dashboard` | Chamava endpoints premium de financeiro/IA e Bling | Sim | A tela abria, mas o console recebia 403 de endpoints premium bloqueados. | `AlertasIA`, `ProjecoesIA` e badge do layout agora evitam chamadas premium quando modulo nao esta ativo. | Corrigido |
| Pessoas | Listar clientes | `/clientes` | `GET /clientes` | Sim | Tenant novo iniciou sem clientes do admin/tenant antigo. | Nenhuma nesta branch. | OK |
| Pessoas | Criar cliente | `/clientes` | `POST /clientes` | Sim | Cliente de teste criado e listado no tenant atual. | Nenhuma nesta branch. | OK |
| Pessoas | Editar/excluir cliente | `/clientes` | `PUT/DELETE /clientes/{id}` | Nao | Nao testado nesta rodada final via MCP. | Nao houve. | Nao testado |
| Pessoas | Financeiro do cliente | `/clientes/:id/financeiro` | Endpoints de resumo financeiro e vendas | Parcial | Historico/financeiro do cliente precisa permanecer liberado no basico; tela nao foi auditada completa nesta rodada. | Nao houve. | Pendente P1 |
| Pessoas | Saldo de campanhas no cadastro | Modal/wizard de cliente | `GET /campanhas/clientes/{id}/saldo` | Sim, por erro observado | Plano basico fazia chamada de campanhas e recebia 403. | `useClientesNovoCadastro` agora nao chama saldo de campanhas se modulo `campanhas` estiver bloqueado. | Corrigido |
| Pets | Criar pet vinculado a tutor | `/pets/novo?cliente_id=...` | `POST /pets` | Sim | Pet de teste criado para o cliente do tenant atual. | Nenhuma nesta branch. | OK |
| Pets | Detalhe do pet | `/pets/:petId` | `GET /pets/{id}` e antes endpoints vet | Parcial | Tela de pet basico nao deve chamar carteirinha/internacoes veterinarias se modulo vet estiver bloqueado. | `PetDetalhes` agora evita chamadas vet e oculta abas vet quando `veterinario` nao esta ativo. | Corrigido |
| Pets | Editar/excluir pet | `/pets/:id/editar` | `PUT/DELETE /pets/{id}` | Nao | Nao testado nesta rodada final. | Nao houve. | Nao testado |
| Pets | Cadastro rapido de especie/raca | `/pets/novo` e modal rapido | `POST /cadastros/especies`, `POST /cadastros/racas` | Parcial | Houve erro anterior ao criar raca sem `especie_id`; nao foi foco desta branch final. | Nao corrigido nesta branch. | Pendente P1 |
| Produtos | Listar produtos | `/produtos` | `GET /produtos` | Sim | Tenant novo iniciou sem produtos herdados indevidamente; produto criado apareceu no tenant atual. | Nenhuma nesta branch. | OK |
| Produtos | Criar produto | `/produtos/novo` | `POST /produtos` | Sim | Produto de teste criado com SKU/EAN/preco. | Nenhuma nesta branch. | OK |
| Produtos | Editar produto | `/produtos/:id/editar` | `PUT /produtos/{id}` | Parcial | Edicao foi usada para configurar produto/racao, mas sem checklist exaustivo de todos os campos. | Correcoes anteriores na trilha de catalogos/racao. | Pendente P1 |
| Produtos | Entrada de estoque pela tela do produto | `/produtos/:id/movimentacoes` ou acao de entrada | `POST /produtos/{id}/entrada` | Sim | Dava erro 500 por `user_id` nulo em `estoque_movimentacoes`. | `backend/app/produtos_routes.py` agora grava `user_id=current_user.id`. | Corrigido |
| Produtos | Entrada oficial de estoque | Fluxo de estoque | `POST /estoque/entrada` | Sim | Entrada oficial funcionou no tenant de teste. | Nenhuma nesta branch. | OK |
| Produtos | Calculadora de racao | `/produtos` / modal calculadora | `GET/POST /produtos/calculadora-racao` | Parcial | Houve erros anteriores quando produto aparecia como pronto sem tabela completa; fluxo foi trabalhado antes, mas nao revalidado nesta branch final. | Nao corrigido nesta branch final. | Pendente P1 |
| Produtos | Catalogos auxiliares | `/produtos/:id/editar` | `GET /produtos/departamentos` e similares | Parcial | Erros 500 foram vistos anteriormente em catalogos auxiliares; nao auditado nesta branch final. | Nao corrigido nesta branch final. | Pendente P1 |
| PDV | Abrir caixa | `/pdv` | Endpoints de caixa | Sim | Caixa aberto para venda de teste. | Nenhuma nesta branch. | OK |
| PDV | Criar venda | `/pdv` | Endpoints de vendas/itens | Sim | Venda criada com cliente, pet opcional e produto do tenant. | Nenhuma nesta branch. | OK |
| PDV | Registrar recebimento | `/pdv` | Endpoints de pagamento/finalizacao | Sim | Venda finalizada com Dinheiro. | Nenhuma nesta branch. | OK |
| PDV | Reabrir/visualizar venda finalizada | `/pdv` | Endpoints de venda e itens | Sim | Venda finalizada abriu para visualizacao. | Nenhuma nesta branch. | OK |
| PDV | Campanhas no recebimento | `/pdv` | `GET /campanhas/...` | Sim, por erro observado | Plano basico recebeu 403 em campanhas quando cliente/venda era selecionado. Parte ja estava protegida; saldo de cliente foi reforcado. | Reforco em `useClientesNovoCadastro`; `usePDVClienteContexto` ja respeitava modulo. | Corrigido |
| Financeiro | Vendas | `/financeiro/vendas` | Endpoints de historico/listagem de vendas | Sim | Historico de vendas abriu para venda do tenant de teste. | Nenhuma nesta branch. | OK |
| Financeiro ERP | Dashboard financeiro completo | `/financeiro` | Endpoints financeiros ERP | Sim, por erro observado no dashboard | Modulo ERP nao deve ser acessado automaticamente no basico. | Alertas/projecoes premium nao disparam sem modulo ativo. | Corrigido |
| Cadastros | Formas de pagamento | `/cadastros/financeiro/formas-pagamento` | Endpoints de formas de pagamento | Parcial | Formas de pagamento padrao existiam no tenant de teste e foram usadas no PDV. CRUD completo nao testado. | Nenhuma nesta branch. | Pendente P1 |
| Cadastros | Operadoras de cartao | `/cadastros/financeiro/operadoras` | Endpoints de operadoras | Nao | Tela padronizada visualmente com componentes globais; CRUD ainda nao foi retestado nesta rodada. | `PageHeader`, `ActionButton` e `Panel` aplicados sem alterar regra de negocio. | Pendente P1 |
| Cadastros | Opcoes de racao | `/cadastros/opcoes-racao` | Endpoints de opcoes de racao | Parcial | Tela padronizada visualmente; criacao rapida foi usada/observada, mas selects e persistencia de tabela de consumo precisam de reteste completo. | `PageHeader`, `Panel`, `SegmentedControl`, `ActionButton`, `IconActionButton`, `LoadingState`, `EmptyState` e `StatusBadge` aplicados sem alterar endpoints. | Pendente P1 |
| Configuracoes | Configuracao da empresa | `/configuracoes/empresa` ou equivalente | Endpoints de configuracao | Nao | Nao testado nesta rodada final. | Nao houve. | Nao testado |
| Administracao | Usuarios | `/admin/usuarios` | Endpoints de usuarios | Nao | Deve estar aberto no basico, mas nao foi testado nesta rodada final. | Nao houve. | Nao testado |
| Premium bloqueado | Campanhas | `/campanhas` | `GET /campanhas/...` | Parcial | Menu/rota deve ficar bloqueado no basico. Antes havia chamadas indiretas gerando 403. | Chamadas indiretas relevantes foram reduzidas. Tela premium completa nao foi retestada. | Corrigido parcial |
| Premium bloqueado | Veterinario | `/veterinario/*` | `GET /vet/...` | Parcial | Detalhe do pet chamava endpoints vet mesmo no basico. | `PetDetalhes` nao chama endpoints vet sem modulo. | Corrigido |
| Premium bloqueado | Bling/fiscal/integracoes | Layout/badges | `/integracoes/bling/...` | Sim, por erro observado | Layout chamava badge Bling e recebia 403 quando modulo bloqueado. | Layout ja estava condicionado a `moduloAtivo("bling")` na branch atual; sem nova alteracao nesta etapa. | OK |

## 4. Checklist de isolamento tenant

Observacao: esta tabela registra o que foi observado no teste do tenant novo. Validacao A/B completa com outro tenant nao foi feita nesta rodada final, entao os itens marcados como "Nao testado diretamente" nao devem ser tratados como aprovacao definitiva.

| Area basica | Dados do tenant A aparecem no tenant B? | Criacao grava tenant_id correto? | Edicao respeita tenant? | Exclusao respeita tenant? | Endpoint sem tenant/token falha corretamente? | Status |
|---|---|---|---|---|---|---|
| Clientes | Nao observado no tenant novo; comparacao A/B nao feita | Nao testado diretamente em DB | Nao testado | Nao testado | Nao testado nesta rodada | Parcial |
| Pets | Nao observado no tenant novo; comparacao A/B nao feita | Nao testado diretamente em DB | Nao testado | Nao testado | Nao testado nesta rodada | Parcial |
| Produtos | Nao observado no tenant novo; comparacao A/B nao feita | Nao testado diretamente em DB | Parcial | Nao testado | Nao testado nesta rodada | Parcial |
| Estoque | Produto do tenant novo recebeu entrada isolada no fluxo testado | Nao testado diretamente em DB | Nao aplicavel | Nao testado | Nao testado nesta rodada | Parcial |
| PDV/Vendas | Venda criada no tenant novo apareceu no historico do tenant atual | Nao testado diretamente em DB | Visualizacao testada; edicao/reabertura nao auditada completa | Nao testado | Nao testado nesta rodada | Parcial |
| Financeiro Vendas | Historico abriu com venda do tenant atual | Nao aplicavel | Nao testado | Nao testado | Nao testado nesta rodada | Parcial |
| Cadastros base | Formas de pagamento usadas no tenant atual | Nao testado diretamente em DB | Nao testado | Nao testado | Nao testado nesta rodada | Parcial |
| Modulos premium bloqueados | Chamadas indevidas reduziram; rota premium completa nao auditada | Nao aplicavel | Nao aplicavel | Nao aplicavel | 403 observado em chamadas bloqueadas | Corrigido parcial |

## 5. Correcoes aplicadas

| Arquivo alterado | Problema encontrado | Como foi corrigido | Risco antes | Como validou depois |
|---|---|---|---|---|
| `frontend/src/pages/Pessoas.jsx` | Listagem de Pessoas ainda tinha header, botoes, loading, empty state, tabela e acao de linha locais, fora da fundacao visual. | Migrado para `PageHeader`, `ActionButton`, `Panel`, `LoadingState`, `EmptyState`, `DataTable`, `CustomerIdentity`, `StatusBadge` e `IconActionButton`, mantendo filtros, importacao e fusao. | Tela essencial do Plano Basico ficava visualmente diferente e mais dificil de manter. | `npm --prefix frontend run build`. |
| `frontend/src/pages/ClienteFinanceiro.jsx` | Financeiro/historico do cliente ainda tinha header, loading, erro, cards, filtros, paginacao e empty state locais. | Migrado para `PageHeader`, `ActionButton`, `Panel`, `LoadingState`, `ErrorState`, `MetricGrid`, `MetricCard`, `IconActionButton` e `EmptyState`, preservando chamadas e tabela expandida. | Fluxo essencial do Plano Basico ficava visualmente desalinhado e mais dificil de manter. | `npm --prefix frontend run build`. |
| `frontend/src/pages/GerenciamentoPets.jsx` | Listagem de Pets ja estava avancada, mas ainda tinha header/loading/empty e alerta imperativo fora do padrao. | Migrado header para `PageHeader`, loading para `LoadingState`, vazio para `EmptyState` e erro de status para `toast.error`. | Experiencia menos consistente entre Pessoas/Pets e feedback de erro pouco padronizado. | `npm --prefix frontend run build`. |
| `frontend/src/pages/OperadorasCartao.jsx` | Tela de operadoras de cartao ainda usava header, acao principal e aviso importante locais, fora da fundacao visual do Plano Basico. | Migrado para `PageHeader`, `ActionButton` e `Panel`, mantendo hook, modal, cards e comportamento de guia. | Cadastro essencial ficava visualmente desalinhado e mais dificil de manter. | `npm --prefix frontend run build`. |
| `frontend/src/components/OpcoesRacao.jsx` | Tela de opcoes de racao tinha header, abas, paineis, loading, empty state e acoes locais; tambem exibia icones/textos quebrados por encoding antigo. | Migrado para componentes globais e icones `lucide`, preservando endpoints, formularios, lista, edicao, inativacao e guia. | Cadastro essencial ficava visualmente desalinhado e com manutencao mais custosa. | `npm --prefix frontend run build`. |
| `backend/app/produtos_routes.py` | `POST /produtos/{id}/entrada` gravava movimentacao sem `user_id` e quebrava com 500. | Incluido `user_id=current_user.id` ao criar `EstoqueMovimentacao`. | Fluxo basico de estoque quebrava ao fazer entrada pela tela do produto. | `python -m compileall backend/app/produtos_routes.py`; reteste manual do endpoint retornou 200. |
| `frontend/src/components/AlertasIA.jsx` | Dashboard/plano basico disparava endpoints de financeiro ERP/IA premium e recebia 403. | Componente agora retorna vazio sem chamar API quando `financeiro_erp` ou `ia_avancada` estao bloqueados. | Console poluido por 403 e risco de experiencia ruim no plano basico. | `npm --prefix frontend run build`. |
| `frontend/src/components/ProjecoesIA.jsx` | Fluxo/projecoes chamavam financeiro ERP sem modulo ativo. | Componente agora nao chama API quando `financeiro_erp` esta bloqueado. | Chamadas premium indevidas e 403 em plano basico. | `npm --prefix frontend run build`. |
| `frontend/src/hooks/useClientesNovoCadastro.js` | Cadastro/edicao de cliente podia buscar saldo de campanhas no plano basico. | `loadSaldoCampanhas` agora respeita `moduloAtivo("campanhas")`. | 403 no cadastro/financeiro do cliente e ruido em fluxo basico. | `npm --prefix frontend run build`. |
| `frontend/src/pages/PetDetalhes.jsx` | Detalhe do pet chamava carteirinha/internacoes/consultas/exames vet mesmo com modulo veterinario bloqueado. | Chamadas vet agora sao ignoradas quando `veterinario` nao esta ativo. | 403 em tela basica de pet e vazamento de experiencia premium. | `npm --prefix frontend run build`. |
| `frontend/src/App.jsx` | Warnings do React Router sobre flags futuras. | Ativadas flags `v7_startTransition` e `v7_relativeSplatPath`. | Ruido no console durante testes. | `npm --prefix frontend run build`. |
| `frontend/src/pages/Login.jsx` | Warning de autocomplete em campos de senha. | Adicionado `autoComplete="username"` e `autoComplete="current-password"`. | Ruido no console/navegador. | `npm --prefix frontend run build`. |
| `frontend/src/pages/Register.jsx` | Warning de autocomplete em campos de senha/cadastro. | Adicionado `autoComplete="email"` e `autoComplete="new-password"`. | Ruido no console/navegador. | `npm --prefix frontend run build`. |

## 6. Pendencias priorizadas

### P0 - Bloqueia vender / risco de vazamento / quebra fluxo basico

- Nenhuma pendencia P0 confirmada nesta rodada depois das correcoes da branch.
- Observacao: antes da correcao, `POST /produtos/{id}/entrada` era P0 para estoque/produto porque quebrava fluxo basico; agora esta corrigido.

### P1 - Importante antes de escalar

- Fazer comparacao A/B real entre dois tenants:
  - criar dados no tenant de teste;
  - logar em outro tenant;
  - confirmar que clientes, pets, produtos, estoque e vendas nao aparecem cruzados.
- Testar CRUD completo de:
  - clientes;
  - pets;
  - produtos;
  - categorias/opcoes de racao;
  - formas de pagamento;
  - usuarios.
- Retestar calculadora de racao ponta a ponta:
  - produto sem tabela nao pode aparecer como pronto;
  - salvar tabela deve persistir;
  - calculo deve retornar resultado sem 400/500.
- Retestar cadastro rapido de especie/raca:
  - nao permitir raca sem especie;
  - garantir que o item criado aparece no select imediatamente.
- Conferir endpoint sem token/tenant para areas basicas:
  - deve retornar 401/403;
  - nao deve retornar dados.
- Revisar menus do plano basico:
  - confirmar que apenas o essencial aparece;
  - premium deve ficar bloqueado ou oculto de forma consistente.

### P2 - Melhoria futura

- Limpar warnings de encoding do backend no Windows quando logs usam emoji.
- Remover `defaultProps` em componentes antigos de modais de entrada XML.
- Criar teste automatizado E2E do fluxo de venda basica.
- Criar rotina de auditoria visual via Playwright para smoke test do plano basico.
- Documentar criterios de "pronto para vender" por modulo/plano.

## 7. Validacoes executadas

### Comandos rodados nesta branch

```powershell
git status --short --branch
```

Resultado: branch de tarefa limpa antes das alteracoes finais.

```powershell
npm --prefix frontend run build
```

Resultado: passou.

```powershell
$env:DEBUG='false'; python -c "import sys; sys.path.insert(0, 'backend'); import app.main; print('main import ok')"
```

Resultado: passou com `main import ok`.

Observacao: o import em Windows ainda exibiu warnings/logging errors por caracteres Unicode em logs, sem impedir o import.

```powershell
python -m compileall backend/app/produtos_routes.py
```

Resultado: passou na validacao da correcao de entrada de estoque.

### Testes manuais via MCP/navegador

- Registro de novo tenant no plano basico: testado.
- Login do novo usuario: testado.
- Criacao de cliente: testado.
- Criacao de pet: testado.
- Criacao de produto: testado.
- Entrada de estoque: testado.
- Venda no PDV com Dinheiro: testado.
- Visualizacao de venda finalizada: testado.
- Acesso ao historico em Financeiro > Vendas: testado.
- Health check de producao: apenas endpoint de saude consultado, sem deploy e sem alteracao.

### Testes backend amplos

- Nao foram rodados novamente nesta etapa final da branch.
- Suites multitenant amplas ja foram usadas nas fases anteriores, mas devem ser reexecutadas antes de merge/deploy se a branch for para producao.

### Auditoria automatizada Codex consolidada

Branch original consolidada aqui: `test/20260514-2259-auditoria-plano-basico-isolamento-ab`.

Resultados automatizados registrados:

| Area | Validacao | Resultado |
|---|---|---|
| Auth/tenant | Rotas criticas do plano basico usando `get_current_user_and_tenant` | OK |
| Auth/tenant | Membership ativa, tenant ativo e sessao/JTI revalidados nas dependencias centrais | OK pela suite existente |
| Modulos premium | Gate `require_active_module` atualizado e testado com token/tenant atual | OK |
| Modulos premium | Routers premium principais protegidos por `_module_dependencies(...)` | OK |
| Plano basico | `/modulos/status` usa tenant selecionado no token, nao tenant legado do usuario | Corrigido e testado |
| Produtos/racao | Calculadora interna de racao usa tenant selecionado no token | Corrigido e testado |
| SQL tenant-safe | Helper e runtime guard de SQL bruto continuam bloqueando query sem tenant | OK |
| Onboarding tenant | Criacao/base de tenant e dados padrao cobertos pela suite multi-tenant | OK |
| Mobile/entregas | Contexto tenant do entregador/e-commerce e status de entrega | OK |
| Frontend | Build de producao Vite | OK |

Comandos registrados na auditoria automatizada:

```powershell
$env:APP_ENV='test'; $env:ENVIRONMENT='test'; $env:ENV='test'; $env:DATABASE_URL='sqlite:///./test.db'; $env:DEBUG='false'; .\backend\.venv\Scripts\python.exe -m pytest backend\tests\unit\test_plano_basico_tenant_contract.py backend\tests\unit\test_module_access_dependency.py backend\tests\unit\test_tenant_security_middleware.py backend\tests\unit\test_sql_audit_config.py backend\tests\multi_tenant\test_phase1_tenant_hardening.py backend\tests\multi_tenant\test_phase1_1_runtime_validation.py backend\tests\multi_tenant\test_phase2b_tenant_safe_sql.py backend\tests\multi_tenant\test_phase3_tenant_onboarding_service.py -q
```

Resultado: `74 passed`.

```powershell
$env:APP_ENV='test'; $env:ENVIRONMENT='test'; $env:ENV='test'; $env:DATABASE_URL='sqlite:///./test.db'; $env:DEBUG='false'; .\backend\.venv\Scripts\python.exe -m pytest backend\tests\unit\test_ecommerce_mobile_tenant_context.py backend\tests\unit\test_entrega_status_contract.py -q
```

Resultado: `14 passed`.

```powershell
npm --prefix frontend run build
```

Resultado: build concluido com sucesso.

Correcoes registradas naquela rodada:

- `backend/app/api/racao_calculadora_routes.py`: trocado `get_current_user` por `get_current_user_and_tenant`.
- `backend/app/routes/modulos_routes.py`: `/modulos/status` agora resolve o tenant pelo token selecionado.
- `backend/tests/unit/test_module_access_dependency.py`: testes ajustados ao contrato atual da dependency assincrona com credenciais.
- `backend/tests/unit/test_plano_basico_tenant_contract.py`: novo contrato automatizado para evitar regressao no plano basico/tenant.

Pendencias manuais que seguem abertas pelo checklist:

- Editar/excluir cliente.
- Financeiro do cliente.
- Editar/excluir pet.
- Cadastro rapido de especie/raca.
- Editar produto com todos os campos.
- Calculadora de racao na UI.
- Catalogos auxiliares de produto.
- Formas de pagamento CRUD.
- Operadoras de cartao.
- Configuracao da empresa.
- Usuarios/admin.
- A/B real no navegador entre dois tenants.

### Deploy

- Nao houve deploy de producao nesta etapa.
- Branch foi enviada para o GitHub para revisao/PR.

## Resumo Executivo

- Telas basicas testadas: 12/22
- Fluxos OK: 8
- Corrigidos nesta branch: 7 arquivos frontend/backend com impacto direto em plano basico ou ruido de console
- Pendencias P0: 0 confirmadas apos esta branch
- Pendencias P1: 6
- Pendencias P2: 5
- Minha recomendacao: liberar para revisao/merge em ambiente de teste/staging. Para producao/comercial, liberar com ressalvas somente depois de retestar CRUD completo, calculadora de racao, cadastro rapido de especie/raca e isolamento A/B entre dois tenants.

