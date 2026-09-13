---
name: dashboard
description: Use ao mexer na tela de dashboard financeiro (/dashboard), nos cartões/indicadores que ela mostra, no filtro de período do topo ou nos endpoints /dashboard/* que ela consome.
---

# Tela de Dashboard (financeiro)

Fonte de verdade simplificada sobre `/dashboard`. Complementa [[RefatoracaoV2]] (histórico da migração visual desta tela para `components/v2/`, inclusive os 4 componentes novos que nasceram dela) e a skill [[login]] (padrão irmão desta, primeira tela migrada).

## Identificação

- Menu: item "Dashboard" do layout autenticado principal (fora do escopo desta skill — ver o componente de layout/menu se precisar mexer nisso)
- Rota frontend: `/dashboard` (e `/dashboard-gerencial`, que só redireciona para `/dashboard`)
- Arquivo: `frontend/src/pages/v2/DashboardFinanceiro.jsx`
- Módulo de rota: `frontend/src/app/routes/CoreProtectedRoutes.jsx`
- Import lazy: `frontend/src/app/lazyPages.jsx` (`preloadDashboardFinanceiro`)

## Objetivo

Dar ao gestor/admin uma visão consolidada do negócio ao abrir o sistema: faturamento, resultado de caixa, contas vencidas, e sinais de atenção sobre clientes — tudo navegável, cada número leva à tela de detalhe correspondente.

## Usuários

Qualquer usuário com a permissão `relatorios.gerencial` (ver Segurança). Não é a tela padrão de todo perfil — `caixa`, por exemplo, cai em `/pdv` ao logar (ver skill [[login]], `getDefaultAuthenticatedRoute`).

## Fluxo

```text
Tela monta → dispara 6 chamadas em paralelo (Promise.allSettled, uma pode falhar sem travar as outras)
  → GET /dashboard/resumo
  → GET /dashboard/entradas-saidas
  → GET /dashboard/contas-vencidas
  → GET /dashboard/gerencial
  → GET /dashboard/top-produtos
  → GET /contas-bancarias/resumo/saldos
→ falhas viram um aviso amarelo no topo ("Parte do painel não pôde ser atualizada") sem esconder o resto
→ usuário troca o período (SeletorOpcoes) → refaz as 6 chamadas com o novo periodo_dias
→ usuário clica "Atualizar" → refaz as 6 chamadas sem mudar o período (loading vira "refreshing", não tela cheia)
→ clique em qualquer CartaoIndicador ou botão de navegação → navigate() para a tela de detalhe (getDashboardDetailPath)
```

## Frontend

- Página: `frontend/src/pages/v2/DashboardFinanceiro.jsx`
- Lógica de cálculo/rótulos (sem JSX): `frontend/src/pages/dashboard/dashboardOverview.js` — `calculateDashboardIndicators`, `getExecutiveStatus`, `getPeriodLabel`, `getDashboardDetailPath`, `getDashboardPeriodFromSearch` (este último também usado por outras telas financeiras, não mexer sem checar `RecebimentosVendas.jsx`/`VendasFinanceiro.jsx`)
- Componentes v2 usados (4 nasceram desta tela): `SeletorOpcoes` (filtro de período), `CartaoIndicador` (as 13 métricas/indicadores clicáveis), `EstadoVazio` (gráfico/lista sem dado no período), `BotaoLink` ("Ver produtos"), `BotaoInteracao` ("Entender painel"/"Analisar com IA"/"Atualizar")
- `CartaoIndicador.tom` usa o mesmo vocabulário de `BotaoBase.variante` (`neutro`/`sucesso`/`perigo`/`informativo`/`atencao`) — ver `Documentacao/RefatoracaoV2.md` para o mapeamento de cada um dos 13 cartões
- Gráfico "Entradas e saídas": Recharts `AreaChart` — cor do grid/eixos calculada em JS via `useTheme()` (`isDark`) porque Recharts não lê classes Tailwind `dark:`
- 2 botões nativos continuam exclusivos da tela (não viraram componente v2): linhas de "Base de clientes" e cabeçalhos "A receber"/"A pagar" — ver razão em [[RefatoracaoV2]]
- IDs `tour-stats`/`tour-financeiro`/`tour-composicao`/`tour-acoes-rapidas` nas `<section>` são âncoras do tour guiado (`frontend/src/tours/tourDefinitions.js`, `tourDashboard`) — **não remover nem renomear** sem atualizar o tour junto

## Backend

Todos em `backend/app/dashboard_routes.py` (`APIRouter()`, sem prefixo próprio — cada rota já inclui `/dashboard` no path):

- `GET /dashboard/resumo` — `backend/app/dashboard_routes.py:115`. Recebe `periodo_dias`. Faturamento, lucro, saldo, contas a receber/pagar do período.
- `GET /dashboard/entradas-saidas` — `backend/app/dashboard_routes.py:351`. Recebe `periodo_dias`. Série diária para o gráfico.
- `GET /dashboard/contas-vencidas` — `backend/app/dashboard_routes.py:508`. Recebe `limite`. Lista as contas a receber/pagar vencidas mais antigas.
- `GET /dashboard/gerencial` — `backend/app/dashboard_routes.py:653`. Sem parâmetros. Métricas de clientes (VIPs em risco, inativos, novos promissores, sem WhatsApp).
- `GET /dashboard/top-produtos` — `backend/app/dashboard_routes.py:798`. Recebe `periodo_dias`, `limite`. Ranking de produtos por quantidade vendida.
- `GET /contas-bancarias/resumo/saldos` — `backend/app/contas_bancarias_routes.py:541`. Sem parâmetros desta tela. Saldo consolidado de todas as contas bancárias; se falhar, a tela cai para `summary.saldo_atual` (saldo estimado, não o saldo bancário real) e o cartão troca o rótulo para "Saldo estimado".

## Banco de dados

Ver [[Dominio]] para as entidades por trás de cada indicador (vendas, contas a pagar/receber, contas bancárias, clientes). Esta tela é só leitura — nenhuma das 6 chamadas grava dado.

## APIs

| Endpoint | Quando é chamado | Parâmetros | Efeito no frontend se falhar |
|---|---|---|---|
| `GET /dashboard/resumo` | Ao montar e a cada troca de período/atualizar | `periodo_dias` | Cartões de "Resultado do período"/"Posição financeira" ficam com os valores anteriores (ou zerados, na primeira carga) |
| `GET /dashboard/entradas-saidas` | Idem | `periodo_dias` | Gráfico mostra `EstadoVazio` |
| `GET /dashboard/contas-vencidas` | Idem | `limite=5` | Bloco "Contas vencidas mais antigas" mostra o estado "Nenhuma conta vencida" mesmo que existam |
| `GET /dashboard/gerencial` | Idem | — | Cartões de VIPs/inativos e bloco "Base de clientes" zerados |
| `GET /dashboard/top-produtos` | Idem | `periodo_dias`, `limite=5` | Lista de produtos mostra `EstadoVazio` |
| `GET /contas-bancarias/resumo/saldos` | Idem | — | Cartão de saldo cai para "Saldo estimado" (usa `summary.saldo_atual`) |

Todas as 6 usam `Promise.allSettled` — uma falha isolada não derruba as outras nem trava a tela; aparece listada no aviso amarelo "Parte do painel não pôde ser atualizada (chave1, chave2...)".

## Segurança

- Rota protegida por `ProtectedRoute permission="relatorios.gerencial"` (`frontend/src/app/routes/CoreProtectedRoutes.jsx:23`) — usuário sem essa permissão não acessa `/dashboard`.
- Todos os 6 endpoints são multi-tenant (dependem do tenant do token da sessão) — não recebem `tenant_id` explícito no payload, ele vem do contexto de autenticação.

## O que esta tela NÃO faz

- Não grava nem edita nada — é 100% leitura/navegação.
- Não decide sozinha o período padrão além do valor inicial fixo (30 dias) — não lê `periodo_dias` da URL como `RecebimentosVendas`/`VendasFinanceiro` fazem via `getDashboardPeriodFromSearch`.
- Não trata erro por endpoint individualmente na UI além do aviso agregado — não há retry automático nem mensagem específica por métrica que falhou.
- Não atualiza sozinha em background — só recarrega quando o usuário troca o período ou clica "Atualizar" (sem polling).

## Dependências

- [[RefatoracaoV2]] — detalhe completo da limpeza de CSS desta tela (por que cada botão nativo virou o que virou).
- `frontend/src/tours/tourDefinitions.js` (`tourDashboard`) — tour guiado ativado pelo botão "Entender painel"; depende dos IDs `tour-*` das `<section>`.
- `frontend/src/pages/dashboard/dashboardOverview.js` — `getDashboardPeriodFromSearch` também é usado por `RecebimentosVendas.jsx`, `VendasFinanceiro.jsx` e `FluxoCaixa.jsx` (telas vizinhas de detalhe, não migradas nesta leva).
- Skill [[login]] — telas irmãs na mesma frente de migração visual.

## Observações (comportamento não óbvio)

- O cartão "Saldo em bancos" muda de rótulo para "Saldo estimado" quando `/contas-bancarias/resumo/saldos` falha — é a pista de que o valor mostrado não é o saldo bancário real, é um fallback calculado (`summary.saldo_atual`).
- `visao_comercial === "recebimento"` (campo vindo do backend em `/dashboard/resumo`) troca o rótulo e o texto de apoio de "Faturamento" para "Recebimentos de vendas" — é uma configuração de exibição por tenant, não uma escolha feita nesta tela.
- Os 13 `CartaoIndicador` usam tons dinâmicos em boa parte dos casos (ex.: "Lucro das vendas" é `sucesso` se ≥ 0, `perigo` se negativo; os 5 cartões de "Atenção agora" são `atencao` se houver pendência, `sucesso` se não houver) — o tom não é fixo por cartão, é calculado a cada carga.

## Pontos de atenção

- Ver [[RefatoracaoV2]] para o mapeamento completo dos 13 cartões (ícone, tom, o que cada um mostra) e o raciocínio de cada decisão de limpeza.
- Não testado visualmente num navegador autenticado nesta rodada — exige login multiempresa contra o backend e não há credenciais de desenvolvimento documentadas neste ambiente. Validado por build de produção, ESLint, Prettier e revisão `rams`, sem achados reais pendentes.
