import os
from pathlib import Path


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"


BACKEND_ROOT = Path(__file__).resolve().parents[2]
FINANCEIRO_MODEL_MODULES = [
    "app/financeiro_models.py",
    "app/financeiro/models_catalogos.py",
    "app/financeiro/models_contas.py",
    "app/financeiro/models_caixa.py",
    "app/financeiro/models_conciliacao.py",
]


def _source(relative: str) -> str:
    return (BACKEND_ROOT / relative).read_text(encoding="utf-8")


def _line_count(relative: str) -> int:
    return len(_source(relative).splitlines())


def test_financeiro_models_batch_15_modules_ficam_abaixo_de_700_linhas():
    assert {
        relative: _line_count(relative) for relative in FINANCEIRO_MODEL_MODULES
    } == {
        relative: count
        for relative in FINANCEIRO_MODEL_MODULES
        if (count := _line_count(relative)) <= 700
    }


def test_financeiro_models_fachada_preserva_imports_publicos():
    from app import financeiro_models
    from app.financeiro import (
        models_caixa,
        models_catalogos,
        models_conciliacao,
        models_contas,
    )

    assert financeiro_models.CategoriaFinanceira is models_catalogos.CategoriaFinanceira
    assert financeiro_models.FormaPagamento is models_catalogos.FormaPagamento
    assert financeiro_models.TipoDespesa is models_catalogos.TipoDespesa
    assert financeiro_models.ContaPagar is models_contas.ContaPagar
    assert financeiro_models.ContaReceber is models_contas.ContaReceber
    assert financeiro_models.Pagamento is models_contas.Pagamento
    assert financeiro_models.Recebimento is models_contas.Recebimento
    assert financeiro_models.ContaBancaria is models_caixa.ContaBancaria
    assert (
        financeiro_models.MovimentacaoFinanceira is models_caixa.MovimentacaoFinanceira
    )
    assert financeiro_models.LancamentoManual is models_caixa.LancamentoManual
    assert financeiro_models.LancamentoRecorrente is models_caixa.LancamentoRecorrente
    assert financeiro_models.ExtratoBancario is models_conciliacao.ExtratoBancario
    assert (
        financeiro_models.MovimentacaoBancaria
        is models_conciliacao.MovimentacaoBancaria
    )
    assert financeiro_models.RegraConciliacao is models_conciliacao.RegraConciliacao
    assert financeiro_models.ProvisaoAutomatica is models_conciliacao.ProvisaoAutomatica
    assert financeiro_models.TemplateAdquirente is models_conciliacao.TemplateAdquirente


def test_financeiro_models_fachada_nao_concentra_definicoes_orm():
    source = _source("app/financeiro_models.py")

    assert _line_count("app/financeiro_models.py") <= 100
    assert "class ContaPagar(" not in source
    assert "class ContaReceber(" not in source
    assert "class MovimentacaoFinanceira(" not in source
    assert "class TemplateAdquirente(" not in source
