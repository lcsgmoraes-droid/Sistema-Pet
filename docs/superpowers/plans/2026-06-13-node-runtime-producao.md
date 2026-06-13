# Node Runtime Producao Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Padronizar o Sistema Pet em Node 22 LTS antes do proximo deploy, bloqueando deploys com Node incompatível e evitando que o servidor de producao avance codigo antes de validar o runtime.

**Architecture:** O repositorio passa a declarar Node 22 como contrato operacional para frontend web, app-mobile e CI. O script de deploy de producao ganha uma validacao de Node antes de `git reset --hard`, para falhar cedo se o host ainda estiver em Node 18. A atualizacao real do Node em producao fica em uma etapa operacional separada, executada somente com autorizacao explicita do Lucas.

**Tech Stack:** Bash, PowerShell, Python/pytest, GitHub Actions, Node.js 22 LTS, npm, Vite, Expo/EAS.

---

## Scope

Esta fatia cobre somente compatibilidade de Node e seguranca operacional do deploy. Tailwind 3 -> 4, React 18 -> 19 no frontend web, React Router 6 -> 7 e upgrades Expo/React Native ficam fora desta mudanca porque podem alterar UI, roteamento ou build mobile.

## Files

- Create: `.node-version`
- Create: `.nvmrc`
- Create: `tests/test_node_runtime_contract.py`
- Modify: `scripts/deploy_producao_seguro.sh`
- Modify: `frontend/Dockerfile`
- Modify: `frontend/Dockerfile.prod`
- Modify: `.github/workflows/smoke-ci.yml`
- Modify: `.github/workflows/eas-build.yml`
- Modify: `docs/FLUXO_UNICO_DEV_PROD.md`
- Optional modify, only if the repo already has a matching section: `docs/PLANO_10_10.md`

## Operational Rule

Do not run production Node installation, `git push origin main`, or production deploy commands until Lucas explicitly authorizes the production step in Portuguese after the PR is merged and green.

---

### Task 1: Confirm clean branch and baseline runtime evidence

**Files:**
- Read: `frontend/package.json`
- Read: `app-mobile/package.json`
- Read: `scripts/deploy_producao_seguro.sh`

- [ ] **Step 1: Confirm branch state**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## chore/20260613-0958-node-runtime-producao
```

- [ ] **Step 2: Confirm package engine requirements from npm**

Run:

```powershell
npm view vite@8.0.16 engines --json
npm view @vitejs/plugin-react@6.0.2 engines --json
npm view react-native@0.81.5 engines --json
```

Expected:

```json
{
  "node": "^20.19.0 || >=22.12.0"
}
{
  "node": "^20.19.0 || >=22.12.0"
}
{
  "node": ">= 20.19.4"
}
```

- [ ] **Step 3: Confirm production currently blocks deploy**

Run through the approved production read-only command path:

```bash
node -v
npm -v
```

Expected current evidence:

```text
v18.20.8
10.8.2
```

---

### Task 2: Add RED test for the Node runtime contract

**Files:**
- Create: `tests/test_node_runtime_contract.py`

- [ ] **Step 1: Write the failing static contract test**

Create `tests/test_node_runtime_contract.py` with this content:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_repo_declares_node_22_runtime_contract():
    assert (ROOT / ".node-version").read_text(encoding="utf-8").strip() == "22"
    assert (ROOT / ".nvmrc").read_text(encoding="utf-8").strip() == "22"


def test_frontend_dockerfiles_use_node_22():
    dev_dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    prod_dockerfile = (ROOT / "frontend" / "Dockerfile.prod").read_text(encoding="utf-8")

    assert "FROM node:22-alpine" in dev_dockerfile
    assert "FROM node:22-alpine AS builder" in prod_dockerfile
    assert "node:18" not in dev_dockerfile
    assert "node:20" not in prod_dockerfile


def test_github_actions_use_node_22():
    smoke_ci = (ROOT / ".github" / "workflows" / "smoke-ci.yml").read_text(
        encoding="utf-8"
    )
    eas_build = (ROOT / ".github" / "workflows" / "eas-build.yml").read_text(
        encoding="utf-8"
    )

    assert "node-version: 22" in smoke_ci
    assert "node-version: 22" in eas_build
    assert "node-version: 20" not in smoke_ci
    assert "node-version: 20" not in eas_build


def test_deploy_checks_node_before_git_reset():
    deploy_script = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
        encoding="utf-8"
    )

    assert "require_node_runtime" in deploy_script
    assert "Node.js incompativel para deploy" in deploy_script
    assert deploy_script.index("require_node_runtime") < deploy_script.index(
        'git reset --hard "$REMOTE/$BRANCH"'
    )
```

- [ ] **Step 2: Run the new test and confirm RED**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests/test_node_runtime_contract.py -q
```

Expected:

```text
FAILED tests/test_node_runtime_contract.py::test_repo_declares_node_22_runtime_contract
FAILED tests/test_node_runtime_contract.py::test_frontend_dockerfiles_use_node_22
FAILED tests/test_node_runtime_contract.py::test_github_actions_use_node_22
FAILED tests/test_node_runtime_contract.py::test_deploy_checks_node_before_git_reset
```

---

### Task 3: Declare Node 22 in repo, Docker and CI

**Files:**
- Create: `.node-version`
- Create: `.nvmrc`
- Modify: `frontend/Dockerfile`
- Modify: `frontend/Dockerfile.prod`
- Modify: `.github/workflows/smoke-ci.yml`
- Modify: `.github/workflows/eas-build.yml`

- [ ] **Step 1: Add version files**

Create `.node-version`:

```text
22
```

Create `.nvmrc`:

```text
22
```

- [ ] **Step 2: Update frontend dev Dockerfile**

Change `frontend/Dockerfile` from:

```dockerfile
# Usar Node 18 como base
FROM node:18-alpine
```

to:

```dockerfile
# Usar Node 22 LTS como base
FROM node:22-alpine
```

- [ ] **Step 3: Update frontend production Dockerfile builder**

Change `frontend/Dockerfile.prod` from:

```dockerfile
FROM node:20-alpine AS builder
```

to:

```dockerfile
FROM node:22-alpine AS builder
```

- [ ] **Step 4: Update GitHub Actions Node version for frontend smoke**

Change `.github/workflows/smoke-ci.yml` from:

```yaml
          node-version: 20
```

to:

```yaml
          node-version: 22
```

- [ ] **Step 5: Update GitHub Actions Node version for EAS mobile build**

Change `.github/workflows/eas-build.yml` from:

```yaml
          node-version: 20
```

to:

```yaml
          node-version: 22
```

- [ ] **Step 6: Run the contract test and confirm these parts pass except deploy guard if not implemented yet**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests/test_node_runtime_contract.py -q
```

Expected after Task 3 only:

```text
FAILED tests/test_node_runtime_contract.py::test_deploy_checks_node_before_git_reset
```

---

### Task 4: Add production deploy preflight before `git reset`

**Files:**
- Modify: `scripts/deploy_producao_seguro.sh`
- Test: `tests/test_node_runtime_contract.py`

- [ ] **Step 1: Add a Bash helper after `require_cmd`**

Insert this function immediately after `require_cmd()`:

```bash
require_node_runtime() {
  local node_check

  command -v node >/dev/null 2>&1 || fail "Comando obrigatorio nao encontrado: node"

  node_check="$(
    node - <<'NODE'
const version = process.versions.node;
const [major, minor, patch] = version.split(".").map(Number);
const ok =
  (major === 20 && (minor > 19 || (minor === 19 && patch >= 4))) ||
  (major === 22 && minor >= 12) ||
  major > 22;

if (!ok) {
  console.error(
    `Node.js incompativel para deploy: v${version}. ` +
      "Use Node >=20.19.4 ou Node >=22.12.0 antes de atualizar o codigo."
  );
  process.exit(1);
}

console.log(`Node.js compativel para deploy: v${version}`);
NODE
  )" || fail "$node_check"

  log "$node_check"
}
```

- [ ] **Step 2: Call the helper before the production repository changes**

Change this block:

```bash
require_cmd git
require_cmd docker
require_cmd npm
require_cmd curl
require_cmd python3

cd "$APP_DIR"
```

to:

```bash
require_cmd git
require_cmd docker
require_cmd npm
require_cmd curl
require_cmd python3
require_node_runtime

cd "$APP_DIR"
```

This call must stay before:

```bash
git fetch "$REMOTE" "$BRANCH"
git reset --hard "$REMOTE/$BRANCH"
```

- [ ] **Step 3: Run the contract test and confirm GREEN**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests/test_node_runtime_contract.py -q
```

Expected:

```text
4 passed
```

---

### Task 5: Document the Node production standard

**Files:**
- Modify: `docs/FLUXO_UNICO_DEV_PROD.md`
- Optional modify: `docs/PLANO_10_10.md`

- [ ] **Step 1: Add a production runtime note to `docs/FLUXO_UNICO_DEV_PROD.md`**

Add this section near the production deploy requirements:

```markdown
### Runtime Node.js de producao

- O build frontend de producao requer Node.js 22 LTS no host de deploy.
- O script `scripts/deploy_producao_seguro.sh` bloqueia o deploy antes de atualizar o codigo quando o Node local nao atende `>=20.19.4` ou `>=22.12.0`.
- A producao nao deve voltar para Node 18 enquanto o frontend estiver em Vite 8.
- Atualizacao de Node no servidor de producao exige autorizacao explicita do Lucas antes de qualquer comando com `sudo` ou mudanca no host.
```

- [ ] **Step 2: If `docs/PLANO_10_10.md` exists, add a short checkpoint**

Run:

```powershell
Test-Path .\docs\PLANO_10_10.md
```

If it prints `True`, add:

```markdown
## Checkpoint runtime Node.js

- Antes de continuar novas fatias RLS do plano 10/10, alinhar producao e CI em Node.js 22 LTS.
- Deploys com frontend Vite 8 ficam bloqueados em hosts com Node 18.
```

If it prints `False`, do not create a new plan file for this checkpoint.

---

### Task 6: Local verification before PR

**Files:**
- Read: `frontend/package-lock.json`
- Read: `app-mobile/package-lock.json`

- [ ] **Step 1: Run Python static tests**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests/test_node_runtime_contract.py tests/test_prod_compose_ops_alert_env.py tests/test_corepet_domain_prod_config.py -q
```

Expected:

```text
passed
```

- [ ] **Step 2: Run frontend install, audit and build**

Run:

```powershell
cd frontend
npm ci
npm audit
npm audit --omit=dev
npm run build
cd ..
```

Expected:

```text
found 0 vulnerabilities
```

and:

```text
built in
```

- [ ] **Step 3: Run app-mobile compatibility check under the current local Node**

Run:

```powershell
cd app-mobile
npm ci
npm run check
npx expo-doctor
cd ..
```

Expected:

```text
tsc --noEmit
```

and no typecheck failures. If `expo-doctor` repeats the existing native-folder warning, record it in the PR body and do not fix it in this branch.

- [ ] **Step 4: Run release validation**

Run:

```powershell
.\FLUXO_UNICO.bat check
.\FLUXO_UNICO.bat release-check
git diff --check
```

Expected:

```text
Release-check passou
```

and no whitespace errors.

---

### Task 7: Commit and open PR

**Files:**
- Stage all files changed in this plan.

- [ ] **Step 1: Review diff**

Run:

```powershell
git diff -- .node-version .nvmrc tests/test_node_runtime_contract.py scripts/deploy_producao_seguro.sh frontend/Dockerfile frontend/Dockerfile.prod .github/workflows/smoke-ci.yml .github/workflows/eas-build.yml docs/FLUXO_UNICO_DEV_PROD.md docs/PLANO_10_10.md
```

Expected:

```text
Only Node runtime contract, deploy preflight, CI/Docker alignment and docs changed.
```

- [ ] **Step 2: Finish task branch**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "chore: padronizar runtime node de producao" -Push
```

Expected:

```text
git push
```

and a pushed branch for PR.

- [ ] **Step 3: Open PR**

Open a PR with this summary:

```markdown
## Summary
- padroniza Node 22 para frontend Dockerfiles e GitHub Actions
- adiciona trava no deploy para bloquear Node incompatível antes do git reset
- documenta o contrato de runtime para producao

## Tests
- python -m pytest tests/test_node_runtime_contract.py tests/test_prod_compose_ops_alert_env.py tests/test_corepet_domain_prod_config.py -q
- npm ci / npm audit / npm audit --omit=dev / npm run build em frontend
- npm ci / npm run check / npx expo-doctor em app-mobile
- FLUXO_UNICO.bat check
- FLUXO_UNICO.bat release-check
- git diff --check
```

---

### Task 8: Production Node upgrade after PR merge

**Files:**
- No repository files changed in this task.
- Production host: `/opt/petshop`

- [ ] **Step 1: Stop and ask for explicit authorization**

Ask Lucas:

```text
Posso atualizar o Node.js da producao para Node 22 LTS agora? Isso vai alterar o runtime do host, sem mexer no banco, e depois eu valido a saude antes do deploy.
```

Proceed only if Lucas explicitly authorizes.

- [ ] **Step 2: Capture read-only production baseline**

Run through the approved production command path:

```bash
cd /opt/petshop
git rev-parse --short HEAD
git status --short --branch
node -v
npm -v
docker compose -f docker-compose.prod.yml ps
curl -fsS https://corepet.com.br/api/health
```

Expected before upgrade:

```text
Node v18.20.8
production containers healthy
health endpoint ok
```

- [ ] **Step 3: Upgrade host Node to Node 22 LTS**

Run only with approved sudo path:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v
```

Expected:

```text
v22.x.x
```

and npm installed successfully.

- [ ] **Step 4: Validate production health after Node upgrade and before app deploy**

Run:

```bash
cd /opt/petshop
docker compose -f docker-compose.prod.yml ps
curl -fsS https://corepet.com.br/api/health
```

Expected:

```text
production containers healthy
health endpoint ok
```

- [ ] **Step 5: Deploy merged main only after Node is compatible**

Run the approved safe deploy flow from `/opt/petshop`.

Expected:

```text
Deploy concluido
frontend build generated runtime/frontend/dist/index.html
backend, worker and nginx healthy
```

- [ ] **Step 6: Production smoke after deploy**

Run:

```bash
cd /opt/petshop
git rev-parse --short HEAD
docker compose -f docker-compose.prod.yml ps
curl -fsS https://corepet.com.br/api/health
curl -fsS https://corepet.com.br/ | head
```

Expected:

```text
HEAD equals merged main commit
production containers healthy
health endpoint ok
frontend HTML served
```

- [ ] **Step 7: Rollback rule if deploy fails**

If the deploy fails after backup creation, use the deploy script rollback output and the latest operational backup directory printed by the script. If Node 22 itself causes a host-level issue before deploy, stop before app deploy and restore Node 18 only after Lucas authorizes the rollback command.

---

## Self-Review

- Spec coverage: The plan covers Node upgrade, Vite compatibility, CI parity, Docker parity, production deploy safety, and explicit authorization before production host changes.
- Placeholder scan: No task uses TBD/TODO/later placeholders. Tailwind is intentionally out of scope and named as a follow-up branch.
- Type consistency: Test names, helper names and file paths match the implementation snippets.
