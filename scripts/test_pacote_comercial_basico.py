from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "comercial" / "PACOTE_PILOTO_PLANO_BASICO.md"
CHECKLIST = ROOT / "docs" / "implantacao" / "CHECKLIST_PLANO_BASICO_PILOTO.md"
SMOKE_WORKFLOW = ROOT / ".github" / "workflows" / "smoke-ci.yml"


def require(content: str, terms: list[str], source: Path) -> None:
    missing = [term for term in terms if term.lower() not in content.lower()]
    assert not missing, f"{source}: secoes/termos ausentes: {missing}"


def test_commercial_package_contract() -> None:
    content = PACKAGE.read_text(encoding="utf-8")
    require(
        content,
        [
            "## 1. Oferta",
            "## 2. Fora do escopo",
            "## 3. Condicao comercial a preencher",
            "## 4. Implantacao e aceite",
            "## 5. Politica de suporte do piloto",
            "## 6. Resposta a incidente",
            "## 7. Dados, privacidade e encerramento",
            "## 9. Go/No-Go para assinar",
            "## 10. FAQ para venda sem promessa excessiva",
            "Stone",
            "WhatsApp",
            "cobranca automatica da assinatura",
            "revisao juridica",
            "P0 critico",
        ],
        PACKAGE,
    )


def test_basic_onboarding_contract() -> None:
    content = CHECKLIST.read_text(encoding="utf-8")
    require(
        content,
        [
            "plano `basico`",
            "Venda teste",
            "Baixa de estoque",
            "Canal oficial de suporte",
            "Pendencias bloqueantes",
            "dias 3 e 7",
            "sem dados sensiveis",
        ],
        CHECKLIST,
    )


def test_contract_runs_in_ci() -> None:
    content = SMOKE_WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/test_pacote_comercial_basico.py" in content
