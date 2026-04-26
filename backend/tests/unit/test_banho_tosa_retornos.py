from app.banho_tosa_retornos import _ordem_prioridade, _prioridade_por_dias


def test_prioridade_retorno_por_dias():
    assert _prioridade_por_dias(-2) == "critica"
    assert _prioridade_por_dias(7) == "alta"
    assert _prioridade_por_dias(15) == "media"
    assert _prioridade_por_dias(30) == "baixa"


def test_ordem_prioridade_retorno():
    prioridades = ["baixa", "critica", "media", "alta"]
    assert sorted(prioridades, key=_ordem_prioridade) == ["critica", "alta", "media", "baixa"]
