from pathlib import Path

import pytest

from app.classificador_racao import ClassificadorRacao


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(path: str) -> str:
    return (BACKEND_ROOT / path).read_text(encoding="utf-8")


def test_racao_ia_report_files_do_not_use_datetime_utcnow():
    for path in (
        "app/ia/aba5_fluxo_caixa.py",
        "app/ia/aba5_fluxo_caixa_parts/base.py",
        "app/ia/aba5_fluxo_caixa_parts/indices.py",
        "app/ia/aba5_fluxo_caixa_parts/projecoes.py",
        "app/ia/aba5_fluxo_caixa_parts/acoes.py",
        "app/ia/aba7_dre.py",
    ):
        assert "datetime.utcnow(" not in _source(path)


def test_racao_weight_extraction_keeps_common_formats():
    classificador = ClassificadorRacao()

    assert classificador.extrair_peso("Racao Premium 15kg") == 15
    assert classificador.extrair_peso("Racao Premium 10 kg") == 10
    assert classificador.extrair_peso("Sachê gato 500g") == pytest.approx(0.5)
    assert classificador.extrair_peso("Racao 1,5 kg") == pytest.approx(1.5)


def test_dre_category_period_args_are_explicitly_unused():
    source = _source("app/ia/aba7_dre.py")

    assert "_data_inicio: date" in source
    assert "_data_fim: date" in source
