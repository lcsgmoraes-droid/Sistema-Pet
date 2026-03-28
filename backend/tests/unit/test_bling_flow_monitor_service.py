from types import SimpleNamespace

from app.services.bling_flow_monitor_service import (
    _build_incident_key,
    diagnosticar_pedido_integrado,
)


def test_build_incident_key_usa_referencias_principais():
    chave = _build_incident_key(
        "SKU_SEM_PRODUTO_LOCAL",
        pedido_integrado_id=10,
        pedido_bling_id="BL-1",
        nf_bling_id="NF-1",
        sku="SKU-1",
    )

    assert chave == "SKU_SEM_PRODUTO_LOCAL|10|BL-1|NF-1|SKU-1"


def test_diagnosticar_pedido_aponta_nf_autorizada_sem_confirmacao_e_sem_itens():
    pedido = SimpleNamespace(id=1, pedido_bling_id="BL-1", status="aberto")

    incidentes = diagnosticar_pedido_integrado(
        pedido,
        [],
        {"ultima_nf": {"id": "NF-1", "situacao_codigo": 9}},
        movimentacoes_saida=0,
    )

    codigos = {incidente["code"] for incidente in incidentes}

    assert "PEDIDO_SEM_ITENS" in codigos
    assert "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO" in codigos


def test_diagnosticar_pedido_confirmado_sem_baixa_e_item_nao_confirmado():
    pedido = SimpleNamespace(id=2, pedido_bling_id="BL-2", status="confirmado")
    itens = [
        SimpleNamespace(sku="SKU-1", vendido_em=None, liberado_em=None),
        SimpleNamespace(sku="SKU-2", vendido_em="2026-03-28T10:00:00", liberado_em=None),
    ]

    incidentes = diagnosticar_pedido_integrado(
        pedido,
        itens,
        {"ultima_nf": {"id": "NF-2", "situacao": "Autorizada"}},
        movimentacoes_saida=0,
        itens_sem_produto=[{"sku": "SKU-1"}],
        itens_mapeados_por_barra=[{"sku": "SKU-2", "produto_codigo": "ABC"}],
    )

    codigos = {incidente["code"] for incidente in incidentes}

    assert "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO" in codigos
    assert "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE" in codigos
    assert "SKU_SEM_PRODUTO_LOCAL" in codigos
    assert "SKU_MAPEADO_POR_CODIGO_BARRAS" in codigos
