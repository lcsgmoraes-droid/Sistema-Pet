from datetime import datetime

from app.produtos.relatorios import (
    _calcular_janelas_vendas_produto,
    _calcular_totais_validade_proxima,
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


def test_calcular_janelas_vendas_produto_preserva_metricas_e_curva():
    data_fim = datetime(2026, 6, 30, 23, 59)
    janela_30_inicio = datetime(2026, 6, 1)
    rows = [
        FakeObject(
            venda_id=1,
            data_venda=datetime(2026, 6, 30),
            quantidade=2,
            subtotal=20,
        ),
        FakeObject(
            venda_id=1,
            data_venda=datetime(2026, 6, 30),
            quantidade=1,
            subtotal=5,
        ),
        FakeObject(
            venda_id=2,
            data_venda=datetime(2026, 6, 23),
            quantidade=1,
            subtotal=7,
        ),
        FakeObject(
            venda_id=3,
            data_venda=datetime(2026, 5, 20),
            quantidade=3,
            subtotal=12,
        ),
    ]

    janelas, curva_30_dias = _calcular_janelas_vendas_produto(
        rows,
        data_fim_dt=data_fim,
        janela_30_inicio=janela_30_inicio,
    )

    assert janelas["7"] == {
        "dias": 7,
        "quantidade_vendida": 3.0,
        "valor_vendido": 25.0,
        "numero_vendas": 1,
        "media_diaria": 0.43,
    }
    assert janelas["15"]["quantidade_vendida"] == 4.0
    assert janelas["15"]["valor_vendido"] == 32.0
    assert janelas["15"]["numero_vendas"] == 2
    assert janelas["60"]["quantidade_vendida"] == 7.0
    assert janelas["90"]["numero_vendas"] == 3
    assert curva_30_dias[0] == {"data": "2026-06-01", "quantidade": 0.0}
    assert curva_30_dias[-1] == {"data": "2026-06-30", "quantidade": 3.0}


def test_calcular_totais_validade_proxima_preserva_resumo_operacional():
    agora = datetime(2026, 6, 1)
    config = FakeObject(
        ativo=True,
        aplicar_app=True,
        aplicar_ecommerce=False,
        desconto_7_dias=10,
        desconto_30_dias=5,
        desconto_60_dias=0,
    )
    rows = [
        (1, 10, "tenant-1", datetime(2026, 6, 5), 2, 3, 10),
        (2, 11, "tenant-1", datetime(2026, 6, 20), 4, 5, 12),
        (3, 12, "tenant-1", datetime(2026, 5, 30), 1, 7, 15),
        (4, 13, "tenant-1", datetime(2026, 7, 20), 6, 2, 8),
    ]

    totais = _calcular_totais_validade_proxima(
        rows,
        agora=agora,
        campaign_configs={"tenant-1": config},
        exclusoes_produto={("tenant-1", 11): FakeObject(id=90)},
        exclusoes_lote={},
    )

    assert totais == {
        "total_lotes": 4,
        "total_produtos": 4,
        "total_quantidade": 13.0,
        "lotes_vencidos": 1,
        "lotes_ate_7_dias": 1,
        "lotes_ate_30_dias": 2,
        "lotes_ate_60_dias": 3,
        "valor_custo_em_risco": 45.0,
        "valor_venda_em_risco": 131.0,
        "lotes_em_campanha": 1,
        "lotes_excluidos_campanha": 1,
    }
