from types import SimpleNamespace
from decimal import Decimal

from app.banho_tosa_avaliacoes_metrics import resumir_nps


def test_resumir_nps_classifica_promotores_neutros_detratores():
    avaliacoes = [
        SimpleNamespace(nota_nps=10, nota_servico=5),
        SimpleNamespace(nota_nps=9, nota_servico=4),
        SimpleNamespace(nota_nps=7, nota_servico=None),
        SimpleNamespace(nota_nps=4, nota_servico=2),
    ]

    resumo = resumir_nps(avaliacoes)

    assert resumo["promotores"] == 2
    assert resumo["neutros"] == 1
    assert resumo["detratores"] == 1
    assert resumo["nps"] == 25
    assert resumo["nota_servico_media"] == Decimal("11") / Decimal("3")
