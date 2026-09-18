---
tipo: eixo
atualizado: 2026-09-12
---

# CI/CD

Um dos 4 grandes eixos. Ver [[README]]. Fontes confirmadas: `.github/workflows/*.yml`, `.githooks/`, `.github/pull_request_template.md`, `.github/dependabot.yml`, `scripts/deploy_producao_seguro.sh` (lido por completo), `scripts/deploy_producao_remoto.ps1`, `scripts/fluxo_unico.ps1`, `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`, `docs/PRODUCAO_DEPLOY_SSH.md`.

## Como o desenvolvimento funciona hoje (confirmado)

### Branches e commits

- Fluxo de branch por tarefa, imposto **localmente por git hooks** (`.githooks/pre-commit`, `.githooks/pre-push`):
  - `pre-commit` bloqueia commit direto em `main`/`master` (exceto `--no-verify` explícito).
  - `pre-push` bloqueia push direto para `main`/`master`, exceto com `ALLOW_MAIN_PUSH=1` explícito.
- Script oficial para abrir tarefa: `scripts/git_start_task.ps1 -Tipo <feat|fix|docs|chore|refactor|test|hotfix> -Nome "..."` — gera branch `tipo/AAAAMMDD-HHmm-slug`, exige árvore limpa e atualiza `main` antes de criar a branch.
- Script oficial para fechar tarefa: `scripts/git_finish_task.ps1 -Mensagem "..." -Push`.
- Regra reforçada em `AGENTS.md`/`CLAUDE.md`: nunca commit/push direto em `main`, PR obrigatório no GitHub.

### Pull Requests

- Template obrigatório (`.github/pull_request_template.md`) exige: resumo, tipo de mudança, classificação de risco, link de ficha de entrega/homologação quando aplicável, plano de rollback, checklist (testou o que alterou, avaliou tenant/permissões/integrações, não incluiu `.env`/dumps/backups, está em branch de tarefa, entende que o PR não autoriza deploy).
- Para mudanças de maior porte (funcionalidade, integração, migration, segurança, arquitetura), `docs/templates/FICHA_ENTREGA.md` é usado como gate adicional (confirmado em `docs/GOVERNANCA_ENTERPRISE.md`).

### Branch protection (confirmado por documento interno, não auditável diretamente no código)

`docs/CI_CD_DEPLOY_SAFETY_AUDIT.md` declara que a branch protection da `main` no GitHub exige os checks: `MCP tests`, `Fluxo unico safety`, `Quality Gate`, `Smoke test`. ❓ **Necessita validação direta nas configurações do repositório GitHub** — não é possível confirmar regra de branch protection lendo apenas o código.

## Pipeline de CI existente (confirmado — 8 workflows)

| Workflow | Gatilho | O que faz (confirmado pelo nome/arquivo) |
|---|---|---|
| `backend-ci.yml` | push/PR `main`,`develop` + manual | Testes backend, `ruff check`/`ruff format` bloqueantes, inclui job `migration-smoke` e `quality-gate` |
| `deploy-safety.yml` | push/PR `main` | Roda `scripts/validar_fluxo.ps1` (guardrails DEV→PROD) — job "Fluxo unico safety" |
| `smoke-ci.yml` | PR | Testes raiz, smoke backend/auth, `npm audit`, lint/format frontend, build frontend |
| `security-ci.yml` | PR | Análise de segurança (CodeQL python/js-ts, Trivy — conforme `DEFAULT_REQUIRED_CHECKS` em `scripts/validate_release_gate.py`) |
| `mcp-ci.yml` | PR | Testes dos MCPs locais |
| `e2e-long.yml` | `workflow_dispatch` + agenda semanal | Suite E2E longa do "Plano Básico", **fora** dos checks obrigatórios |
| `homologacao-isolada.yml` | mudança em infra + manual | Monta ambiente completo descartável (build produção + Postgres + migrations + E2E com dados fictícios), sem acessar produção |
| `eas-build.yml` | manual/condicional | Pipeline de build/update do app mobile via EAS |

Dependabot (`\.github/dependabot.yml`): atualização semanal (segundas) para pip (`backend/`, `mcp/frontend_react_server`, `mcp/ops_api_server`), npm (`frontend/`) e GitHub Actions.

## Migration Smoke (confirmado)

Job dedicado no `backend-ci.yml` cria dois bancos Postgres descartáveis: um do zero (`alembic upgrade head` em banco vazio) e um a partir de um ponto histórico específico — confirma que a cadeia de 317 migrations chega a uma única `head` sem conflito, antes de qualquer merge.

## Gate de release para deploy (confirmado, `scripts/validate_release_gate.py`)

Antes de qualquer deploy real, o script consulta a API do GitHub e exige que o commit tenha **todos** estes checks aprovados:
```
Quality Gate, Tests & Quality, Migration Smoke, Fluxo unico safety,
Smoke test, CodeQL (python), CodeQL (javascript-typescript), Trivy filesystem scan
```
Se algum check faltar ou falhar, o deploy **reverte automaticamente** o código para o commit anterior no servidor (`git reset --hard $HEAD_BEFORE`) e aborta — não fica com um commit não aprovado rodando.

## Pipeline de deploy (CD) — confirmado, script lido por completo

Não há deploy automático por push. O fluxo é:

```text
scripts/deploy_producao_remoto.ps1  (roda no PC do responsável)
  -> valida DNS de corepet.com.br
  -> SSH para petdeploy@corepet.com.br (chave dedicada, IdentitiesOnly)
  -> sudo -n /usr/local/sbin/petshop-deploy-producao   (wrapper root restrito)
       -> scripts/deploy_producao_seguro.sh  (script real, no servidor)
```

Passos confirmados do `deploy_producao_seguro.sh` (nessa ordem):

1. Lock exclusivo (`flock`) — recusa deploy concorrente.
2. Revalida o destino público (DNS) no próprio servidor.
3. Exige repositório Git limpo (sem alterações locais nem artefatos versionados indevidos).
4. Cria diretório de backup com o commit atual.
5. `git fetch` + `git reset --hard origin/main`.
6. **Gate de release** (checks do GitHub) — se falhar, reverte automaticamente.
7. Se o diff só mexeu em `docs/`/`.github/`/Markdown → pula rebuild/restart, só valida health.
8. Caso contrário: reinstala guardas operacionais (retenção de journal, disk guard, host watchdog, monitor TLS, backups de continuidade); builda frontend (`npm ci && npm run build`) em diretório "next"; rebuilda imagem Docker do backend; sobe Postgres; **`pg_dump` do banco ANTES de qualquer migration** (retém últimos 10); `alembic upgrade head`; checagem de guard RLS ("no-debt"); sobe `backend`/`worker-bling`/`worker-catalogo`; só então troca `runtime/frontend/dist` (mantém `.prev`); recria `nginx`; valida watchdog interno, heartbeat dos workers, health público e **confirma que o domínio público está servindo o commit implantado**; roda checagens finais de disco/host e poda histórico de backups antigos.

## Rollback (confirmado)

Não é automático fora do caso de falha no gate. O script imprime um bloco `ROLLBACK MANUAL DISPONIVEL` com os 3 comandos exatos (restaurar `pg_dump`, `git reset --hard` para o commit anterior, resubir containers). Checklist detalhado: `docs/PRODUCAO_ROLLBACK_CHECKLIST.md`.

## Ambientes (confirmado)

| Ambiente | Uso | Isolamento |
|---|---|---|
| DEV local | Desenvolvimento | Docker Compose local + Vite, dados fictícios |
| Homologação | Aceite isolado e descartável | Ambiente `corepet-homolog`, Postgres próprio, sem acesso a segredos/banco de produção |
| CI (GitHub Actions) | Checks obrigatórios | Efêmero, bancos descartáveis por job |
| Produção | Dados reais | Servidor único, `petdeploy@corepet.com.br`, `/opt/petshop` |

## Gestão de secrets (confirmado)

- Nenhum secret real versionado em `.env.example` (só nomes de variáveis) — confirmado por busca de padrões hardcoded (ver [[Secrets]]).
- `.env` real de produção fica fora do Git, com permissão restrita (`chmod 0600`) aplicada pelo próprio script de deploy.
- GitHub Secrets são usados apenas pelo `e2e-long.yml` (variáveis `E2E_*`) — se ausentes, a suite pula com mensagem clara em vez de falhar.
- Rotação de SSH/secrets documentada em `docs/SEGURANCA_ROTACAO_SSH_SECRETS.md` (não auditado a fundo nesta rodada).

## Situação atual: o que existe vs. o que falta

**Existe (sólido, confirmado):**
- Branch protection + hooks locais redundantes.
- 8 pipelines de CI cobrindo lint, testes, segurança (CodeQL, Trivy), smoke, migrations, E2E.
- Gate de release que impede deploy de commit sem checks aprovados, com reversão automática.
- Deploy com backup pré-migration, lock exclusivo, validação de destino público, rollback documentado, watchdog externo pós-deploy.
- Dependabot semanal para as 4 stacks de dependências.

**Falta / não identificado:**
- ❓ Deploy automático por push (é deliberadamente manual — decisão documentada, não uma lacuna).
- ⚠️ Não identificado no código analisado: pipeline de deploy para o app mobile além do `eas-build.yml` (não auditado a fundo).
- ❓ Ambiente de staging remoto compartilhado — `docs/GOVERNANCA_ENTERPRISE.md` registra que isso só será criado "quando acesso compartilhado, webhooks, HTTPS ou carga contínua justificarem o custo" (decisão consciente, não descoberta).
- ❓ Confirmar regras exatas de branch protection direto no GitHub (não visível via código).

## Proposta de evolução (usando o que já existe, sem reinventar)

O pipeline atual já é maduro para o estágio de "uma pessoa + IA" documentado em `docs/GOVERNANCA_ENTERPRISE.md`. Para múltiplos desenvolvedores, a evolução recomendada é incremental sobre o que já existe, não uma reescrita:

1. **CODEOWNERS** — não encontrado no repositório. Adicionar para exigir revisão por área (backend/frontend/fiscal/integrações) quando houver mais de uma pessoa committando.
2. **Environments do GitHub** (Settings → Environments) para `production`, com required reviewers — formaliza a "autorização explícita" que hoje é só uma regra em `AGENTS.md`.
3. **Deploy automático apenas para homologação** (o `homologacao-isolada.yml` já monta o ambiente; falta automatizar o gatilho pós-merge em `main`, mantendo produção manual).
4. Manter o gate de release e o rollback exatamente como estão — já seguem o padrão de "commit aprovado → backup → migration → health check → confirmação pública" que é o estado da arte para deploy seguro sem Kubernetes.

Ver [[Vulnerabilidades]] para riscos de segurança que tocam CI/CD (ex.: rate limiting em múltiplos processos).
