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
| Comercial/auth/onboarding | Pronto local | Cadastro real A/B por `/auth/register` passou depois do alinhamento das migrations. |
| Dashboard | Quase pronto | Confirmar dashboard inicial completo no navegador; Lembretes ja ficou sem chamadas premium em tenant basico. |
| Pessoas/clientes | Quase pronto | Listagem, criacao, edicao, exclusao e bloqueio cruzado passaram em auditoria A/B local; retestar financeiro/historico do cliente. |
| Pets | Quase pronto | Criacao real A/B passou com codigo unico por tenant; retestar detalhe visual e cadastro rapido de especie/raca. |
| Produtos/estoque | Quase pronto | Listagem, criacao, edicao, exclusao e entrada de estoque com bloqueio cruzado passaram em auditoria A/B local; retestar lote/validade visual e fluxo completo de estoque. |
| Calculadora de racao | Pronto local | API A/B e smoke visual no navegador passaram com operador nao-admin; busca, calculo e comparativo retornaram 200 e console limpo. |
| PDV/vendas | Pronto local A/B + smoke visual | Venda completa por API real e pelo navegador passou com operador nao-admin; caixa, sangria, suprimento, pagamento em dinheiro, finalizacao e baixa de estoque passaram. Falta apenas reteste visual de recibo/historico como refinamento. |
| Financeiro de vendas | Quase pronto | Finalizacao gerou reflexos financeiros sem 500 no A/B local; falta conferir telas/historico visual. |
| Cadastros essenciais | Quase pronto | Formas de pagamento, operadoras e opcoes de racao passaram em A/B real por API e smoke visual; catalogos de produto ainda precisam smoke visual completo no navegador. |
| Configuracoes/usuarios/LGPD | Pronto local | Usuarios/admin passou por smoke visual; Roles & Permissoes passou por criar, duplicar, editar e excluir perfil; LGPD passou busca de titular e dossie com schema local alinhado. |
| Premium bloqueado | Quase pronto | Smoke de chamadas premium indiretas em formas, layout e Lembretes passou; ainda falta varrer menus/URLs diretas premium. |
| Landing page/contratacao | Pronto local | Bloco de selecao do Plano Basico criado na landing; cadastro envia `plan=basico` e API grava plano validado. |

### 0.4. Cronograma final para vender o Plano Basico

| Etapa | Objetivo | Status | Bloqueia venda? |
|---|---|---|---|
| 1. Base tecnica multi-tenant | Cadastro real de tenants A/B, selecao de tenant, migrations limpas e bloqueio de vazamento entre empresas. | Concluido local | Sim, mas ja passou localmente. |
| 2. Fluxos essenciais do basico | Clientes, pets, produtos, estoque, PDV/vendas, historico financeiro de vendas e cadastros auxiliares. | Em andamento; PDV A/B, caixa, sangria/suprimento, pagamentos/operadoras, opcoes de racao, usuarios/admin, Roles e LGPD com smoke visual concluido | Sim, enquanto configuracao da empresa, lote/validade visual e cadastros auxiliares de produto restantes nao fecharem. |
| 3. Usuarios e permissoes | Criar usuario do tenant, validar permissoes basicas e bloqueio de acesso indevido. | Concluido local: Usuarios/Admin, Roles & Permissoes e LGPD operacional passaram por API/smoke visual. | Nao bloqueia venda controlada; manter reteste em staging/producao. |
| 4. Calculadora/catalogos de racao | Validar fluxo visual, persistencia e mensagens de erro sem 500. | Concluido local: API A/B e smoke visual passaram com operador nao-admin. | Nao bloqueia venda controlada; retestar em staging/producao. |
| 5. Landing page e selecao de planos | Exibir planos, destacar Basico, iniciar contratacao com plano escolhido e levar ao cadastro/onboarding correto. | Concluido local | Sim para vender por autoatendimento; falta smoke visual em producao/staging. |
| 6. A/B visual no navegador | Usar dois tenants reais no browser e conferir que menus, dados e mensagens batem com o plano. | Em andamento; PDV completo, autocomplete, Lembretes, pagamentos/operadoras, usuarios/admin, Roles e LGPD passaram | Sim antes de abrir para varias empresas. |
| 7. Produção controlada | Merge, deploy, migrations, health check e smoke real sem dados sensiveis. | Pendente | Sim. |

## 1. Branch e commits

- Branch historica consolidada: `fix/20260514-2157-corrigir-entrada-estoque-produto-user-id`
- Branch atual de alinhamento local/onboarding: `fix/20260515-1515-corrigir-onboarding-tenant-basico`
- Base observada antes da branch: `a74e82bfb fix: ajustar feedback de rota do entregador`
- Commits desta branch:
  - `cf47be7f9 fix: gravar usuario na entrada de estoque do produto`
  - `2e662a8b9 fix: evitar chamadas premium no plano basico`
- PR:
  - Atual: `https://github.com/lcsgmoraes-droid/Sistema-Pet/pull/36`
  - Status: draft, aguardando revisao/merge controlado.

## 2. Ambiente testado

- Ambiente: local/staging com Docker local rodando backend, banco e frontend Vite.
- Frontend: `http://localhost:5173`
- Tenant criado para teste: `Pet Basico 20260515002403`
- Usuario usado: `basico.20260515002403@teste.local`
- Senha: nao registrada.
- Comparacao com outro tenant:
  - Auditoria A/B local automatizada feita em 2026-05-15 com cadastro real via `/auth/register`.
  - Tenants criados pela API real: `tenant.a.20260515152334@example.com` e `tenant.b.20260515152334@example.com`.
  - Foram usados selecao real de tenant, token real e endpoints reais das telas basicas.
  - A rodada confirmou isolamento em clientes, pets, formas de pagamento e opcoes de racao.
  - A rodada de PDV/vendas `20260515154447` confirmou venda finalizada e bloqueio cruzado entre tenants.
  - A rodada de usuarios `20260515155144` confirmou operador PDV nao-admin com permissoes minimas, busca/autocomplete isolados e bloqueio de administracao RBAC.
  - A rodada de racao/catalogos `20260515160544` confirmou operador nao-admin, catalogos isolados, calculadora sem vazamento e bloqueio por permissao.
  - A rodada de cadastros de produto `20260515161002` confirmou departamentos, categorias e marcas isolados e bloqueados por permissao.
  - A rodada de pagamentos/operadoras `20260515161901` confirmou operador de vendas nao-admin lendo formas/operadoras do proprio tenant, bloqueio de tenant cruzado, mutacoes restritas a `configuracoes.editar`, taxas filtradas por tenant e analise de venda sem processar forma de outro tenant.
  - A rodada visual `20260515162539` confirmou, via navegador isolado, formas de pagamento e operadoras no plano basico sem chamadas premium indevidas, operador nao-admin no PDV, autocomplete de produto isolado por tenant e usuario sem permissao bloqueado.
  - A rodada `20260515165148` confirmou operador PDV nao-admin com permissao `vendas.criar`, permissao implicita no backend, venda/finalizacao por API, caixa, sangria, suprimento, fechamento sem banco e autocomplete sem falso positivo entre SKUs alfanumericos A/B.
  - A rodada visual `20260515201225` confirmou PDV completo no navegador com operador nao-admin: caixa aberto, produto adicionado por SKU, pagamento em dinheiro, venda finalizada, item gravado e estoque baixado. Tambem confirmou Lembretes sem chamadas premium indevidas no tenant basico.
  - A rodada visual `20260515173417` confirmou tela de Usuarios/Admin: login, listagem, criacao de usuario, mensagem clara para e-mail duplicado, desativacao, logout forcado com escopo de tenant e reload sem erros inesperados.
  - A rodada visual/API `20260515175152` confirmou Roles & Permissoes e LGPD operacional: criacao/duplicidade/edicao/exclusao de perfil, busca de titular e dossie LGPD sem 500 depois das migrations de reparo.
  - A rodada visual `20260515181603` confirmou calculadora de racao e opcoes de racao no navegador com operador nao-admin.
  - A comparacao visual completa por navegador ainda fica pendente para financeiro de vendas, configuracao da empresa e alguns cadastros auxiliares.
- Data/hora aproximada dos testes: 2026-05-15, madrugada e tarde, horario local.

## 3. Checklist tela por tela do plano basico

| Area | Tela/Fluxo | Frontend | Endpoint | Testado | Resultado | Correcao | Status |
|---|---|---|---|---|---|---|---|
| Comercial | Registro com plano basico | `/register?plan=basico` | `POST /auth/register` | Sim | Conta/tenant criados em dois tenants A/B por API real. Erros locais de schema foram corrigidos por migrations. | Adicionadas migrations para gaps de onboarding local e tabelas auxiliares de racao. | OK |
| Comercial | Landing page com selecao de planos | `/landing` e `/planos` | Plano escolhido alimenta cadastro/contratacao | Sim | Landing tem bloco de selecao do Plano Basico, `/planos` detalha o Basico e o cadastro recebe `plan=basico`. API bloqueia plano invalido e grava tenant com `plan=basico`. | `LandingPage`, `Register`, `AuthContext` e `auth_routes_multitenant` amarrados ao contrato de plano. | OK local |
| Autenticacao | Login do novo usuario | `/login` | `POST /auth/login` | Sim | Login do usuario de teste funcionou e redirecionou para area autenticada. | Adicionado `autoComplete` correto para reduzir warnings do navegador. | OK |
| Dashboard | Dashboard inicial do plano basico | `/dashboard` | Chamava endpoints premium de financeiro/IA e Bling | Sim | A tela abria, mas o console recebia 403 de endpoints premium bloqueados. | `AlertasIA`, `ProjecoesIA` e badge do layout agora evitam chamadas premium quando modulo nao esta ativo. | Corrigido |
| Pessoas | Listar clientes | `/clientes` | `GET /clientes` | Sim | Auditoria A/B confirmou que cliente do tenant A aparece no A e nao aparece no B, e vice-versa. | Nenhuma nesta branch. | OK |
| Pessoas | Criar cliente | `/clientes` | `POST /clientes` | Sim | Cliente criado por endpoint real em dois tenants; acesso direto cruzado a `/clientes/{id}` retornou 404. | Nenhuma nesta branch. | OK |
| Pessoas | Editar/excluir cliente | `/clientes` | `PUT/DELETE /clientes/{id}` | Sim | Auditoria A/B estendida confirmou edicao/exclusao no proprio tenant e 404 em tentativa cruzada. | Nenhuma nesta branch. | OK |
| Pessoas | Financeiro do cliente | `/clientes/:id/financeiro` | Endpoints de resumo financeiro e vendas | Parcial | Historico/financeiro do cliente precisa permanecer liberado no basico; tela nao foi auditada completa nesta rodada. | Nao houve. | Pendente P1 |
| Pessoas | Saldo de campanhas no cadastro | Modal/wizard de cliente | `GET /campanhas/clientes/{id}/saldo` | Sim, por erro observado | Plano basico fazia chamada de campanhas e recebia 403. | `useClientesNovoCadastro` agora nao chama saldo de campanhas se modulo `campanhas` estiver bloqueado. | Corrigido |
| Pets | Criar pet vinculado a tutor | `/pets/novo?cliente_id=...` | `POST /pets` | Sim | Pet criado por endpoint real em dois tenants; ambos puderam usar `10001-PET-0001` sem colisao, isolado por tenant. | Corrigida busca de pets que duplicava join com cliente e unicidade de codigo de pet passou a ser por tenant. | OK |
| Pets | Detalhe do pet | `/pets/:petId` | `GET /pets/{id}` e antes endpoints vet | Parcial | Tela de pet basico nao deve chamar carteirinha/internacoes veterinarias se modulo vet estiver bloqueado. | `PetDetalhes` agora evita chamadas vet e oculta abas vet quando `veterinario` nao esta ativo. | Corrigido |
| Pets | Editar/excluir pet | `/pets/:id/editar` | `PUT/DELETE /pets/{id}` | Sim | Auditoria A/B estendida confirmou edicao/exclusao no proprio tenant e 404 em tentativa cruzada. | Nenhuma nesta branch. | OK |
| Pets | Cadastro rapido de especie/raca | `/pets/novo` e modal rapido | `POST /cadastros/especies`, `POST /cadastros/racas` | Sim por navegador | Smoke visual criou especie e raca por modal rapido no tenant basico; raca entrou selecionada no formulario; chamadas de especies/racas retornaram 201/200 sem 500. A tentativa de raca sem especie fica bloqueada/explicada no frontend. | `PetForm` limpa raca ao trocar especie, bloqueia quick-add de raca sem especie e `QuickAddModal` valida `especie_id` antes de chamar API; contrato inclui `cadastros_routes.py` no tenant selecionado. | OK local + smoke visual |
| Produtos | Listar produtos | `/produtos` | `GET /produtos` | Sim | Auditoria A/B confirmou que produto do tenant A aparece no A e nao aparece no B, e vice-versa. Regra de validade revalidada por teste: listagem usa o lote com saldo e validade mais urgente; tooltip recebe lotes com saldo. | Nenhuma nesta branch para isolamento; suite de validade/lote reexecutada. | OK |
| Produtos | Criar produto | `/produtos/novo` | `POST /produtos` | Sim | Produto criado por endpoint real em dois tenants; acesso direto cruzado a `/produtos/{id}` retornou 404. | Nenhuma nesta branch. | OK |
| Produtos | Editar produto | `/produtos/:id/editar` | `PUT /produtos/{id}` | Sim | Auditoria A/B estendida confirmou edicao no proprio tenant e 404 em tentativa cruzada. Checklist exaustivo de todos os campos segue pendente. | Correcoes anteriores na trilha de catalogos/racao. | OK parcial |
| Produtos | Entrada de estoque pela tela do produto | `/produtos/:id/movimentacoes` ou acao de entrada | `POST /produtos/{id}/entrada` | Sim | Dava erro 500 por `user_id` nulo em `estoque_movimentacoes`; na auditoria A/B estendida, entrada propria retornou 200 e entrada cruzada retornou 404. | `backend/app/produtos_routes.py` agora grava `user_id=current_user.id`. | OK |
| Produtos | Entrada oficial de estoque | Fluxo de estoque | `POST /estoque/entrada` | Sim | Entrada oficial funcionou no tenant de teste. | Nenhuma nesta branch. | OK |
| Produtos | Calculadora de racao | `/produtos` / modal calculadora | `GET/POST /produtos/calculadora-racao` e `POST /internal/racao/calcular` | Sim por API e navegador | Operador A com `produtos.visualizar` buscou/calculou racao do tenant A, nao encontrou racao do tenant B e recebeu 404 ao forcar ID cruzado. Usuario sem `produtos.visualizar` recebeu 403. No navegador, operador nao-admin buscou racao apta, calculou consumo e executou comparativo com chamadas 200 e console limpo. | Calculadora e rota interna agora exigem `produtos.visualizar`; campos da tela receberam `id/name` e labels associados. | OK local + smoke visual |
| Produtos | Catalogos auxiliares | `/produtos/:id/editar` | `GET/POST/PUT/DELETE /produtos/departamentos`, `/categorias`, `/marcas` | Sim por API | Departamentos, categorias e marcas passaram em A/B: operador A viu apenas tenant A, acesso direto cruzado retornou 404, operador apenas visualizacao nao mutou e usuario sem `produtos.visualizar` recebeu 403. | Rotas auxiliares de produto agora exigem permissao por acao; criacao de marca/departamento grava `user_id`; contagens de delete filtram tenant. | OK local; falta smoke visual |
| PDV | Abrir caixa | `/pdv` | Endpoints de caixa | Sim | Caixa aberto para venda A/B por API real em dois tenants Basico. | Nenhuma regra de caixa alterada nesta rodada. | OK local |
| PDV | Criar venda | `/pdv` | Endpoints de vendas/itens | Sim | Venda criada nos tenants A e B com cliente e produto do proprio tenant; acesso cruzado a venda do outro tenant retornou 404. No navegador, operador nao-admin abriu PDV sem 403 indevido, autocomplete encontrou produto do tenant A e nao mostrou produto/SKU B. | Adicionada migration para alinhar campos `tipo_retirada` e `palavra_chave_retirada` de `vendas`; backend agora respeita permissoes implicitas e busca de SKU alfanumerico nao cai no fallback numerico. | OK local + smoke visual |
| PDV | Registrar recebimento | `/pdv` | Endpoints de pagamento/finalizacao | Sim | Venda finalizada com Dinheiro nos dois tenants; estoque caiu de 5 para 3 em cada tenant. Rodada visual `20260515201225` finalizou venda `202605150002` pelo navegador, gerou status `finalizada`, item gravado e estoque do produto caiu para 6. | Adicionadas migrations para `empresa_config_fiscal` e campos faltantes em `dre_subcategorias`, removendo 500 na finalizacao. | OK local + smoke visual |
| PDV | Sangria e suprimento do caixa | `/pdv` / menu do caixa | `POST /caixas/{id}/movimentacao` | Sim por API e revisao de contrato | Sangria e suprimento sao movimentacoes do caixa fisico, nao dependem de banco, conta bancaria ou modulo `financeiro_erp`; origem/destino ficam opcionais. Rodada `20260515165148` confirmou suprimento, sangria e fechamento de caixa com diferenca zero. | Ajustada a UI para nao marcar origem/destino como obrigatorios. | OK local |
| PDV | Reabrir/visualizar venda finalizada | `/pdv` | Endpoints de venda e itens | Sim | GET da venda finalizada retornou status `finalizada`; visualizacao cruzada pelo outro tenant retornou 404. | Nenhuma regra de reabertura alterada nesta rodada. | OK local |
| PDV | Campanhas no recebimento | `/pdv` | `GET /campanhas/...` | Sim, por erro observado | Plano basico recebeu 403 em campanhas quando cliente/venda era selecionado. Parte ja estava protegida; saldo de cliente foi reforcado. | Reforco em `useClientesNovoCadastro`; `usePDVClienteContexto` ja respeitava modulo. | Corrigido |
| Financeiro | Vendas | `/financeiro/vendas` | Endpoints de historico/listagem de vendas | Sim | Historico de vendas abriu para venda do tenant de teste. | Nenhuma nesta branch. | OK |
| Financeiro ERP | Dashboard financeiro completo | `/financeiro` | Endpoints financeiros ERP | Sim, por erro observado no dashboard | Modulo ERP nao deve ser acessado automaticamente no basico. | Alertas/projecoes premium nao disparam sem modulo ativo. | Corrigido |
| Cadastros | Formas de pagamento | `/cadastros/financeiro/formas-pagamento` | Endpoints de formas de pagamento | Sim por API e navegador | Operador com `vendas.criar` listou formas do proprio tenant e nao viu tenant B; usuario sem permissao recebeu 403; usuario com `configuracoes.editar` conseguiu criar; admin A nao editou forma do tenant B. No navegador, usuario de configuracao viu a forma A, sem coluna/field premium de conta destino e sem chamadas a `contas-bancarias`/Bling. | Leitura agora aceita `vendas.criar` ou `configuracoes.editar`; mutacoes exigem `configuracoes.editar`; contrato automatizado adicionado. Frontend evita chamadas premium no basico. | OK local + smoke visual |
| Cadastros | Taxas/analise de formas de pagamento | PDV/modal pagamento | `GET/POST/PUT/DELETE /formas-pagamento/taxas` e `POST /formas-pagamento/analisar-venda` | Sim por API | Taxas foram filtradas por tenant; operador de vendas conseguiu analisar forma do proprio tenant; forma do tenant B nao foi processada na analise do tenant A; usuario sem permissao recebeu 403. | Taxas e analise agora exigem permissao por leitura/alteracao e filtram `FormaPagamento`, `FormaPagamentoTaxa` e imposto padrao por tenant. | OK local; falta smoke visual |
| Cadastros | Operadoras de cartao | `/cadastros/financeiro/operadoras` | Endpoints de operadoras | Sim por API e navegador | Operador com `vendas.criar` listou operadoras do proprio tenant e nao viu tenant B; acesso direto a operadora do tenant B retornou 404; mutacao por operador retornou 403. No navegador, usuario de configuracao viu operadora A e nao viu operadora B. | Leitura agora aceita `vendas.criar` ou `configuracoes.editar`; mutacoes exigem `configuracoes.editar`; contrato automatizado adicionado. | OK local + smoke visual |
| Cadastros | Opcoes de racao | `/cadastros/opcoes-racao` | Endpoints de opcoes de racao | Sim por API e navegador | Catalogos A/B ficaram isolados; operador com apenas `produtos.visualizar` conseguiu listar, mas nao criar. Mutacoes agora exigem permissao de produto. No navegador, operador com permissao de produto listou, criou, editou e inativou linha; criou e inativou apresentacao; abas carregaram sem warnings de form ou erros de rede. | Endpoints de opcoes de racao agora exigem `produtos.visualizar`, `produtos.criar` ou `produtos.editar` conforme acao; tela recebeu labels/ids/names nos campos. | OK local + smoke visual |
| Configuracoes | Configuracao da empresa | `/configuracoes`, `/configuracoes/fiscal`, `/configuracoes/geral`, `/configuracoes/estoque` | `/empresa/fiscal`, `/empresa/dados-cadastrais`, `/empresa/config`, `/empresa/config-estoque` | Parcial | Contrato local confirmou que rotas e endpoints de configuracao exigem permissao de configuracao; hub de configuracoes agora respeita modulos premium e permissoes. | Protegidos endpoints de dados/fiscal/geral/estoque com `configuracoes.empresa` ou `configuracoes.editar`; subrotas frontend e `/admin/roles` receberam `ProtectedRoute`; cards premium somem quando modulo esta bloqueado. | Corrigido local; falta smoke visual |
| Administracao | Usuarios | `/admin/usuarios` | `POST/GET /usuarios` | Sim | Admin criou operador PDV em dois tenants; operador logou, recebeu apenas `clientes.visualizar`, `produtos.visualizar`, `vendas.criar` e nao acessou `/usuarios`. No navegador, operador foi bloqueado em tela administrativa e usuario sem permissao foi bloqueado no PDV. | Nenhuma regra de usuario alterada; validado contrato de permissao. | OK local + smoke visual parcial |
| Administracao | Roles/permissoes | `/admin/roles` e perfis | `/roles`, `/permissions` | Sim | Operador sem `usuarios.manage` recebe 403; admin criou perfil, duplicidade exibiu mensagem corrigivel, edicao atualizou permissoes e exclusao removeu vinculos sem 500. | Tela refatorada para componentes globais; `roles_routes` apaga `role_permissions` antes da role; endpoints seguem exigindo `usuarios.manage`. | OK local + smoke visual |
| Administracao | LGPD operacional | `/admin/lgpd` | `/lgpd/status`, `/lgpd/solicitacoes`, `/lgpd/clientes/{id}/dossie`, `/lgpd/clientes/{id}/consentimentos` | Sim | Busca de titular funcionou; dossie LGPD respondeu 200 e incluiu dados do cliente, vendas, e-commerce, preferencias, consentimentos, solicitacoes e logs. | Adicionadas migrations idempotentes para tabelas LGPD/e-commerce faltantes e ajustes de acessibilidade/nesting na tela. | OK local + smoke visual parcial |
| Premium bloqueado | Campanhas | `/campanhas` | `GET /campanhas/...` | Parcial | Menu/rota deve ficar bloqueado no basico. Antes havia chamadas indiretas gerando 403 em Lembretes. | Chamadas indiretas relevantes foram reduzidas; Lembretes agora respeita `moduloAtivo("campanhas")`. Tela premium completa nao foi retestada. | Corrigido parcial |
| Premium bloqueado | Veterinario | `/veterinario/*` | `GET /vet/...` | Parcial | Detalhe do pet chamava endpoints vet mesmo no basico. | `PetDetalhes` nao chama endpoints vet sem modulo. | Corrigido |
| Premium bloqueado | Bling/fiscal/integracoes | Layout/badges e Lembretes | `/integracoes/bling/...` | Sim, por erro observado | Layout/Lembretes chamavam Bling e recebiam 403 quando modulo bloqueado. | Layout ja estava condicionado a `moduloAtivo("bling")`; Lembretes tambem passou a respeitar `moduloAtivo("bling")`. | OK |

## 4. Checklist de isolamento tenant

Observacao: em 2026-05-15 foi feita auditoria A/B local automatizada com dois tenants criados pela API real de cadastro, selecao real de tenant, token real e endpoints reais. Em seguida foram feitas rodadas visuais no navegador para pagamentos/operadoras, PDV autocomplete, bloqueio de permissoes, PDV completo, Lembretes, Usuarios/Admin, Roles & Permissoes, LGPD operacional, calculadora de racao e opcoes de racao. Financeiro de vendas, configuracao da empresa e alguns cadastros auxiliares ainda precisam complemento visual.

| Area basica | Dados do tenant A aparecem no tenant B? | Criacao grava tenant_id correto? | Edicao respeita tenant? | Exclusao respeita tenant? | Endpoint sem tenant/token falha corretamente? | Status |
|---|---|---|---|---|---|---|
| Clientes | Nao: busca/listagem cruzada A/B passou | Sim, por endpoint real com token de cada tenant | Sim: edicao propria 200 e cruzada 404 | Sim: exclusao propria 204 e cruzada 404 | Sem token retornou 403; acesso direto cruzado a ID de outro tenant retornou 404 | OK |
| Pets | Nao: busca/listagem cruzada A/B passou | Sim, por endpoint real com tutor do mesmo tenant | Sim: edicao propria 200 e cruzada 404 | Sim: exclusao propria 204 e cruzada 404 | Sem token retornou 403; acesso direto cruzado a ID de outro tenant retornou 404 | OK |
| Produtos | Nao: busca/listagem cruzada A/B passou | Sim, por endpoint real com SKU distinto por tenant | Sim: edicao propria 200 e cruzada 404 | Sim: exclusao propria 204 e cruzada 404 | Sem token retornou 403; acesso direto cruzado a ID de outro tenant retornou 404 | OK |
| Estoque | Entrada propria retornou 200 e entrada cruzada em produto de outro tenant retornou 404 | Sim, por endpoint real com produto do tenant autenticado | Nao aplicavel | Nao testado | Cross-tenant por ID de produto retornou 404 | OK parcial |
| PDV/Vendas | Nao: GET cruzado de venda A/B retornou 404; autocomplete visual do operador A achou produto A e nao mostrou produto/SKU B | Sim, venda criada/finalizada com token de cada tenant e estoque baixado somente no produto do tenant; smoke visual `20260515201225` confirmou venda finalizada e estoque baixado | Visualizacao propria 200; visualizacao cruzada 404; edicao/reabertura ainda nao auditada completa | Nao testado | Sem tenant/token segue coberto por suites de auth; acesso direto cruzado a ID de outro tenant retornou 404 | OK local + smoke visual |
| Financeiro Vendas | Historico/reflexos de venda nao vazaram na rodada A/B local | Sim, finalizacao gerou DRE/financeiro sem 500 depois do alinhamento de schema | Tela visual ainda pendente | Nao testado | Nao testado nesta rodada visual | OK parcial |
| Usuarios/permissoes | Operador PDV do tenant A nao viu produto/cliente do tenant B e nao administrou RBAC; Usuarios/Admin e Roles exibiram apenas dados do tenant atual | Sim, admin criou operador/role com tenant correto e criou usuario pelo navegador com `tenant_id`/membership corretos | Status de usuario alterado no proprio tenant; edicao de role atualizou permissoes do proprio tenant; logout forcado limitado ao tenant selecionado | Exclusao de role propria removeu vinculos e retornou 204 | `/usuarios`, `/roles` e `/permissions` retornaram 403 para operador sem `usuarios.manage`; navegador exibiu acesso negado para operador/usuario sem permissao; reload de `/admin/usuarios` retornou somente chamadas 200 | OK local + smoke visual |
| Calculadora/catalogos de racao | Operador A nao viu produto/opcoes do tenant B; calculo cruzado por ID retornou 404 | Sim, admin criou catalogos/produtos em cada tenant e operador A acessou somente tenant A | Sim: linha de racao editada/inativada e apresentacao criada/inativada no proprio tenant | Mutacao de catalogo por operador sem permissao retornou 403 | Usuario sem `produtos.visualizar` recebeu 403 na calculadora | OK local + smoke visual |
| Catalogos auxiliares de produto | Operador A nao viu departamentos/categorias/marcas do tenant B; acesso direto cruzado retornou 404 | Sim, admin criou os tres cadastros em cada tenant | PUT cruzado de categoria B com admin A retornou 404 | Mutacao por operador sem permissao retornou 403 | Usuario sem `produtos.visualizar` recebeu 403 na listagem | OK local |
| Cadastros base | Formas de pagamento, taxas, operadoras e linha de racao nao vazaram entre tenants A/B; visual de formas/operadoras mostrou apenas tenant A | Sim, por endpoint real com token de cada tenant e usuario operacional nao-admin | Edicao cruzada de forma/taxa retornou 404 | Mutacao sem `configuracoes.editar` retornou 403 | Usuario sem permissao recebeu 403; acesso direto cruzado a IDs de outro tenant retornou 404 | OK local + smoke visual parcial |
| Modulos premium bloqueados | Bling e WhatsApp retornaram 403 no plano basico | Nao aplicavel | Nao aplicavel | Nao aplicavel | 403 observado em chamadas bloqueadas | OK parcial |

## 5. Correcoes aplicadas

| Arquivo alterado | Problema encontrado | Como foi corrigido | Risco antes | Como validou depois |
|---|---|---|---|---|
| `frontend/src/pages/Pessoas.jsx` | Listagem de Pessoas ainda tinha header, botoes, loading, empty state, tabela e acao de linha locais, fora da fundacao visual. | Migrado para `PageHeader`, `ActionButton`, `Panel`, `LoadingState`, `EmptyState`, `DataTable`, `CustomerIdentity`, `StatusBadge` e `IconActionButton`, mantendo filtros, importacao e fusao. | Tela essencial do Plano Basico ficava visualmente diferente e mais dificil de manter. | `npm --prefix frontend run build`. |
| `frontend/src/pages/ClienteFinanceiro.jsx` | Financeiro/historico do cliente ainda tinha header, loading, erro, cards, filtros, paginacao e empty state locais. | Migrado para `PageHeader`, `ActionButton`, `Panel`, `LoadingState`, `ErrorState`, `MetricGrid`, `MetricCard`, `IconActionButton` e `EmptyState`, preservando chamadas e tabela expandida. | Fluxo essencial do Plano Basico ficava visualmente desalinhado e mais dificil de manter. | `npm --prefix frontend run build`. |
| `frontend/src/pages/GerenciamentoPets.jsx` | Listagem de Pets ja estava avancada, mas ainda tinha header/loading/empty e alerta imperativo fora do padrao. | Migrado header para `PageHeader`, loading para `LoadingState`, vazio para `EmptyState` e erro de status para `toast.error`. | Experiencia menos consistente entre Pessoas/Pets e feedback de erro pouco padronizado. | `npm --prefix frontend run build`. |
| `frontend/src/pages/OperadorasCartao.jsx` | Tela de operadoras de cartao ainda usava header, acao principal e aviso importante locais, fora da fundacao visual do Plano Basico. | Migrado para `PageHeader`, `ActionButton` e `Panel`, mantendo hook, modal, cards e comportamento de guia. | Cadastro essencial ficava visualmente desalinhado e mais dificil de manter. | `npm --prefix frontend run build`. |
| `frontend/src/components/OpcoesRacao.jsx` | Tela de opcoes de racao tinha header, abas, paineis, loading, empty state e acoes locais; tambem exibia icones/textos quebrados por encoding antigo e campos sem associacao completa de label. | Migrado para componentes globais e icones `lucide`, preservando endpoints, formularios, lista, edicao, inativacao e guia; campos receberam `id/name` e labels vinculados. | Cadastro essencial ficava visualmente desalinhado, com manutencao mais custosa e console ruidoso em smoke visual. | Smoke visual `20260515181603`: linha criada/editada/inativada, apresentacao criada/inativada, chamadas 200 e console limpo; `npm --prefix frontend run build`. |
| `frontend/src/pages/CalculadoraRacao.jsx` | Campos da calculadora estavam funcionais, mas sem `id/name` e label associado, gerando warnings de formulario no navegador durante a auditoria visual. | Busca de pet, peso, idade, atividade, busca de racao, comparativo, filtros e selects receberam `id/name` consistentes; `RacaoSearchInput` passou a receber e repassar esses atributos. | Console ruidoso podia mascarar falhas reais e prejudicava acessibilidade da tela basica. | Smoke visual `20260515181603`: operador nao-admin buscou racao, calculou consumo, rodou comparativo, chamadas 200 e console limpo. |
| `backend/app/pets_routes.py` | `GET /pets?busca=...` fazia join com `clientes` duas vezes e quebrava no Postgres com `DuplicateAlias`. | Removido o segundo join dentro do filtro de busca, mantendo o join base usado para isolamento por tenant. | Busca de pets podia falhar com 500 e impedir auditoria A/B/uso da tela. | Auditoria A/B local passou em criacao, listagem e acesso cruzado de pets. |
| `backend/app/produtos_routes.py` | `POST /produtos/{id}/entrada` gravava movimentacao sem `user_id` e quebrava com 500. | Incluido `user_id=current_user.id` ao criar `EstoqueMovimentacao`. | Fluxo basico de estoque quebrava ao fazer entrada pela tela do produto. | `python -m compileall backend/app/produtos_routes.py`; reteste manual do endpoint retornou 200. |
| `frontend/src/components/AlertasIA.jsx` | Dashboard/plano basico disparava endpoints de financeiro ERP/IA premium e recebia 403. | Componente agora retorna vazio sem chamar API quando `financeiro_erp` ou `ia_avancada` estao bloqueados. | Console poluido por 403 e risco de experiencia ruim no plano basico. | `npm --prefix frontend run build`. |
| `frontend/src/components/ProjecoesIA.jsx` | Fluxo/projecoes chamavam financeiro ERP sem modulo ativo. | Componente agora nao chama API quando `financeiro_erp` esta bloqueado. | Chamadas premium indevidas e 403 em plano basico. | `npm --prefix frontend run build`. |
| `frontend/src/hooks/useClientesNovoCadastro.js` | Cadastro/edicao de cliente podia buscar saldo de campanhas no plano basico. | `loadSaldoCampanhas` agora respeita `moduloAtivo("campanhas")`. | 403 no cadastro/financeiro do cliente e ruido em fluxo basico. | `npm --prefix frontend run build`. |
| `frontend/src/pages/PetDetalhes.jsx` | Detalhe do pet chamava carteirinha/internacoes/consultas/exames vet mesmo com modulo veterinario bloqueado. | Chamadas vet agora sao ignoradas quando `veterinario` nao esta ativo. | 403 em tela basica de pet e vazamento de experiencia premium. | `npm --prefix frontend run build`. |
| `frontend/src/pages/PetForm.jsx`, `frontend/src/components/QuickAddModal.jsx`, `backend/app/cadastros_routes.py`, `backend/tests/unit/test_plano_basico_tenant_contract.py` | Cadastro rapido de raca podia depender de `especie_id` invalido e o contrato do Plano Basico nao monitorava `cadastros_routes.py`. | `PetForm` bloqueia raca sem especie, limpa raca ao trocar especie e usa nome da especie selecionada; `QuickAddModal` valida `especie_id`, mostra erro corrigivel e tem `id/name` no campo; contrato passou a cobrir a rota de cadastros. | Empresa nova poderia ver erro pouco claro ou raca presa na especie errada durante cadastro de pet; regressao de tenant em especies/racas ficaria sem alerta automatizado. | Smoke visual `202605151900`: especie e raca criadas pelo modal, raca selecionada, chamadas 201/200; contrato `10 passed`; build frontend passou. |
| `backend/app/api/v1/empresa_fiscal.py`, `backend/app/empresa_routes.py`, `backend/app/empresa_config_routes.py`, `frontend/src/App.jsx`, `frontend/src/pages/Configuracoes.jsx`, `backend/tests/unit/test_plano_basico_tenant_contract.py` | Configuracoes da empresa estavam protegidas no menu principal, mas subrotas/API podiam ficar expostas para usuario autenticado sem permissao correta; o hub tambem mostrava cards premium mesmo em tenant basico. | Endpoints de dados/fiscal exigem `configuracoes.empresa` ou `configuracoes.editar`; configuracao geral/estoque exige `configuracoes.editar`; subrotas frontend e `/admin/roles` receberam `ProtectedRoute`; cards de entregas/integracoes somem sem modulo ativo. | Usuario operacional poderia tentar alterar dados da empresa por chamada direta/API; tenant basico podia ver atalhos premium que nao pertencem ao plano. | Contrato focado `12 passed`; `npm --prefix frontend run build`; `git diff --check`. |
| `frontend/src/App.jsx` | Warnings do React Router sobre flags futuras. | Ativadas flags `v7_startTransition` e `v7_relativeSplatPath`. | Ruido no console durante testes. | `npm --prefix frontend run build`. |
| `frontend/src/pages/Login.jsx` | Warning de autocomplete em campos de senha. | Adicionado `autoComplete="username"` e `autoComplete="current-password"`. | Ruido no console/navegador. | `npm --prefix frontend run build`. |
| `frontend/src/pages/Register.jsx` | Warning de autocomplete em campos de senha/cadastro. | Adicionado `autoComplete="email"` e `autoComplete="new-password"`. | Ruido no console/navegador. | `npm --prefix frontend run build`. |
| `backend/alembic/versions/oj20260515a1_repair_onboarding_local_schema.py` | Cadastro real de tenant falhava localmente porque o schema DEV nao tinha colunas/tabelas usadas pelo onboarding e jobs recentes. | Migration idempotente adiciona `categorias_financeiras.tipo_custo`, tabela `bling_pedido_webhook_events` e indices de pedidos integrados quando necessario. | Testes locais ficavam ficticios ou bloqueados antes do cadastro real do tenant. | `alembic upgrade head`; `POST /auth/register` deixou de falhar nesse ponto. |
| `backend/alembic/versions/ok20260515a2_create_missing_ration_option_tables.py` | Onboarding obrigatorio nao conseguia criar opcoes de racao porque as tabelas auxiliares nao existiam. | Criadas `linhas_racao`, `portes_animal`, `fases_publico`, `tipos_tratamento`, `sabores_proteina` e `apresentacoes_peso` com indices por tenant. | Novo tenant podia falhar no cadastro ou nascer sem dados obrigatorios. | `alembic upgrade head`; cadastro real A/B passou. |
| `backend/app/models.py` e `backend/alembic/versions/ol20260515a3_pet_codigo_unique_per_tenant.py` | Codigo de pet era unico globalmente e colidia quando dois tenants tinham o primeiro cliente/pet com o mesmo codigo. | Removida unicidade global do modelo e trocado o indice para unico composto `(tenant_id, codigo)`. | Segundo tenant podia receber erro 500 ao criar pet com codigo interno igual ao de outro tenant. | Auditoria A/B criou pet `10001-PET-0001` nos dois tenants sem colisao. |
| `frontend/src/pages/LandingPage.jsx`, `frontend/src/pages/Register.jsx`, `frontend/src/contexts/AuthContext.jsx`, `backend/app/auth_routes_multitenant.py` | Contratacao por plano existia visualmente em `/planos`, mas o plano escolhido nao era parte explicita do contrato com a API. | Landing recebeu bloco de selecao do Basico; register envia `plan`; backend valida plano permitido e grava o tenant com o plano selecionado. | Futuro autoatendimento poderia parecer selecionar plano sem o backend respeitar o contrato. | Build frontend, cadastro real com `plan=basico`, bloqueio de `plan=premium` e consulta do tenant no banco. |
| `backend/alembic/versions/om20260515a4_add_venda_retirada_fields.py` | Criacao de venda no fluxo PDV A/B quebrava com 500 porque o modelo esperava campos de retirada que nao existiam no schema local. | Migration idempotente adiciona `vendas.tipo_retirada` e `vendas.palavra_chave_retirada`. | PDV do Plano Basico podia quebrar antes de finalizar a venda. | `alembic upgrade head`; criacao de venda A/B passou. |
| `backend/alembic/versions/on20260515a5_create_empresa_config_fiscal.py` | Finalizacao de venda abortava a transacao ao buscar configuracao fiscal inexistente no banco. | Migration cria `empresa_config_fiscal` conforme modelo atual, com indice por tenant. | Venda finalizada podia virar 500 por dependencia fiscal opcional. | `alembic upgrade head`; tabela conferida no Postgres; finalizacao A/B avancou. |
| `backend/alembic/versions/oo20260515a6_add_dre_subcategoria_fields.py` | Geracao de DRE por competencia na finalizacao buscava `dre_subcategorias.custo_pe` e `categoria_financeira_id`, ausentes no schema. | Migration adiciona os campos e FK opcional para `categorias_financeiras`. | Finalizacao de venda ficava vulneravel a 500 em tenants novos. | Venda A/B `20260515154447` finalizou nos dois tenants; estoque baixou corretamente; migrations passaram em banco limpo. |
| `backend/app/roles_routes.py`, `backend/app/permissions_routes.py`, `backend/tests/unit/test_plano_basico_tenant_contract.py` | Operador PDV sem `usuarios.manage` conseguia criar role e listar permissoes globais. | Endpoints administrativos de roles/permissoes agora exigem `usuarios.manage`; contrato automatizado protege a regra. | Escalada de permissao dentro do tenant por usuario operacional. | Rodada usuario A/B `20260515155144`: `/usuarios`, `/roles` e `/permissions` retornaram 403 para operador; suite tenant/hardening reexecutada. |
| `backend/app/opcoes_racao_routes.py`, `backend/app/calculadora_racao.py`, `backend/app/api/racao_calculadora_routes.py`, `backend/tests/unit/test_plano_basico_tenant_contract.py` | Catalogos de racao e calculadora tinham isolamento por tenant, mas dependiam apenas de autenticacao em alguns pontos. | Leitura exige `produtos.visualizar`; criacao de opcoes exige `produtos.criar`; edicao/exclusao exige `produtos.editar`; calculadoras exigem `produtos.visualizar`; contrato automatizado adicionado. | Usuario autenticado com permissao limitada podia mexer em cadastro auxiliar ou consultar calculadora fora da politica de produto. | Rodada racao A/B `20260515160544`: catalogos isolados, mutacao negada ao operador, busca/calculo cruzado 404 e usuario sem produto 403. |
| `backend/app/produtos_routes.py`, `backend/tests/unit/test_plano_basico_tenant_contract.py` | Categorias, marcas e departamentos tinham tenant correto, mas faltava permissao granular; marcas/departamentos tambem falhavam com `user_id` nulo. | Leitura exige `produtos.visualizar`; criacao exige `produtos.criar`; edicao/exclusao exige `produtos.editar`; marcas/departamentos gravam `user_id`; contagens de delete filtram tenant. | Usuario limitado podia alterar cadastros auxiliares e criacao de departamento/marca podia dar 500. | Rodada catalogos A/B `20260515161002`: isolamento OK, mutacao de operador 403, cross-tenant 404 e usuario sem produto 403. |
| `backend/app/security/permissions_decorator.py`, `backend/app/financeiro_routes.py`, `backend/app/formas_pagamento_routes.py`, `backend/app/operadoras_routes.py`, `backend/tests/unit/test_plano_basico_tenant_contract.py` | Formas de pagamento, taxas e operadoras tinham tenant correto em parte do CRUD, mas faltava permissao granular e algumas consultas auxiliares de taxa/analise nao filtravam tenant. | Criado `require_any_permission`; leitura aceita `vendas.criar` ou `configuracoes.editar`; mutacoes exigem `configuracoes.editar`; taxas, analise e imposto padrao filtram por tenant. | Operador/usuario autenticado poderia acessar cadastro auxiliar fora da politica; analise de venda podia considerar forma/taxa de outro tenant por ID direto. | Rodada pagamentos/operadoras A/B `20260515161901`: operador nao-admin leu apenas tenant A, usuario sem permissao recebeu 403, mutacoes sem config deram 403, cross-tenant retornou 404 e analise nao processou forma do tenant B. |
| `frontend/src/contexts/ModulosContext.jsx` | Em DEV, durante a hidratacao da sessao, o contexto inicializava modulos premium como ativos antes de confirmar `/modulos/status`. | Sem usuario logado, o estado agora fica em carregamento (`null`) para evitar uma janela em que telas autenticadas chamam endpoints premium. | Plano basico podia disparar chamadas premium no primeiro render e gerar 403 intermitente. | Smoke visual em navegador isolado: formas de pagamento carregou sem chamadas a `contas-bancarias` e sem badge Bling. |
| `frontend/src/components/FormasPagamento.jsx` | Tela de formas sempre buscava contas bancarias e exibia campo/coluna de conta destino, que pertence ao Financeiro ERP premium. | Busca, coluna e campo de conta destino agora aparecem apenas com `financeiro_erp` ativo confirmado. | Usuario basico recebia 403 e via elemento premium indevido em cadastro essencial. | Smoke visual `20260515162539`: rede limpa, sem 403, forma A visivel, conta destino oculta. |
| `frontend/src/components/Layout.jsx` | Badge/resumo Bling podia ser chamado antes da confirmacao real dos modulos do tenant. | Chamada de Bling agora depende de usuario autenticado e lista de modulos confirmada. | Tenant basico podia gerar 403 de Bling no carregamento. | Smoke visual `20260515162539`: sem chamada a `/integracoes/bling/nf/autocadastros-recentes`. |
| `frontend/src/components/ModaisCaixa.jsx` | Modais de sangria/suprimento davam a entender que origem/destino eram obrigatorios, embora o caixa basico nao dependa de banco. | Labels ajustadas para origem/destino opcionais e opcao inicial `Nao informar`. | Usuario do plano basico poderia achar que precisava cadastrar banco para bater o caixa. | Revisao do contrato: backend aceita movimentacao sem conta bancaria; `npm --prefix frontend run build`. |
| `backend/app/security/permissions_service.py` | Permissoes implicitas apareciam no frontend, mas o backend ainda exigia a permissao gravada diretamente no role. Operador com `vendas.criar` recebia 403 em chamadas auxiliares como entregadores/clientes. | `get_user_permissions` e `check_permission` agora retornam/validam permissoes efetivas expandidas. | Operador PDV nao-admin podia abrir a tela mas receber 403 indevido em fluxos basicos. | Testes unitarios e smoke visual do PDV: `/clientes/?is_entregador=true` passou de 403 para 200. |
| `backend/app/produtos_routes.py` | Busca/autocomplete de produtos usava fallback numerico mesmo em SKU alfanumerico, podendo retornar produto do proprio tenant com SKU parecido ao buscar outro SKU A/B. | Fallback por digitos agora roda apenas quando o termo digitado nao tem letras; SKUs alfanumericos usam busca textual completa. | Autocomplete podia sugerir produto errado em SKUs parecidos, confundindo validacao de isolamento. | Testes unitarios; API e navegador: busca por SKU B no tenant A retornou `items=[]`, busca por SKU A retornou o produto A. |
| `frontend/src/pages/Lembretes.jsx` | Lembretes carregava alertas de campanhas, DRE e Bling mesmo quando o tenant basico nao tinha esses modulos. | Chamadas premium agora so rodam com `moduloAtivo("campanhas")`, `moduloAtivo("financeiro_erp")` e `moduloAtivo("bling")`; estados sao zerados quando o modulo esta bloqueado. | Console/rede do plano basico ficavam com 403 premium que nao pertencem ao fluxo vendido. | Navegador em `/lembretes`: somente `/auth/me-multitenant`, `/modulos/status` e `/lembretes/pendentes`, todos 200, sem console error. |
| `frontend/src/pages/UsuariosPage.jsx`, `frontend/src/components/usuarios/UsuarioModal.jsx`, `frontend/src/components/usuarios/UsuariosTable.jsx`, `frontend/src/hooks/useUsuariosPage.js` | Tela de Usuarios/Admin ainda usava estrutura visual local, `alert` e mensagens pouco direcionais para erros corrigiveis. | Migrado para `PageHeader`, `ActionButton`, `Panel`, `DataTable`, `StatusBadge`, `IconActionButton` e `toast`; modal passou a exibir erro de formulario com orientacao clara. | Tela essencial de administracao do tenant ficava desalinhada e o usuario nao entendia bem erros como e-mail duplicado. | Smoke visual `20260515173417`: listagem, criacao de usuario, e-mail duplicado com mensagem clara, desativacao e logout forcado passaram. |
| `frontend/src/pages/RolesPage.jsx`, `frontend/src/hooks/useRolesPage.js`, `frontend/src/components/roles/RoleCard.jsx`, `frontend/src/components/roles/RoleModal.jsx` | Tela de perfis/permissoes tinha 408 linhas, `alert`, icones mistos e estrutura visual local. | Quebrada em hook e componentes reutilizaveis; migrada para `PageHeader`, `ActionButton`, `Panel`, `StatusBadge`, `IconActionButton`, `LoadingState`, `EmptyState` e `toast`; duplicidade/403/role em uso agora exibem mensagem direcionada. | Fluxo essencial de administracao ficava desalinhado e mais dificil de manter; erros corrigiveis apareciam de forma pobre. | Smoke visual `20260515175152`: criar perfil, tentar duplicado, editar permissoes e excluir passaram. |
| `backend/app/roles_routes.py` | Exclusao de role com permissoes vinculadas retornava 500 por FK em `role_permissions`. | Delete agora remove `RolePermission` do mesmo `tenant_id` antes de excluir a role. | Admin nao conseguia limpar perfil criado errado, gerando erro de sistema em acao corrigivel. | Reteste visual/API: `DELETE /roles/{id}` passou de 500 para 204 e o card saiu da tela. |
| `frontend/src/pages/LGPDOperacional.jsx`, `frontend/src/components/clientes/PessoaSelector.jsx`, `frontend/src/components/ui/FormField.jsx` | LGPD tinha warnings de campos sem `id/name` e sugestao clicavel como `button` contendo botoes internos de copiar. | `TextField`/`PessoaSelector` receberam `id/name`; sugestao de cliente virou `div role=button` acessivel por teclado, removendo nested button. | Console ficava ruidoso durante auditoria visual e podia mascarar erro real. | Reteste visual: busca de titular funcionou sem warnings relevantes e sem nesting warning. |
| `backend/alembic/versions/op20260515a7_create_missing_lgpd_privacy_tables.py`, `backend/alembic/versions/oq20260515a8_create_missing_ecommerce_order_tables.py` | Dossie LGPD local quebrava com 500 por tabelas ausentes (`data_privacy_consents` e depois `pedidos`). | Migrations idempotentes criam as tabelas LGPD/e-commerce faltantes quando necessario e mantem downgrade nao destrutivo. | Teste local ficava ficticio: a tela podia falhar por schema diferente de producao/novo tenant. | `alembic upgrade head` local chegou em `oq20260515a8`; `GET /lgpd/clientes/{id}/dossie` retornou 200. |
| `backend/app/utils/tenant_safe_sql.py`, `backend/app/db/sql_audit.py` | `pedidos` e `pedido_itens` nao estavam declarados nas listas de tabelas tenant-scoped usadas pelos guardrails de SQL bruto. | Tabelas de e-commerce adicionadas ao contrato tenant-safe/auditoria. | SQL bruto futuro poderia tocar pedidos de e-commerce sem o mesmo alerta de tenant aplicado a vendas/clientes. | Revisao estatica e build/testes da branch. |
| `frontend/src/api.js` e `frontend/src/services/api.ts` | Interceptor sobrescrevia `Authorization` explicito quando havia token antigo em storage, quebrando `/auth/select-tenant` com temp token. | Interceptor agora so injeta Bearer de sessao se a request ainda nao trouxe `Authorization`. | Login/selecao de tenant podia falhar de forma intermitente com token stale, criando teste ficticio e risco real em troca de tenant. | Smoke visual: apos limpar sessao e repetir login, `/auth/login-multitenant` e `/auth/select-tenant` passaram e a tela autenticada abriu corretamente. |
| `backend/app/session_manager.py`, `backend/app/usuarios_routes.py`, `backend/tests/unit/test_session_manager.py` | Logout forcado revogava sessoes do usuario sem limitar pelo tenant selecionado; vinculo por `user_id` podia buscar usuario fora do tenant atual. | `revoke_all_sessions` recebeu filtro opcional `tenant_id`; rota de logout forcado passa o tenant atual; vinculacao de usuario agora busca `User.tenant_id == tenant_id`; teste unitario cobre revogacao limitada ao tenant. | Admin de um tenant poderia afetar sessoes de outro tenant em usuario compartilhado/legado, e ID direto aumentava a superficie de associacao indevida. | Suite `test_session_manager.py`, `test_usuarios_routes_errors.py` e `test_plano_basico_tenant_contract.py`: `14 passed`; smoke visual confirmou logout forcado sem erro e contagem retornada. |

## 6. Pendencias priorizadas

### P0 - Bloqueia vender / risco de vazamento / quebra fluxo basico

- Nenhuma pendencia P0 confirmada nesta rodada depois das correcoes da branch.
- Observacao: antes da correcao, `POST /produtos/{id}/entrada` era P0 para estoque/produto porque quebrava fluxo basico; agora esta corrigido.

### P1 - Importante antes de escalar

- Complementar comparacao A/B real entre dois tenants para fluxos ainda nao cobertos:
  - demais cadastros auxiliares e CRUD visual completo onde so houve API/smoke parcial.
- Complementar smoke visual no navegador para PDV/vendas:
  - a API A/B ja passou com finalizacao e baixa de estoque;
  - operador, permissoes implicitas, autocomplete de produto, caixa/sangria/suprimento por API e finalizacao visual ja passaram;
  - falta conferir recibo/historico visual com mais calma, sem bloquear a venda controlada.
- Retestar visualmente entrada de estoque com lote/validade:
  - o endpoint passou no A/B e a suite focada de lote/validade passou com `8 passed`;
  - ainda falta confirmar tela, tooltip/listagem de lotes e validade urgente no navegador.
- Testar CRUD completo de:
  - categorias/departamentos/marcas visualmente;
  - formas de pagamento alem do smoke de listagem sem premium;
  - configuracao da empresa no navegador, com salvar fiscal/geral/estoque.
- Conferir endpoint sem token/tenant para areas basicas:
  - deve retornar 401/403;
  - nao deve retornar dados.
- Revisar menus do plano basico:
  - hub de configuracoes ja esconde entregas/integracoes sem modulo ativo;
  - confirmar que apenas o essencial aparece nas demais areas;
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

```powershell
python -m py_compile backend/app/models.py backend/alembic/versions/oj20260515a1_repair_onboarding_local_schema.py backend/alembic/versions/ok20260515a2_create_missing_ration_option_tables.py backend/alembic/versions/ol20260515a3_pet_codigo_unique_per_tenant.py
```

Resultado: passou.

```powershell
docker compose -f docker-compose.local-dev.yml exec -T backend alembic upgrade head
docker compose -f docker-compose.local-dev.yml exec -T backend alembic current
```

Resultado: passou; head local atualizado em `oq20260515a8`.

```powershell
docker compose -f docker-compose.local-dev.yml exec -T postgres psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS petshop_migration_check WITH (FORCE);" -c "CREATE DATABASE petshop_migration_check;"
docker compose -f docker-compose.local-dev.yml exec -T -e DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/petshop_migration_check backend alembic upgrade head
docker compose -f docker-compose.local-dev.yml exec -T -e DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/petshop_migration_check backend alembic current
```

Resultado: passou em banco temporario limpo; head `oq20260515a8`, tabelas auxiliares de racao/webhook/LGPD/e-commerce, indice `uq_pets_tenant_codigo`, `empresa_config_fiscal` e campos novos de DRE/vendas foram criados.

```powershell
# Auditoria A/B local real 2026-05-15
# 1. criar dois tenants por POST /auth/register;
# 2. selecionar tenant por POST /auth/select-tenant;
# 3. criar cliente, pet, forma de pagamento e linha de racao em cada tenant;
# 4. comparar listagem e acesso direto cruzado por ID;
# 5. confirmar bloqueio de Bling/WhatsApp no plano basico.
```

Resultado: passou na rodada `20260515152334`.

- Tenant A: `tenant.a.20260515152334@example.com`, tenant `57b4aa0a-ddfc-496d-969b-015a706171f4`.
- Tenant B: `tenant.b.20260515152334@example.com`, tenant `af90babf-6ad0-4a41-902b-781aa2a8b38f`.
- Cliente A/B criados por endpoint real e nao aparecem no outro tenant.
- Acesso direto cruzado a `/clientes/{id}` retornou 404.
- Pets A/B criados com o mesmo codigo interno `10001-PET-0001`, agora isolado por tenant.
- Formas de pagamento A/B e linhas de racao A/B nao aparecem no outro tenant.
- `/bling/monitor/resumo` e `/whatsapp/analytics/dashboard` retornaram 403 no plano basico.

Rodada de contratacao por plano `20260515153410`:

- `POST /auth/register` com `plan=premium` retornou 400.
- `POST /auth/register` com `plan=basico` retornou 200.
- Tenant criado `45e438b6-01ab-4e2c-8f8e-4303b5934fe8` ficou com `plan=basico` no banco.

Rodada PDV/vendas A/B `20260515154447`:

- Tenant A: `4b586466-1e70-44ae-8ac3-7edd9b757902`.
- Tenant B: `f6c1c6e7-f86a-45c6-815b-9a6f4c492991`.
- Cada tenant criou cliente, produto com lote, entrada de estoque e caixa aberto por API real.
- Venda A `3` e venda B `4` finalizaram com status `finalizada`, total `50.0` e estoque final `3.0`.
- GET cruzado de venda retornou 404 nos dois sentidos.
- Produto do tenant A nao apareceu na lista do tenant B, e vice-versa.

Rodada usuarios/permissoes A/B `20260515155144`:

- Tenant A: `03899ca2-56c8-47f6-8aa2-21359d66750a`.
- Tenant B: `cf980a30-2757-4ff3-9244-30a4e7c3eeed`.
- Admin criou role `Operador PDV` com `clientes.visualizar`, `produtos.visualizar` e `vendas.criar`.
- Operador A encontrou produto/cliente do tenant A e nao encontrou produto/cliente do tenant B em busca/autocomplete.
- Acesso direto cruzado a produto/cliente do tenant B retornou 404.
- Venda propria pelo operador A foi criada; tentativa de venda com cliente/produto do tenant B retornou 404.
- `/usuarios`, `/roles` e `/permissions` retornaram 403 para operador sem `usuarios.manage`.

Rodada racao/catalogos A/B `20260515160544`:

- Tenant A: `d51067c0-3c99-420d-a9f2-db2bb9421d0b`.
- Tenant B: `f4987049-e92c-404d-ac68-1cb5553a4d20`.
- Operador A: `qa.racao.operador.a.20260515160544@example.com`, com `produtos.visualizar`.
- Produto A `29` e produto B `30` criados com tabela de consumo e opcoes de racao por tenant.
- Operador A listou opcoes do tenant A e nao recebeu opcoes do tenant B.
- `POST /opcoes-racao/linhas` retornou 403 para operador sem `produtos.criar`.
- Busca da calculadora por produto A retornou item; busca por produto B retornou lista vazia.
- Calculo legado `/produtos/calculadora-racao` e interno `/internal/racao/calcular` funcionaram para produto A e retornaram 404 quando forcaram produto B.
- Usuario sem `produtos.visualizar` recebeu 403 na busca da calculadora e no calculo interno.

Rodada cadastros auxiliares de produto A/B `20260515161002`:

- Tenant A: `01e90215-6c19-401a-9ee9-aa7244442f01`.
- Tenant B: `ea6572a5-3aba-4380-826c-d9c099b2f8ed`.
- Operador A: `qa.catalogo.operador-a.user.20260515161002@example.com`, com `produtos.visualizar`.
- Departamento A `29`, categoria A `57`, marca A `1`; departamento B `30`, categoria B `58`, marca B `2`.
- Operador A listou apenas departamentos/categorias/marcas do tenant A.
- Acesso direto cruzado aos IDs do tenant B retornou 404.
- PUT cruzado em categoria B usando admin A retornou 404.
- Operador com apenas `produtos.visualizar` recebeu 403 ao criar/editar/excluir cadastros auxiliares.
- Usuario sem `produtos.visualizar` recebeu 403 ao listar categorias.

Rodada visual no navegador `20260515162539`:

- Tenant A: `03b3e67b-5dce-451e-bcd0-1138c951eeb8`.
- Tenant B: `763be7ad-50e5-4d97-955e-70b1f53a3157`.
- Usuario de configuracao A abriu `/cadastros/financeiro/formas-pagamento`; forma A apareceu, coluna/campo de conta destino ficaram ocultos no Basico e a rede ficou sem `contas-bancarias`, sem Bling e sem 403.
- Usuario de configuracao A abriu `/cadastros/financeiro/operadoras`; operadora A apareceu e operadora B nao apareceu.
- Operador A abriu `/pdv`, com permissoes `clientes.visualizar`, `produtos.visualizar` e `vendas.criar`.
- Autocomplete visual de produto no PDV encontrou `QA Produto A 20260515162539` e nao exibiu `QA Produto B 20260515162539`.
- Acesso direto do operador a `/cadastros/financeiro/formas-pagamento` mostrou acesso negado por falta de `configuracoes.editar`.
- Usuario sem permissoes abriu `/pdv` e recebeu acesso negado por falta de `vendas.criar`.
- Console sem erro relevante; unico aviso observado foi do tour do PDV para seletor ausente `#tour-pdv-resumo`.

Rodada visual no navegador `20260515201225`:

- API local 8001 e Vite 5174 apontado explicitamente para `VITE_DEV_API_PROXY_TARGET=http://127.0.0.1:8001`.
- Operador A: `qa.basico.operador.a.20260515165148@example.com`, com permissao direta `vendas.criar` e permissoes efetivas expandidas.
- `/pdv` abriu com `Caixa #2`; produto `QA-PDV-A-20260515165148` foi encontrado pelo autocomplete e adicionado a venda.
- Pagamento em Dinheiro de `R$ 12,90` foi registrado pelo modal visual; `POST /vendas` e `POST /vendas/10/finalizar` retornaram 200.
- Venda `202605150002` ficou `finalizada`, com total `12.90`, item gravado e estoque do produto A baixado para `6`.
- `/lembretes` foi recarregado no mesmo operador basico; rede chamou apenas `me`, `modulos/status` e `lembretes/pendentes`, todos 200, sem console error e sem chamadas premium a campanhas/DRE/Bling.

Rodada visual Usuarios/Admin `20260515173417`:

- API local 8001 e Vite 5174 contra Postgres DEV, com tenant novo criado pelo fluxo real.
- Admin abriu `/admin/usuarios`; `/usuarios`, `/roles`, `/auth/me-multitenant`, `/modulos/status` e `/lembretes/pendentes` retornaram 200 no caminho normal.
- Criacao de usuario pelo modal retornou 200 e o usuario apareceu na tabela com role Administrador.
- Tentativa de criar e-mail duplicado retornou 409 e a tela exibiu mensagem corrigivel: usar outro e-mail ou verificar se o usuario ja existe.
- Desativacao de acesso retornou 200 e atualizou status visual para Inativo.
- Logout forcado retornou 200 com escopo limitado ao tenant atual.
- Conferencia no banco confirmou usuario e membership com o mesmo `tenant_id` do tenant de teste.
- A primeira tentativa de login revelou bug real de token stale no interceptor; corrigido em `frontend/src/api.js` e `frontend/src/services/api.ts`.

Rodada visual/API Roles & LGPD `20260515175152`:

- API local 8001 e Vite 5174 contra Postgres DEV, com tenant novo criado pelo fluxo real.
- Admin abriu `/admin/roles`; `/roles` e `/permissions` retornaram 200.
- Criacao de perfil com permissoes de Vendas/Produtos retornou 200 e apareceu na lista.
- Tentativa de duplicar o mesmo nome retornou 400 e a tela exibiu mensagem corrigivel para usar outro nome ou editar o perfil existente.
- Edicao do perfil atualizou nome/permissoes com `PUT /roles/{id}` 200.
- Exclusao inicialmente revelou bug real de FK em `role_permissions`; apos correcao, `DELETE /roles/{id}` retornou 204 e o perfil saiu da lista.
- Admin abriu `/admin/lgpd`; status/solicitacoes retornaram 200, busca de titular encontrou o cliente de teste e o dossie LGPD retornou 200.
- Primeira tentativa de dossie revelou gaps de schema local em tabelas LGPD/e-commerce; corrigido com migrations idempotentes ate `oq20260515a8`.

```powershell
# Auditoria A/B local historica 2026-05-15
# 1. semear dois tenants DEV locais diretamente no banco;
# 2. fazer login real em /auth/login-multitenant;
# 3. selecionar tenant em /auth/select-tenant;
# 4. criar cliente, pet e produto em cada tenant;
# 5. comparar listagem e acesso direto cruzado por ID.
```

Resultado: passou para clientes, pets e produtos. Rodada `866741`:

- Tenant A: cliente `9`, pet `9`, produto `9`.
- Tenant B: cliente `10`, pet `10`, produto `10`.
- Listagem por busca mostrou apenas dados do tenant autenticado.
- Acesso direto cruzado a `/clientes/{id}`, `/pets/{id}` e `/produtos/{id}` retornou 404.

Observacao de ambiente historica: antes das migrations `oj20260515a1` e `ok20260515a2`, o onboarding local por `/auth/register` ficava bloqueado por gaps de schema do DEV. Esse bloqueio foi corrigido e a rodada A/B real acima substitui o atalho por seed direto no banco.

Rodada estendida `866987` + reteste de estoque:

- Sem token em `/clientes/`, `/pets` e `/produtos/`: 403.
- Cliente: edicao propria 200, edicao cruzada 404, exclusao propria 204, exclusao cruzada 404.
- Pet: edicao propria 200, edicao cruzada 404, exclusao propria 204, exclusao cruzada 404.
- Produto: edicao propria 200, edicao cruzada 404, exclusao propria 204, exclusao cruzada 404.
- Estoque: entrada propria 200 e entrada cruzada por ID de produto de outro tenant 404 nos dois tenants.
- Observacao de ambiente: o primeiro teste de entrada de estoque retornou 500 porque o schema DEV local nao tinha `estoque_movimentacoes.status`; apos alinhar a coluna local ao modelo atual, o reteste passou.

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
- Smoke visual de formas de pagamento no Basico sem chamadas premium: testado.
- Smoke visual de operadoras no Basico com isolamento A/B: testado.
- Smoke visual de PDV como operador nao-admin e autocomplete de produto A/B: testado.
- Smoke visual de finalizacao do PDV com Dinheiro e baixa de estoque: testado.
- Smoke visual de Lembretes no Basico sem chamadas premium a campanhas/DRE/Bling: testado.
- Smoke visual de Usuarios/Admin com criacao, erro corrigivel, desativacao e logout forcado: testado.
- Smoke visual de Roles & Permissoes com criacao, duplicidade, edicao e exclusao: testado.
- Smoke visual/API de LGPD operacional com busca de titular e dossie: testado.
- Smoke visual de Calculadora de Racao com operador nao-admin, busca, calculo e comparativo: testado.
- Smoke visual de Opcoes de Racao com listagem, criacao/edicao/inativacao de linha e criacao/inativacao de apresentacao: testado.
- Smoke visual de cadastro rapido de especie/raca no formulario de pet: especie criada, raca criada, raca selecionada e chamadas 201/200.
- Smoke visual de bloqueio de permissao para operador/usuario sem acesso: testado.
- Health check de producao: apenas endpoint de saude consultado, sem deploy e sem alteracao.

### Testes backend amplos

- Suite multitenant/hardening reexecutada nesta rodada: `74 passed`.
- Migrations completas reexecutadas em banco Postgres limpo ate `oq20260515a8`.
- Contrato de Plano Basico/racao/cadastros reexecutado nesta rodada: `14 passed`.
- Rodada API A/B de racao/catalogos concluida na API local 8001 apontada para o Postgres DEV, usando o codigo atual da branch.
- Contrato de catalogos auxiliares de produto reexecutado nesta rodada: `8 passed`.
- Rodada API A/B de departamentos/categorias/marcas concluida na API local 8001 apontada para o Postgres DEV.
- Rodada API A/B de pagamentos/operadoras `20260515161901` concluida na API local 8001 apontada para o Postgres DEV, com operador de vendas, usuario de configuracao e usuario sem permissao.
- Rodada visual `20260515162539` concluida no Vite local 5174 contra API local 8001, com usuarios nao-admin e dois tenants A/B.
- Testes unitarios de permissoes efetivas e busca de produto: `tests/unit/test_permissions_service.py` e `tests/unit/test_produtos_search_helpers.py`, resultado `4 passed`.
- Testes unitarios de Usuarios/Admin, sessao e contrato basico reexecutados: `14 passed`.
- Smoke visual de calculadora/opcoes de racao `20260515181603`: chamadas 200, console limpo e CRUD visual de opcoes validado.
- Contrato focado Plano Basico/racao reexecutado apos o smoke visual: `14 passed`.
- Build frontend apos ajustes de labels/ids em calculadora/opcoes de racao: `npm --prefix frontend run build`, resultado passou.
- Contrato Plano Basico apos ajuste de cadastro rapido especie/raca: `10 passed`.
- Build frontend apos ajuste de `PetForm`/`QuickAddModal`: `npm --prefix frontend run build`, resultado passou.
- Contrato Plano Basico/configuracao da empresa apos protecao de endpoints e rotas: `12 passed`.
- Build frontend apos protecao do hub/subrotas de configuracao: `npm --prefix frontend run build`, resultado passou.
- Suite focada de lote/validade de produto e XML: `test_produtos_validade_listagem.py`, `test_estoque_routes_lotes.py`, `test_notas_entrada_parse_validade.py`, resultado `8 passed`.
- Build frontend apos refactor de Roles/LGPD: `npm --prefix frontend run build`, resultado passou.
- Py compile das migrations e arquivos backend alterados: passou.
- Migrations completas em Postgres limpo reexecutadas ate `oq20260515a8`.
- Dossie LGPD local: `GET /lgpd/clientes/{id}/dossie` retornou 200 depois das migrations `op20260515a7` e `oq20260515a8`.
- Observacao: o frontend nao possui script `lint`; scripts disponiveis no `package.json` sao `dev`, `build`, `build:dev` e `preview`.

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
| Produtos/racao | Calculadora interna de racao usa tenant selecionado no token e exige `produtos.visualizar` | Corrigido e testado |
| Produtos/racao | Catalogos de racao exigem permissao de produto por acao | Corrigido e testado |
| Produtos/catalogos | Categorias, marcas e departamentos exigem permissao de produto por acao | Corrigido e testado |
| Cadastros/pagamentos | Formas de pagamento, taxas, analise de venda e operadoras exigem permissao por leitura/alteracao e filtram tenant | Corrigido e testado |
| Configuracoes empresa | Dados/fiscal/geral/estoque exigem permissao de configuracao no backend e nas subrotas frontend | Corrigido local; falta smoke visual |
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

- Financeiro do cliente.
- Editar produto com todos os campos.
- Calculadora de racao na UI: API A/B e smoke visual concluidos.
- Catalogos auxiliares de produto: API A/B concluida; falta smoke visual.
- Formas de pagamento e operadoras: API A/B e smoke visual concluidos; falta CRUD completo no navegador.
- Configuracao da empresa: permissao/tenant corrigidos por contrato; falta smoke visual de salvar dados fiscal/geral/estoque no navegador.
- Landing page com selecao de planos e CTA do Plano Basico para contratacao: concluido local; falta smoke visual em staging/producao.
- PDV/vendas: API A/B concluida e smoke visual de operador/autocomplete/finalizacao passou; falta apenas reteste de recibo/historico visual.
- A/B visual no navegador entre dois tenants: em andamento.

### Deploy

- Nao houve deploy de producao nesta etapa.
- Branch atual enviada para GitHub no PR `#36`: `https://github.com/lcsgmoraes-droid/Sistema-Pet/pull/36`.

## Resumo Executivo

- Telas/fluxos basicos com algum teste registrado: 22/23
- Fluxos OK ou OK parcial: 20
- Corrigidos/registrados nesta trilha: frontend padronizado, onboarding local, tabelas auxiliares de racao/LGPD/e-commerce, unicidade de pet por tenant, contratacao por plano, schema de PDV/DRE, Roles & Permissoes e chamadas premium indevidas no Basico
- Pendencias P0: 0 confirmadas apos esta branch
- Pendencias P1: 3
- Pendencias P2: 5
- Minha recomendacao: liberar para revisao/merge em ambiente de teste/staging. Para producao/comercial controlada, seguir depois de retestar visualmente configuracao da empresa, lote/validade no navegador e cadastros auxiliares de produto restantes.

