# Entrada XML Acoes Processamento Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add intelligent, manually editable processing actions to XML/PDF purchase note entry so bonification notes can add stock and validity without changing costs, prices, or payables.

**Architecture:** Keep the existing preview-first flow and extend it with an explicit processing action contract. Backend owns the suggestion logic and applies flags atomically during `/notas-entrada/{nota_id}/processar`; frontend renders the suggested actions, allows manual override, and sends the selected actions with adjusted cost/price payloads.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, React, Vite.

---

### Task 1: Backend Suggestion Helpers

**Files:**
- Create: `backend/app/notas_entrada/processamento_acoes.py`
- Test: `backend/tests/unit/test_notas_entrada_processamento_acoes.py`

- [ ] **Step 1: Write failing tests for default and bonification suggestions**

```python
from app.notas_entrada.processamento_acoes import sugerir_acoes_processamento


def test_sugere_todas_acoes_para_nota_comum():
    dados_xml = {
        "natureza_operacao": "Compra para comercializacao",
        "valor_total": 125.50,
        "duplicatas": [{"valor": 125.50}],
        "itens": [{"cfop": "1102", "valor_total": 125.50}],
    }

    sugestao = sugerir_acoes_processamento(dados_xml)

    assert sugestao["acoes"] == {
        "lancar_estoque": True,
        "atualizar_custo": True,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": True,
    }
    assert sugestao["contexto"] == "nota_comum"


def test_sugere_apenas_estoque_para_bonificacao():
    dados_xml = {
        "natureza_operacao": "Bonificacao sem cobranca",
        "valor_total": 0,
        "duplicatas": [],
        "itens": [{"cfop": "1910", "valor_total": 0}],
    }

    sugestao = sugerir_acoes_processamento(dados_xml)

    assert sugestao["acoes"] == {
        "lancar_estoque": True,
        "atualizar_custo": False,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": False,
    }
    assert sugestao["contexto"] == "bonificacao"
    assert "custo atual do sistema" in sugestao["mensagem"]
```

- [ ] **Step 2: Run the new helper tests and verify they fail**

Run: `python -m pytest backend/tests/unit/test_notas_entrada_processamento_acoes.py -q`

Expected: FAIL because `app.notas_entrada.processamento_acoes` does not exist.

- [ ] **Step 3: Implement the helper**

Create `backend/app/notas_entrada/processamento_acoes.py` with:

```python
from __future__ import annotations

BONIFICACAO_CFOPS = {"1910", "2910", "5910", "6910", "1949", "2949", "5949", "6949"}
BONIFICACAO_TERMOS = ("bonificacao", "bonificação", "brinde", "amostra", "remessa")


def _texto_normalizado(valor: object) -> str:
    return str(valor or "").strip().lower()


def _tem_cobranca(dados_xml: dict) -> bool:
    duplicatas = dados_xml.get("duplicatas") or dados_xml.get("cobrancas") or []
    if any(float(item.get("valor") or item.get("valor_duplicata") or 0) > 0 for item in duplicatas):
        return True
    return float(dados_xml.get("valor_total") or 0) > 0


def _cfops(dados_xml: dict) -> set[str]:
    return {
        str(item.get("cfop") or "").strip()
        for item in (dados_xml.get("itens") or [])
        if str(item.get("cfop") or "").strip()
    }


def detectar_contexto_processamento(dados_xml: dict) -> dict:
    natureza = _texto_normalizado(dados_xml.get("natureza_operacao"))
    texto_indica_bonificacao = any(termo in natureza for termo in BONIFICACAO_TERMOS)
    cfop_indica_bonificacao = bool(_cfops(dados_xml) & BONIFICACAO_CFOPS)
    tem_cobranca = _tem_cobranca(dados_xml)
    bonificacao = (texto_indica_bonificacao or cfop_indica_bonificacao) and not tem_cobranca

    return {
        "contexto": "bonificacao" if bonificacao else "nota_comum",
        "bonificacao": bonificacao,
        "tem_cobranca": tem_cobranca,
        "cfops": sorted(_cfops(dados_xml)),
    }


def sugerir_acoes_processamento(dados_xml: dict) -> dict:
    contexto = detectar_contexto_processamento(dados_xml)
    if contexto["bonificacao"]:
        return {
            "contexto": "bonificacao",
            "mensagem": (
                "Bonificacao detectada: estoque e validade serao lancados usando "
                "o custo atual do sistema; custo, preco e financeiro ficaram desmarcados."
            ),
            "acoes": {
                "lancar_estoque": True,
                "atualizar_custo": False,
                "atualizar_preco_venda": False,
                "gerar_contas_pagar": False,
            },
        }

    return {
        "contexto": "nota_comum",
        "mensagem": "Nota comum detectada: estoque, custo e contas a pagar serao processados.",
        "acoes": {
            "lancar_estoque": True,
            "atualizar_custo": True,
            "atualizar_preco_venda": False,
            "gerar_contas_pagar": True,
        },
    }
```

- [ ] **Step 4: Verify helper tests pass**

Run: `python -m pytest backend/tests/unit/test_notas_entrada_processamento_acoes.py -q`

Expected: PASS.

### Task 2: Persist Applied Actions on Notes

**Files:**
- Modify: `backend/app/produtos_models.py`
- Create: `backend/alembic/versions/zz20260624a1_add_nota_entrada_processamento_acoes.py`
- Test: `backend/tests/unit/test_nota_entrada_processamento_model_contract.py`

- [ ] **Step 1: Write failing model contract test**

```python
from app.produtos_models import NotaEntrada


def test_nota_entrada_expoe_acoes_processamento():
    columns = NotaEntrada.__table__.columns

    assert "processamento_acoes" in columns
    assert "processamento_contexto" in columns
```

- [ ] **Step 2: Run test and verify it fails**

Run: `python -m pytest backend/tests/unit/test_nota_entrada_processamento_model_contract.py -q`

Expected: FAIL because the columns are missing.

- [ ] **Step 3: Add model columns and migration**

Add to `NotaEntrada`:

```python
    processamento_contexto = Column(String(30), nullable=True)
    processamento_acoes = Column(Text, nullable=True)
```

Create an idempotent migration adding those columns to `notas_entrada` if absent, and dropping them on downgrade if present.

- [ ] **Step 4: Verify model contract**

Run: `python -m pytest backend/tests/unit/test_nota_entrada_processamento_model_contract.py -q`

Expected: PASS.

### Task 3: Backend Preview and Processing Flags

**Files:**
- Modify: `backend/app/notas_entrada/schemas.py`
- Modify: `backend/app/notas_entrada_routes.py`
- Test: `backend/tests/unit/test_notas_entrada_processamento_config_contract.py`

- [ ] **Step 1: Write failing config and preview contract tests**

```python
from app.notas_entrada.schemas import AtualizarPrecoRequest, ProcessarConfig


def test_processar_config_defaults_preservam_fluxo_atual():
    config = ProcessarConfig()

    assert config.lancar_estoque is True
    assert config.atualizar_custo is True
    assert config.atualizar_preco_venda is True
    assert config.gerar_contas_pagar is True
    assert config.precos_venda_override == []


def test_processar_config_aceita_precos_no_payload_final():
    config = ProcessarConfig(
        atualizar_preco_venda=True,
        precos_venda_override=[{"produto_id": 10, "preco_venda": 42.9}],
    )

    assert isinstance(config.precos_venda_override[0], AtualizarPrecoRequest)
    assert config.precos_venda_override[0].produto_id == 10
```

- [ ] **Step 2: Run test and verify it fails**

Run: `python -m pytest backend/tests/unit/test_notas_entrada_processamento_config_contract.py -q`

Expected: FAIL because the new fields are missing.

- [ ] **Step 3: Extend `ProcessarConfig`**

```python
class ProcessarConfig(BaseModel):
    multiplicadores_override: dict = Field(default_factory=dict)
    custos_override: dict = Field(default_factory=dict)
    lancar_estoque: bool = True
    atualizar_custo: bool = True
    atualizar_preco_venda: bool = True
    gerar_contas_pagar: bool = True
    precos_venda_override: List[AtualizarPrecoRequest] = Field(default_factory=list)
```

- [ ] **Step 4: Add preview suggestion**

In `preview_processamento`, parse `nota.xml_content`, call `sugerir_acoes_processamento`, and include:

```python
"acoes_processamento_sugeridas": sugestao["acoes"],
"processamento_contexto": sugestao["contexto"],
"processamento_mensagem": sugestao["mensagem"],
```

- [ ] **Step 5: Move price override application into processing**

Before stock loop in `processar_entrada_estoque`, if `config.atualizar_preco_venda` and `config.precos_venda_override`, call a shared helper that applies price changes and history using the same logic as the existing `/atualizar-precos` route.

- [ ] **Step 6: Apply flags during processing**

Update processing so:

- `lancar_estoque=false` skips lotes, estoque, movements, item processed status for stock, and Bling stock sync.
- `atualizar_custo=false` uses current product cost for lot/movement when available and does not change `Produto.preco_custo` or `ProdutoFornecedor.preco_custo`.
- `gerar_contas_pagar=false` skips `criar_contas_pagar_da_nota`.
- applied actions are stored in `nota.processamento_acoes` JSON and `nota.processamento_contexto`.

- [ ] **Step 7: Verify focused backend tests**

Run:

```powershell
python -m pytest backend/tests/unit/test_notas_entrada_processamento_acoes.py backend/tests/unit/test_nota_entrada_processamento_model_contract.py backend/tests/unit/test_notas_entrada_processamento_config_contract.py -q
```

Expected: PASS.

### Task 4: Frontend Processing Actions UI

**Files:**
- Modify: `frontend/src/components/entrada-xml/EntradaXmlRevisaoPrecosModal.jsx`
- Modify: `frontend/src/components/entrada-xml/useEntradaXmlRevisaoPrecos.js`
- Test: run frontend build

- [ ] **Step 1: Inspect existing modal props and confirm where footer actions live**

Run: `Get-Content frontend/src/components/entrada-xml/EntradaXmlRevisaoPrecosModal.jsx -TotalCount 260`

Expected: identify the final confirmation button and summary area.

- [ ] **Step 2: Add action state in hook**

In `useEntradaXmlRevisaoPrecos`, add `acoesProcessamento` state initialized from `previewComOverrides.acoes_processamento_sugeridas`, plus `setAcaoProcessamento`.

- [ ] **Step 3: Send selected actions in final processing payload**

Change `confirmarProcessamento` so it no longer calls `/atualizar-precos` separately. Instead, build `precos_venda_override` from changed prices and send it in `/processar` with:

```javascript
{
  lancar_estoque: acoesProcessamento.lancar_estoque,
  atualizar_custo: acoesProcessamento.atualizar_custo,
  atualizar_preco_venda: acoesProcessamento.atualizar_preco_venda,
  gerar_contas_pagar: acoesProcessamento.gerar_contas_pagar,
  precos_venda_override: acoesProcessamento.atualizar_preco_venda ? precosParaAtualizar : [],
  multiplicadores_override: overridesNaoDefault,
  custos_override: custosOverride,
}
```

- [ ] **Step 4: Render checkboxes and summary in the modal**

Add a compact "Acoes ao processar" section with four checkboxes and the preview message. Disable price updates when there are no changed prices, but keep manual control over estoque/custo/financeiro.

- [ ] **Step 5: Verify frontend build**

Run: `npm --prefix frontend run build`

Expected: PASS.

### Task 5: Verification and Commit

**Files:**
- All changed files

- [ ] **Step 1: Run focused backend tests**

Run:

```powershell
python -m pytest backend/tests/unit/test_notas_entrada_processamento_acoes.py backend/tests/unit/test_nota_entrada_processamento_model_contract.py backend/tests/unit/test_notas_entrada_processamento_config_contract.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run: `npm --prefix frontend run build`

Expected: PASS.

- [ ] **Step 3: Run release check**

Run: `.\FLUXO_UNICO.bat release-check`

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "Adiciona acoes selecionaveis na entrada XML"
```

Expected: commit created locally on the feature branch.

## Self-Review

- Spec coverage: suggestions, manual overrides, cost-current bonification rule, validity/lots, backend flags, frontend checkboxes, and reversao audit support are represented.
- No placeholder steps remain.
- Types are consistent: frontend sends snake_case keys matching `ProcessarConfig`; backend stores applied actions as JSON text on `NotaEntrada`.
