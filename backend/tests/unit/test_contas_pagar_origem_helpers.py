from types import SimpleNamespace

from app.financeiro.contas_pagar_origem import (
    _extrair_caixa_referencia,
    _identificar_origem_conta_pagar,
)


def test_extrair_caixa_referencia_aceita_formatos_do_pdv():
    assert (
        _extrair_caixa_referencia("Gerada automaticamente pelo PDV - Caixa #123")
        == "Caixa #123"
    )
    assert _extrair_caixa_referencia("Caixa 987 fechado") == "Caixa #987"
    assert _extrair_caixa_referencia("sem caixa") is None
    assert _extrair_caixa_referencia(None) is None


def test_identificar_origem_conta_pagar_caixa_pdv():
    conta = SimpleNamespace(
        observacoes="Gerada automaticamente pelo PDV - Caixa #42",
        nota_entrada_id=None,
    )

    origem = _identificar_origem_conta_pagar(conta)

    assert origem == {
        "origem_lancamento": "caixa_pdv",
        "origem_lancamento_label": "Caixa/PDV",
        "caixa_referencia": "Caixa #42",
    }


def test_identificar_origem_conta_pagar_nota_e_manual():
    nota = SimpleNamespace(observacoes="", nota_entrada_id=10)
    manual = SimpleNamespace(observacoes="", nota_entrada_id=None)

    assert _identificar_origem_conta_pagar(nota)["origem_lancamento"] == "nota_entrada"
    assert _identificar_origem_conta_pagar(manual)["origem_lancamento"] == "manual"
