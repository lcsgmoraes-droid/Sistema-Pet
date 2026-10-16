---
name: pessoas
description: Use ao mexer na listagem de Pessoas (/clientes), no cadastro rápido (modal "Nova pessoa") ou na tela de edição em abas (/clientes/:clienteId/editar) — inclui endereços, alertas do PDV e os 4 tipos de cadastro (cliente/fornecedor/veterinário/funcionário). Gestão de acesso ao sistema (login/perfis) fica na tela Usuários, não aqui.
---

# Pessoas (Cliente/Fornecedor/Veterinário/Funcionário)

Fonte de verdade simplificada sobre a família de telas de "Pessoa" — um único cadastro (`Cliente` no banco) reaproveitado para clientes, fornecedores, veterinários e funcionários. Complementa [[Cliente]] (modelo de dados, isolamento por tenant, campo a campo) — esta skill foca em **tela, regras de negócio e histórico da evolução**, não repete o que já está em [[Cliente]].

## Identificação

- Menu: item "Clientes"/"Pessoas" do layout autenticado principal
- Rotas frontend:
  - `/clientes` — listagem (`frontend/src/pages/ClientesNovo.jsx`, exportado como `Pessoas` em `lazyPages.jsx`)
  - `/clientes/:clienteId/editar` — edição em abas (`frontend/src/pages/ClientePessoaEditar.jsx`)
  - `/clientes/:clienteId/financeiro`, `/clientes/:clienteId/timeline` — telas satélite, fora do escopo desta skill
- Módulo de rota: `frontend/src/app/routes/CoreProtectedRoutes.jsx`
- ⚠️ `frontend/src/pages/Pessoas.jsx` existe no repositório mas **não está roteado em lugar nenhum** (confirmado por busca — nenhum import ativo). Não confundir com a listagem real (`ClientesNovo.jsx`); não editar esse arquivo morto pensando que é a tela em uso.

## Objetivo

Dar ao Lucas (ou a qualquer usuário com `clientes.visualizar`) um cadastro único para qualquer pessoa que a loja precise registrar — quem compra, quem vende, quem atende como veterinário, quem trabalha na loja — sem duplicar a entidade por papel.

## Usuários

Qualquer usuário com permissão `clientes.visualizar`. Desde 2026-09-23, gerenciar **acesso ao sistema** (login/senha/perfil administrativo e perfis de app) não acontece mais aqui — é tudo na tela Usuários (`/admin/usuarios`, fora do escopo desta skill) — ver seção "Evolução" abaixo.

## Fluxo

```text
Listagem (/clientes)
  → abas Todos/Clientes/Fornecedores/Veterinários/Funcionários (ClientesNovoTabsBar.jsx)
     → cada aba manda is_cliente=true / is_fornecedor=true / ... para GET /clientes/
     → uma pessoa com vários tipos marcados aparece em mais de uma aba
  → "Nova pessoa" → ClientePessoaCriarModal.jsx (cadastro mínimo: tipos, nome/razão social, CPF/CNPJ, celular)
     → POST /clientes/ → abre ClientePessoaEditar.jsx da pessoa recém-criada
  → clicar numa pessoa → ClientePessoaEditar.jsx

Edição (/clientes/:clienteId/editar) — 5 abas, sempre visíveis:
  → "Dados gerais": tipos de cadastro, identificação, complementares (entregador/parceiro)
  → "Contatos": telefone/e-mail/observações
  → "Endereço": principal + adicionais
  → "Alertas do PDV": mensagens automáticas
  → "Financeiro": crédito, timeline de compras, WhatsApp
  → botão "Gerenciar pets" (ao lado de Salvar, não é aba) abre /pets?cliente_id=X em nova aba
  → Salvar → PUT /clientes/:id
```

## Frontend

- Listagem: `frontend/src/pages/ClientesNovo.jsx` + `ClientesNovoTabsBar.jsx` (abas) + `ClientesNovoTabelaSection.jsx` (tabela/cards) + hook `frontend/src/hooks/useClientesNovoListagem.js` (monta os query params, inclusive `is_cliente`/`is_fornecedor`/`is_veterinario`/`is_funcionario`)
- Criação rápida: `frontend/src/components/clientes/ClientePessoaCriarModal.jsx`
- Edição, um arquivo por aba:
  - `ClientePessoaEditar.jsx` — página, monta `formData`, define as 5 abas (`abas` useMemo), valida, orquestra `salvar()`
  - Aba "Dados gerais": `ClientePessoaDadosGeraisTab.jsx` (tipos de cadastro via `InputCheckGroup`, tipo de pessoa PF/PJ, nome/CPF/data nascimento ou razão social/CNPJ, CRMV só `is_veterinario`, origem do cliente só `is_cliente`) + `ClientePessoaComplementaresTab.jsx` (entregador, só se `is_funcionario`/`is_fornecedor`, e parceiro/comissões, qualquer tipo) — as duas juntas na mesma aba, com um divisor
  - Aba "Contatos": `ClientePessoaContatosTab.jsx` — celular/telefone/e-mail + Observações (2 colunas: contatos à esquerda, observações ocupando o resto)
  - Aba "Endereço": `ClientePessoaEnderecoTab.jsx` + `ClientePessoaEnderecoModal.jsx` — principal + adicionais, badge colorida por tipo (entrega/cobrança/comercial/residencial/trabalho)
  - Aba "Alertas do PDV": `ClientePessoaAlertasPdvSection.jsx` + `ClientePessoaAlertaPdvModal.jsx` — mesmo padrão de lista+modal do endereço
  - Aba "Financeiro": `ClientePessoaFinanceiroTab.jsx` — sempre visível (não depende mais de `is_cliente`)
  - Botão "Gerenciar pets" (não é aba): ao lado do Salvar, abre `/pets?cliente_id=X` em nova aba do navegador — `ClientePessoaAnimaisTab.jsx` foi removido
- Componentes v2 que nasceram deste trabalho: `AbasNavegacao`, `ModalPadrao` (modal padrão com título/rodapé/fechar — clicar fora nunca fecha), `InputCheckGroup` (grupo de pills seleção múltipla, usado nos 4 tipos de cadastro), `InputTelefone` (celular/fixo unificado, com toggle de WhatsApp embutido)
- Todo botão de ação vem de `components/v2/` (`BotaoInteracao`, `BotaoExcluir`, `BotaoSalva`, `BotaoCancelar`) — nunca `ui/ActionButton` nem HTML cru. Ver catálogo em `frontend/src/pages/styleGuide/styleGuideCatalog.js` / tela `/style-guide`.

## Backend

- Rotas: `backend/app/clientes/crud_routes.py` (`create_cliente`, `update_cliente`, `list_clientes`/`_montar_query_listagem_clientes`)
- Helpers compartilhados: `backend/app/clientes/common.py` — `_validar_telefone_cliente_obrigatorio` (celular só obrigatório se `is_cliente`), `_validar_e_normalizar_flags_tipo_criacao`/`_validar_e_normalizar_flags_tipo_update` (exigem pelo menos 1 flag `true`; recalculam `tipo_cadastro` legado numa ordem fixa sem significado de negócio)
- Schemas: `backend/app/clientes/schemas.py` — `ClienteCreate`/`ClienteUpdate`/`ClienteResponse`
- Modelo: `backend/app/models_cadastros.py` (`Cliente`) — ver [[Cliente]] para o campo a campo completo

## Banco de dados

Ver [[Cliente]] (modelo `Cliente`, tabela `clientes`, isolamento por tenant). Resumo do que esta skill acrescenta: desde 2026-09-22, `is_cliente`/`is_fornecedor`/`is_veterinario`/`is_funcionario` (booleanas independentes) são a fonte de verdade sobre o(s) tipo(s) da pessoa — `tipo_cadastro` (string única, antiga) ficou obsoleto, ver seção "Evolução" abaixo.

## APIs

| Endpoint | Quando é chamado | Parâmetros relevantes |
|---|---|---|
| `GET /clientes/` | Listagem, cada troca de aba/busca/página | `is_cliente`/`is_fornecedor`/`is_veterinario`/`is_funcionario` (bool), `is_entregador`, `search`, `resumo_por_origem` (só quando `is_cliente=true`) |
| `POST /clientes/` | Modal "Nova pessoa" | `is_cliente`/`is_fornecedor`/`is_veterinario`/`is_funcionario` — pelo menos 1 `true`, senão 400 |
| `PUT /clientes/:id` | Salvar na tela de edição | Idem; desmarcar o único tipo marcado sem marcar outro também dá 400 |
| `GET /clientes/origens` | Combobox de origem em Dados gerais | — |

## Segurança

- Todas as rotas exigem `clientes.visualizar` (`@require_permission`).
- Isolamento por tenant herdado de `BaseTenantModel` — ver [[Cliente]] para o detalhe (RLS, sem cliente compartilhado entre lojas do mesmo grupo).
- `auth_user_id`/`app_login`/`app_access_profiles` continuam existindo em `ClienteCreate`/`ClienteUpdate` (backend não foi alterado, só a UI de Pessoa parou de expor esses campos — ver "Evolução") — quem ainda chamar a API diretamente com esses campos precisa de `usuarios.manage`.

## O que esta família de telas NÃO faz

- Não migra os ~30 consumidores backend/frontend que ainda leem `tipo_cadastro` para decisão de negócio (folha de pagamento, acerto financeiro de entregador, agenda veterinária, e-commerce/app, comissões, dashboard/relatórios, seletores de fornecedor em Compras/Financeiro/Produtos, LGPD) — ver "Backlog Fase 2" abaixo. Esses continuam funcionando exatamente como antes, sem quebrar, só não refletem múltiplos tipos ainda.
- Endereço principal não pode ser "excluído de verdade" — o botão Excluir nele só limpa os campos (mesmo componente/confirmação dos endereços adicionais, que esses sim somem da lista).
- Não funde cadastros automaticamente por CPF/CNPJ repetido — isso é um fluxo separado (`PessoasFusaoModal.jsx`/`pessoa_merge_service.py`, fora do escopo desta skill).

## Dependências

- [[Cliente]] — modelo de dados completo, campo a campo, isolamento por tenant.
- `.claude/skills/login/SKILL.md`, `.claude/skills/dashboard/SKILL.md` — mesmo template desta skill.
- `frontend/src/pages/styleGuide/styleGuideCatalog.js` — catálogo de componentes v2 (consultar antes de criar campo/botão novo).

## Observações (comportamento não óbvio)

- `tipo_cadastro` continua sendo gravado no banco (coluna `NOT NULL` legada) mesmo depois da mudança de 2026-09-22 — o backend escolhe automaticamente a primeira flag `true` numa ordem fixa (`cliente` → `fornecedor` → `veterinario` → `funcionario`) só para preencher a coluna. Essa ordem **não tem significado de prioridade de negócio** — é só compatibilidade técnica. Não usar `tipo_cadastro` para decidir nada novo.
- As 5 abas (Dados gerais/Contatos/Endereço/Alertas do PDV/Financeiro) sempre aparecem, para qualquer tipo de pessoa — não há mais regra de esconder aba por tipo (nem por `is_cliente`, nem "só para veterinário"). A barra de abas em si (`AbasNavegacao`) também nunca fica escondida, mesmo com 1 aba só — já foi um bug real (tela parecia "quebrada" pra pessoas só-funcionário).
- O bloco "Entregador" em Complementares aparece se `is_funcionario` OU `is_fornecedor` — uma pessoa com os dois marcados ao mesmo tempo vê os dois sub-blocos (RH + taxa fixa/km) simultaneamente; é união, não exclusão.
- `InputCheckGroup` (novo componente v2) é visualmente idêntico ao `InputRadio`, mas seleção múltipla — usado hoje só para os 4 tipos de cadastro; cotovelo natural para qualquer outro "marque um ou mais" pill-style que aparecer.
- Gerenciar acesso (login e perfis de app) de uma Pessoa que **já existe**: não tem UI direta na tela de Pessoa nem em Usuários hoje — a tela Usuários só cria/vincula acesso a partir do formulário de criação (busca por celular/e-mail) ou edita perfis de quem **já tem** login (`UsuarioCredenciaisModal.jsx`). Não há um fluxo de "abrir a Pessoa X e criar/vincular login pra ela" — isso só acontece pelo lado Usuários agora.

## Pontos de atenção

### Evolução do processo (mais recente primeiro)

- **2026-09-23 — 3 abas → 5 abas: Contatos, Endereço e Alertas do PDV voltaram a ser abas separadas.** Motivo: pedido explícito do Lucas ("me foi solicitado que as informações voltassem a ficar separadas em abas") — a consolidação em "Dados gerais" (ver item "6 abas → 3 abas" abaixo) tinha ido longe demais na prática. "Dados gerais" ficou só com identificação + Complementares; Animais **não** voltou a ser aba (continua o botão "Gerenciar pets" ao lado do Salvar). Mudança só de organização visual em `ClientePessoaEditar.jsx` (`abas` useMemo + blocos de render) — nenhum componente de aba mudou por dentro.
- **2026-09-23 — Gestão de acesso ao sistema saiu de Pessoa, centralizada em Usuários.** Motivo: o Lucas percebeu que a tela Usuários (`/admin/usuarios`, Administração) já existia e duplicava, dentro de Pessoa, a mesma responsabilidade — criar/vincular login administrativo e marcar perfis de app. Correção importante do Lucas durante o planejamento: **não é sobre funcionário, é sobre acesso** — nem todo funcionário tem login no sistema, então os campos de RH (cargo/salário/férias/décimo terceiro, telas `/rh/funcionarios` e `/cadastros/cargos`) **não mudaram**, só a parte de login/perfis de app. `ClientePessoaAcessoAppCard.jsx` foi apagado; `ClientePessoaComplementaresTab.jsx` e `ClientePessoaEditar.jsx` perderam os states/efeito que buscavam contas/perfis. Do lado Usuários: criar um usuário agora busca uma Pessoa existente por celular/e-mail (`GET /clientes/verificar-duplicata/campo`, que ganhou um branch de `email`) e oferece vincular em vez de duplicar; sem achar nada, cria uma Pessoa nova com `is_funcionario=true` (`_vincular_ou_criar_pessoa_para_usuario` em `usuarios_routes.py`). Perfis de app editáveis também na tela Usuários (`GET`/`PUT /usuarios/{id}/perfis-app`, lista compartilhada em `frontend/src/utils/appAccessProfiles.js`). Script de reconciliação de dado (não Alembic) em `backend/scripts/backfill_dados_usuario_de_pessoa.py`, dry-run por padrão — copia nome/celular/e-mail de Pessoas já vinculadas (antes desta mudança) para o `User` correspondente, só preenchendo lacunas, e marca `is_funcionario=true` pra quem já tinha login.
- **2026-09-22 — `tipo_cadastro` único → 4 flags independentes.** Motivo: o Lucas precisava que uma pessoa acumulasse vários papéis ao mesmo tempo (ex.: cliente que também é funcionário), pensando em uso futuro para filtragem/campanhas. Migrations `zzzf20260922a1` (adiciona colunas) + `zzzg20260922a1` (backfill: baseline a partir do `tipo_cadastro` antigo + histórico real de uso — quem já apareceu em `vendas.cliente_id`/`funcionario_id`, `notas_entrada`/`pedidos_compra.fornecedor_id`, ou nas 6 tabelas `vet_*.veterinario_id` ganhou a flag correspondente, mesmo que o cadastro nunca tivesse sido daquele tipo). Decisão explícita do Lucas: `tipo_cadastro` fica obsoleto de verdade, sem derivação "inteligente" — só a Fase 1 (banco + esta tela) foi migrada; o resto é backlog documentado abaixo.
- **Antes — wizard de múltiplas etapas → cadastro mínimo + edição em abas.** Fluxo antigo tinha 4 passos no cadastro e 6 passos na edição (`ClientesNovoCadastroStep.jsx`/`useClientesNovoCadastro.js`, removidos). Virou modal de cadastro mínimo (`ClientePessoaCriarModal.jsx`) + edição em abas.
- **Depois — 6 abas → 3 abas.** Dados gerais/Contatos/Endereço/Complementares viraram uma única aba "Dados gerais" com seções internas; Animais e Financeiro continuaram separadas.
- **Endereço**: principal + adicionais unificados numa lista só (`ClientePessoaEnderecoTab.jsx`), com badge colorida por tipo e modal padrão para editar.
- **Alertas do PDV**: saiu de formulário sempre-aberto dentro de Complementares para o mesmo padrão lista+modal do endereço (`ClientePessoaAlertasPdvSection.jsx`).
- **`ModalPadrao`**: componente v2 novo (título + rodapé de botões + fechar padronizado, clicar fora nunca fecha) — adotado primeiro no modal de endereço, é o modelo para próximas modais da tela.
- **Telefone**: celular e fixo unificados em `InputTelefone` (`tipo="celular"|"fixo"`), com toggle de WhatsApp embutido só no celular.

### Backlog Fase 2 — consumidores de `tipo_cadastro` ainda não migrados

Continuam lendo o campo antigo (funcionam normalmente, só não enxergam múltiplos tipos):

- **Folha de pagamento/benefícios**: `decimo_terceiro_service.py`, `ferias_service.py`, `provisao_beneficios_service.py`, `provisao_trabalhista_service.py`, `cargos_routes.py`.
- **Acerto financeiro de entregador**: `acerto_entrega_service.py`.
- **Agenda/prontuário veterinário**: `veterinario_calendar.py`, `veterinario_agendamentos.py`, `veterinario_acompanhamento_routes.py`, `veterinario_agenda_routes_parts/cadastros_routes.py`.
- **E-commerce/app**: `ecommerce_auth_cliente.py`, `ecommerce_auth_profiles.py`, `app_access_profile_service.py`.
- **Comissões**: `comissoes_avancadas/conferencia_routes.py`, `comissoes_parceiros_routes.py`.
- **Dashboard/relatórios**: `dashboard_routes.py` (KPIs `visao_dashboard`), `clientes/relatorio_routes.py`, `pessoa_merge_service.py`, `pessoa_duplicate_service.py`.
- **Seletores de fornecedor/cliente (frontend)**: `ContasPagar.jsx`, `ModalNovaContaReceber.jsx`, `modalNovaContaPagar/useModalNovaContaPagarController.js`, `compras/pedidosCompraDataController.js`, `fornecedores/FornecedorSelector.jsx`, `useProdutosNovoCarregamento.js`, `useProdutosCatalogos.js`, `useProdutosBalancoPage.js`, `pdv/ModalCadastroCliente.jsx`.
- **Auto-cadastro por outros fluxos**: `notas_entrada/fornecedores.py`, `estoque/transferencia_grupo_service.py`, `importacao_pessoas.py`. (`usuarios_routes.py` **saiu** desta lista em 2026-09-23 — `criar_usuario` agora grava `is_funcionario=true` na Pessoa nova/vinculada, ver "Evolução" acima; `tipo_cadastro="funcionario"` continua sendo gravado também, só por compatibilidade.)
- **LGPD**: `services/lgpd_serializers.py`.

Antes de migrar qualquer um destes, reler esta seção — a lista existe justamente para não precisar buscar no código inteiro de novo.
