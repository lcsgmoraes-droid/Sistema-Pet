# Sonar Gate Equilibrado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Manter o SonarCloud visivel no PR sem fazer o `Quality Gate` esperar ate 12 minutos pelo check externo.

**Architecture:** O `Quality Gate` continua sendo o check obrigatorio de seguranca operacional do backend, dependente de `Tests & Quality` e `Migration Smoke`. O SonarCloud permanece como check externo independente do GitHub/SonarCloud, aparecendo no PR, mas sem espera duplicada dentro do workflow.

**Tech Stack:** GitHub Actions, GitHub CLI no runner, SonarCloud automatic analysis, pytest contract tests.

---

### Task 1: Atualizar Contrato Do Workflow

**Files:**
- Modify: `tests/test_backend_ci_workflow_contract.py`

- [ ] **Step 1: Escrever o teste que exige Sonar visivel, mas nao bloqueante dentro do gate**

```python
def test_backend_ci_quality_gate_does_not_wait_for_sonarcloud_external_check():
    source = _workflow_source()

    assert "Quality Gate" in source
    assert "SonarCloud Code Analysis" not in source
    assert "SONAR_WAIT_SECONDS" not in source
    assert "check-runs" not in source
    assert "Operational backend checks passed" in source
```

- [ ] **Step 2: Rodar o teste e confirmar falha**

Run: `python -m pytest tests/test_backend_ci_workflow_contract.py::test_backend_ci_quality_gate_does_not_wait_for_sonarcloud_external_check -q`

Expected: FAIL porque o workflow atual ainda contem `SONAR_WAIT_SECONDS`, `check-runs` e espera pelo `SonarCloud Code Analysis`.

### Task 2: Simplificar O Quality Gate

**Files:**
- Modify: `.github/workflows/backend-ci.yml`

- [ ] **Step 1: Remover o passo de espera do SonarCloud**

Substituir o step `Ensure SonarCloud external check passed` por um step unico que apenas registra os checks operacionais:

```yaml
      - name: All required backend checks passed
        run: |
          echo "Operational backend checks passed"
          echo "Tests & Quality passed"
          echo "Startup import passed"
          echo "Migration smoke passed"
          echo "SonarCloud runs as an independent PR check and is not waited on here"
```

- [ ] **Step 2: Rodar o teste de contrato e confirmar verde**

Run: `python -m pytest tests/test_backend_ci_workflow_contract.py -q`

Expected: PASS.

### Task 3: Atualizar Documentacao Da Estrategia

**Files:**
- Modify: `docs/CI_CD_DEPLOY_SAFETY_AUDIT.md`
- Modify: `docs/MATURIDADE_GERAL_10_10_GUIA.md`

- [ ] **Step 1: Trocar a descricao antiga**

Registrar que o SonarCloud permanece como check externo independente/visivel no PR, e que o `Quality Gate` nao espelha mais o check externo para evitar espera duplicada.

- [ ] **Step 2: Rodar validacoes finais**

Run:

```powershell
python -m pytest tests/test_backend_ci_workflow_contract.py tests/test_sonarcloud_config_contract.py -q
.\FLUXO_UNICO.bat check
```

Expected: todos os testes passam e o fluxo unico retorna `OK`.
