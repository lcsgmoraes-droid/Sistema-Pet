from types import SimpleNamespace

from app.caixa_routes import _anexar_conferencia_abertura


def test_conferencia_de_abertura_preserva_observacao_e_registra_diferenca():
    anterior = SimpleNamespace(numero_caixa=41, valor_informado=250.0)

    observacao = _anexar_conferencia_abertura(
        "Troco separado pelo gerente.",
        caixa_anterior=anterior,
        valor_abertura=230.0,
    )

    assert "Troco separado pelo gerente." in observacao
    assert "Caixa anterior #41: R$ 250.00" in observacao
    assert "diferenca: R$ -20.00" in observacao


def test_conferencia_sem_caixa_anterior_nao_inventa_registro():
    assert (
        _anexar_conferencia_abertura(
            "Primeira abertura", caixa_anterior=None, valor_abertura=100.0
        )
        == "Primeira abertura"
    )
