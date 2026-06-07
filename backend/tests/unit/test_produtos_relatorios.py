from datetime import datetime

from app.produtos.relatorios import (
    _parse_relatorio_datetime,
    _serializar_movimentacao_relatorio,
)


class FakeObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_parse_relatorio_datetime_normaliza_inicio_e_fim_do_dia():
    assert _parse_relatorio_datetime("2026-06-07").isoformat() == "2026-06-07T00:00:00"
    assert (
        _parse_relatorio_datetime("2026-06-07", end_of_day=True).isoformat()
        == "2026-06-07T23:59:59.999999"
    )
    assert _parse_relatorio_datetime("data-invalida") is None
    assert _parse_relatorio_datetime("") is None


def test_serializar_movimentacao_relatorio_preserva_contrato_visual():
    produto = FakeObject(
        codigo="SKU-1",
        sku="SKU-FISCAL",
        codigo_barras="7891234567890",
        nome="Produto Teste",
    )
    usuario = FakeObject(nome="Lucas")
    movimento = FakeObject(
        id=10,
        created_at=datetime(2026, 6, 7, 15, 30),
        produto=produto,
        produto_id=20,
        quantidade=2,
        quantidade_nova=5,
        tipo="saida",
        motivo="venda",
        custo_unitario=3.5,
        valor_total=7,
        user=usuario,
        documento="202606070001",
        observacao="ok",
        lotes_consumidos=[{"lote": "A"}],
    )

    serializado = _serializar_movimentacao_relatorio(
        movimento,
        {"em_promocao": True, "desconto_promocional": 1.25},
    )

    assert serializado["data"] == "07/06/2026"
    assert serializado["sku"] == "SKU-FISCAL"
    assert serializado["saida"] == 2.0
    assert serializado["entrada"] is None
    assert serializado["usuario"] == "Lucas"
    assert serializado["em_promocao"] is True
    assert serializado["desconto_promocional"] == 1.25
