# Instruções para o Claude Code — Sistema Pet

> **Regras gerais de trabalho, fluxo Git e produção protegida: siga `@AGENTS.md`** (fonte única — vale igual para Codex e Claude). Tudo abaixo **complementa** aquelas regras; em caso de conflito, AGENTS.md prevalece.

## Priorize as ferramentas do projeto (skills e MCPs)

Antes de executar uma tarefa, **verifique se já existe uma skill / slash command ou uma ferramenta MCP que a cobre, e use-a** em vez de comandos ad-hoc (curl, build manual, `docker` na mão, scripts soltos). Esses MCPs têm travas de segurança e gravam auditoria local — usá-los é mais seguro e rastreável do que fazer na mão.

### Mapa tarefa → ferramenta (quando configuradas nesta máquina)

| Tarefa | Use primeiro |
|---|---|
| Validar frontend (status, build DEV, HTTP, auth) | `/front-check` · `mcp__sistema-pet-frontend__*` |
| Subir e validar ambiente DEV | `/fluxo-dev` (`fluxo_dev_up` → `fluxo_status` → `api_health_check`) |
| Diagnóstico **read-only** geral (API + fluxo + front) | `/health` |
| Estado de campanhas + correlação com logs | `/campaigns` |
| Checagem pré-release (sem subir prod) | `/release-check` (`fluxo_check` + `fluxo_release_check`) |
| Resumo de auditoria dos MCPs | `/audit` (`mcp_audit_report`) |
| Saúde da API / rota de auth | `mcp__sistema-pet-ops__api_health_check` · `api_auth_route_smoke` |
| Status do fluxo único | `mcp__sistema-pet-ops__fluxo_status` |
| Logs do backend | `mcp__sistema-pet-ops__backend_logs` |
| Permissões de abas/auth | `mcp__sistema-pet-ops__auth_validate_tabs_permissions` |

### Regras de uso das ferramentas
- **Read-only primeiro:** para diagnosticar, prefira as tools de `status`/`health`/`check` (não alteram estado) antes de subir ambiente.
- **DEV, nunca PROD:** **não** chame `fluxo_prod_up`. Deploy de produção é manual, travado por variável de ambiente + frase de confirmação no servidor, e exige autorização explícita do Lucas em português (ver AGENTS.md).
- **Efeitos colaterais só com intenção clara:** `fluxo_dev_up` (sobe containers) e `campaign_enqueue_test_event` (gera evento) só quando a tarefa pedir explicitamente.
- **Degradação graciosa:** se a ferramenta não existir nesta máquina, siga manualmente — mas avise que um MCP/skill cobriria isso (e que dá pra espelhar a config via `~/.claude.json`).

## Skills de plugin gerais (use quando couber)
- Código: `engineering:code-review`, `engineering:debug`, `/security-review`.
- Dados/SQL: `data:*`. Design/UX: `design:*`. Produto: `product-management:*`.
- Fluxos do superpowers: `superpowers:brainstorming`, `test-driven-development`, `systematic-debugging`, etc.
- **Docs de libs/SDKs:** consulte a documentação atual via context7 (`query-docs`) antes de responder de memória.
