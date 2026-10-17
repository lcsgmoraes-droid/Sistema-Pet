---
name: lembretes
description: Use ao mexer na Central de Lembretes (/lembretes) — recompras, aniversários, relacionamento/clientes inativos, controle de validade, auto cadastro Bling e relatórios de contato — ou nos endpoints /lembretes/*, /estoque/validade/* e /clientes/inativos que ela consome.
---

# Central de Lembretes

Fonte de verdade simplificada sobre `/lembretes`. Refatorada para componentes v2 em 2026-10-17 (branch `documentacao`).

## Identificação

- Menu: "Lembretes" (badge = recompras pendentes + auto cadastros Bling de 24h; poll de 5 min em `Layout.jsx`)
- Rota: `/lembretes` — `frontend/src/app/routes/ProductInventoryRoutes.jsx` (sem `ProtectedRoute`; item de menu com `permission: null`)
- Página: `frontend/src/pages/lembretes/LembretesPage.jsx` (fachada `pages/Lembretes.jsx`)
- Rota inicial de qualquer perfil que não seja caixa/admin/gerente (`auth/userRole.js`).

## Objetivo

Reunir num só lugar as oportunidades de contato com cliente (recompra, aniversário, cliente inativo), as pendências de validade de estoque e o resumo dos contatos feitos.

## Abas (ordem: consulta à esquerda, alteração de dados à direita)

| Aba | O que faz | Altera dados? |
|---|---|---|
| Relatórios | Resumo de 30 dias: contatos, oportunidades contatadas, recompras após contato, histórico | Não |
| Auto cadastro Bling | Produtos criados sozinhos na baixa de NF do Bling nas últimas 24h (só com módulo `bling` ativo) | Não |
| Relacionamento | Alertas de campanhas (módulo `campanhas`) + clientes inativos 30/60/90+ dias; WhatsApp/copiar manual | Não (WhatsApp daqui não grava histórico) |
| Aniversários | Tutores e pets (30 dias): mensagem, WhatsApp, push | Sim (registra contato) |
| Recompras | Fila de lembretes: filtros de prazo/tipo, mensagem, push, registrar recompra, próximo ciclo, cancelar | Sim |
| Validade | Lotes retirados do estoque vendável: descartar, trocar, retornar | Sim (estoque/financeiro) |

Cada aba tem contador (`AbasNavegacao.contador`). Aba padrão: Recompras.

## Frontend

- Controller único: `useLembretesController.js` (carrega tudo; refresh a cada 60 s; abre contato, push, WhatsApp, validade).
- Componentes: `LembretesTabs` (+ `montarAbas`), `LembretesHeader` (cartões), `LembretesList`/`LembreteCard`, `LembreteContatoModal` (`ModalPadrao` grande), `LembretesAniversariantes`, `LembretesCampanhasAlertas`, `LembretesClientesInativos` (`DataTable` + `PaginationControls`, coluna Ações primeiro), `LembretesValidadeSection`, `LembretesBlingAutocadastros`, `LembretesRelatorios`.
- Utilitários: `lembretesUtils.js` (prazos, filtro, `whatsappUrl`), `lembretesFormatters.js`.
- Novos componentes v2 criados aqui: `FaixaAviso`, `Etiqueta` (ver `/style-guide`).
- Cartão de recompra: "Criar mensagem" sempre visível; Push, Registrar recompra, Criar próximo ciclo e Cancelar lembrete no `BotaoMenuAcoes` (motivo de push indisponível vira `title` do item).
- Testes (fonte-grep, node:test): `lembretes/*.test.mjs`, `pages/lembretesValidadeFlow.test.mjs`, `scripts/test-lembretes-refactor.mjs`.

## Backend

- `backend/app/lembretes.py` (`/lembretes/criar|pendentes|para-notificar|{id}/notificar|completar|renovar|DELETE {id}|simular-data`)
- `lembretes_relacionamento_routes.py` (contatos por lembrete, WhatsApp com checagem de consentimento, `/relatorios/resumo`)
- `lembretes_aniversarios_routes.py` (`/lembretes/aniversarios`, contatos, WhatsApp, `notificar-app`)
- `estoque_validade_routes.py` (`/estoque/validade/processar|pendencias|{id}/descartar|trocar-fornecedor|retornar-vendavel`)
- `clientes/inativos_routes.py` (`GET /clientes/inativos`, exige `clientes.visualizar`)
- `integracao_bling_nf_routes.py` (`GET /integracoes/bling/nf/autocadastros-recentes`)
- `GET /campanhas/dashboard`, `GET /empresa/config-estoque`.

## Banco de dados

`Lembrete`, `LembreteContato`, `AniversarioContato` (BaseTenantModel + RLS). Aniversários são calculados na hora (Cliente/Pet). Validade: `EstoqueValidadeBloqueio`; config `protecao_validade_ativa` e `dias_alerta_validade`.

## Como os lembretes nascem

Finalização de venda (`product_recurrence.py`) e job de 15 min (push via `NotificationQueue`). Nada é enviado ao cliente sem ação humana, exceto push de recorrência pelo job. WhatsApp é só `wa.me` (a conversa abre; o envio é do operador).

## Segurança (estado atual)

- Rotas de lembretes **sem** `require_permission`; só autenticação + isolamento por tenant.
- Validade: `processar`, descartar, trocar, retornar exigem `produtos.editar`; `pendencias` só autenticação.
- Permissões **não** chegam a perfis existentes automaticamente (ver "Diretriz de permissões").

## O que a tela NÃO faz

- Não cria lembrete manual (sem "novo lembrete").
- Não envia WhatsApp sozinha nem registra contato do aba Relacionamento.
- Não aplica gating por módulo/entitlement em `/lembretes`.

## Observações / pontos de atenção

- Ao abrir a tela, `carregarValidadePendencias({processar:true})` **retira lotes do estoque vendável** (não há job agendado). Pode rodar duas vezes em dev (StrictMode) e dá 403 silencioso sem `produtos.editar`.
- Badge do menu soma auto cadastros Bling, agora visíveis na aba própria.
- "Renovar" perde o tipo/dose do lembrete original (ver backlog).
- `PaginationControls` (ui) ainda usa `<select>`/botões nativos internamente; fora do escopo.
- Datas: mistura de `utcnow`, `date.today`, naive e `now_brasilia` — ver diretriz de datas.

## Diretrizes do Lucas (2026-10-17)

1. **Permissões por aba**: abas só informativas ficam sem validação. Abas que alteram dados (Aniversários, Recompras, Validade) precisam de **política de controle**: permissão própria que pode ou não ser associada a um perfil/usuário. Aba só aparece/age com a permissão.
2. **Ordem das abas**: sem interação primeiro, com mudança no sistema à direita (já aplicado).
3. **Bling 24h**: exibido numa aba própria condicional (aplicado).
4. **Datas**: o correto é armazenar tudo em UTC e exibir no fuso local de quem vê. Trabalho extenso → **atividade separada** (ordem de grandeza: centenas de ocorrências de `utcnow`/`date.today`/naive).
5. Tudo que mudar comportamento só entra após decisão.

### Diretriz de permissões (levantamento RBAC)

- Catálogo: `PERMISSION_CATALOG` na migration `zxd20260826a1` (formato `modulo.acao`); teste `tests/test_permission_catalog_migration_contract.py` lê só essa migration e precisa ser ajustado para ler migration nova.
- Permissão nova **não** entra em nenhum perfil sozinha (nem Administrador existente). Frontend libera admin por nome do perfil; backend não → 403 se faltar backfill. Receita: migration nova com `INSERT ... ON CONFLICT` + backfill idempotente em `role_permissions` para quem hoje acessa (RLS por tenant), `@require_permission` nas rotas, `ProtectedRoute`/`menuConfig`/gating das abas, `CATEGORY_LABELS` em `useRolesPage.js`, perfis padrão em `default_roles_service.py`, cuidado com `/lembretes` ser rota inicial.

## Segunda rodada de ajustes (BACKLOG — a decidir com o Lucas)

- Política de permissões por aba (acima) — nomes, backfill por perfil, rota inicial.
- Processamento de validade fora da tela (job agendado como o de 15 min) mantendo "Verificar agora"; hoje abrir a tela muta estoque.
- Clientes inativos: WhatsApp ignora consentimento e histórico (diferente de recompra/aniversário); decidir entre só checar consentimento ou registrar contato.
- Renovar lembrete perde tipo/dose; revisar regras de renovação/ciclo aprendido.
- Atividade separada: padronização de datas (UTC no banco, fuso local na exibição).
- Generalizar a política de permissão por tela (outras telas com ações que alteram dados).
- `/lembretes` sem gating de módulo/entitlement.
- Revisar `PaginationControls`/componentes `ui/` legados para v2.
- Ícone de "Ver cliente" (usado `Eye`) — padronizar com as demais telas.
