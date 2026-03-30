from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.bling_flow_monitor_service import (
    _build_incident_key,
    _obter_nfs_recentes_bling,
    _reconciliar_pedido_confirmado,
    diagnosticar_pedido_integrado,
    _nf_recentes_cache,
    normalizar_data_evento_monitor,
    registrar_vinculo_nf_pedido,
    serializar_data_evento_monitor,
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


def test_diagnosticar_pedido_aberto_aponta_nf_detectada_sem_vinculo():
    pedido = SimpleNamespace(
        id=3,
        pedido_bling_id="BL-3",
        pedido_bling_numero="11600",
        status="aberto",
        tenant_id="tenant-1",
        canal="mercado_livre",
        payload={"pedido": {"numeroLoja": "2000015749248294"}},
    )

    incidentes = diagnosticar_pedido_integrado(
        pedido,
        [SimpleNamespace(sku="SKU-1", vendido_em=None, liberado_em=None)],
        pedido.payload,
        movimentacoes_saida=0,
        nfs_detectadas=[
            {
                "id": "NF-10984",
                "numero": "010984",
                "numero_pedido_loja": "2000015749248294",
                "situacao_codigo": 5,
                "canal": "mercado_livre",
                "valor_total": 166.90,
            }
        ],
    )

    codigos = {incidente["code"] for incidente in incidentes}

    assert "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO" in codigos


def test_diagnosticar_pedido_aberto_aponta_multiplas_nfs_para_mesmo_pedido_loja():
    pedido = SimpleNamespace(
        id=4,
        pedido_bling_id="BL-4",
        pedido_bling_numero="11601",
        status="aberto",
        tenant_id="tenant-1",
        canal="shopee",
        payload={"pedido": {"numeroLoja": "260329D3XB4GMW"}},
    )

    incidentes = diagnosticar_pedido_integrado(
        pedido,
        [SimpleNamespace(sku="SKU-1", vendido_em=None, liberado_em=None)],
        pedido.payload,
        movimentacoes_saida=0,
        nfs_detectadas=[
            {
                "id": "NF-1",
                "numero": "010983",
                "numero_pedido_loja": "260329D3XB4GMW",
                "situacao_codigo": 5,
                "canal": "shopee",
            },
            {
                "id": "NF-2",
                "numero": "010999",
                "numero_pedido_loja": "260329D3XB4GMW",
                "situacao_codigo": 5,
                "canal": "shopee",
            },
        ],
    )

    codigos = {incidente["code"] for incidente in incidentes}

    assert "NF_MULTIPLA_ENCONTRADA_POR_PEDIDO_LOJA" in codigos


def test_obter_nfs_recentes_bling_enriquece_resumo_quando_lista_nao_traz_pedido_loja(monkeypatch):
    class _FakeBlingAPI:
        def listar_nfes(self, data_inicial=None, data_final=None):
            return {
                "data": [
                    {
                        "id": "NF-10984",
                        "numero": "010984",
                        "situacao": 5,
                        "dataEmissao": "2026-03-29 12:22:54",
                        "loja": {"id": 204647675},
                    }
                ]
            }

        def listar_nfces(self, data_inicial=None, data_final=None):
            return {"data": []}

    monkeypatch.setattr("app.bling_integration.BlingAPI", _FakeBlingAPI)
    monkeypatch.setattr(
        "app.integracao_bling_nf_routes._consultar_relacao_nf_bling",
        lambda nf_id, situacao_num: {
            "pedido_bling_id": "25429854609",
            "pedido_bling_numero": "11600",
            "numero_pedido_loja": "2000015749248294",
            "nf_completa": {
                "loja": {"id": 204647675},
                "valorTotal": 166.90,
            },
        },
    )
    _nf_recentes_cache.clear()

    notas = _obter_nfs_recentes_bling(tenant_id="tenant-1", dias=7)

    assert len(notas) == 1
    assert notas[0]["numero_pedido_loja"] == "2000015749248294"
    assert notas[0]["pedido_bling_numero"] == "11600"
    assert notas[0]["canal"] == "mercado_livre"


def test_normalizar_data_evento_monitor_converte_iso_utc_em_datetime_naive():
    data = normalizar_data_evento_monitor("2026-03-29T18:35:00+00:00")

    assert data == datetime(2026, 3, 29, 18, 35, 0)
    assert data.tzinfo is None


def test_serializar_data_evento_monitor_assume_naive_como_utc():
    texto = serializar_data_evento_monitor(datetime(2026, 3, 29, 18, 35, 0))

    assert texto == "2026-03-29T18:35:00+00:00"


def test_registrar_vinculo_nf_pedido_monta_payload_com_relacao(monkeypatch):
    capturado = {}

    def _fake_registrar_evento(**kwargs):
        capturado.update(kwargs)
        return 77

    monkeypatch.setattr("app.services.bling_flow_monitor_service.registrar_evento", _fake_registrar_evento)
    pedido = SimpleNamespace(
        id=15,
        tenant_id="tenant-1",
        pedido_bling_id="25430581957",
        pedido_bling_numero="11601",
        status="aberto",
        payload={
            "pedido": {"numeroLoja": "260329D3XB4GMW"},
            "ultima_nf": {"id": "25427303470", "numero": "010984"},
        },
    )

    resultado = registrar_vinculo_nf_pedido(
        pedido=pedido,
        source="webhook",
        nf_bling_id="25427303470",
        nf_numero="010984",
        payload={"link_source": "nf.webhook"},
        processed_at="2026-03-29T18:35:00+00:00",
    )

    assert resultado == 77
    assert capturado["event_type"] == "invoice.linked_to_order"
    assert capturado["processed_at"] == "2026-03-29T18:35:00+00:00"
    assert capturado["payload"]["pedido_bling_numero"] == "11601"
    assert capturado["payload"]["numero_pedido_loja"] == "260329D3XB4GMW"
    assert capturado["payload"]["nf_numero"] == "010984"
    assert capturado["payload"]["link_source"] == "nf.webhook"


def test_reconciliar_pedido_confirmado_so_confirma_item_apos_baixa(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        id=1088,
        tenant_id="tenant-1",
        pedido_bling_numero="11598",
        status="aberto",
        confirmado_em=None,
        payload={"ultima_nf": {"id": "NF-11598", "situacao_codigo": 5}},
    )
    item = SimpleNamespace(sku="022860.1/2", quantidade=1, vendido_em=None)

    monkeypatch.setattr(
        "app.services.bling_nf_service.processar_nf_autorizada",
        lambda **kwargs: "venda_confirmada",
    )

    sucesso, detalhes = _reconciliar_pedido_confirmado(db, pedido, [item])

    assert sucesso is True
    assert detalhes["acao"] == "venda_confirmada"
    assert detalhes["nf_id"] == "NF-11598"


def test_reconciliar_pedido_confirmado_nao_confirma_item_quando_baixa_falha(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        id=1088,
        tenant_id="tenant-1",
        pedido_bling_numero="11598",
        status="aberto",
        confirmado_em=None,
        payload={"ultima_nf": {"id": "NF-11598", "situacao_codigo": 5}},
    )
    item = SimpleNamespace(sku="022860.1/2", quantidade=1, vendido_em=None)
    monkeypatch.setattr(
        "app.services.bling_nf_service.processar_nf_autorizada",
        lambda **kwargs: "erro",
    )

    sucesso, detalhes = _reconciliar_pedido_confirmado(db, pedido, [item])

    assert sucesso is False
    assert item.vendido_em is None
    assert detalhes["acao"] == "erro"


def test_reconciliar_pedido_confirmado_sem_nf_deterministica_nao_aplica_baixa():
    db = Mock()
    pedido = SimpleNamespace(
        id=1088,
        tenant_id="tenant-1",
        pedido_bling_numero="11598",
        status="aberto",
        confirmado_em=None,
        payload={"ultima_nf": {"id": "-1"}},
    )
    item = SimpleNamespace(sku="022860.1/2", quantidade=1, vendido_em=None)

    sucesso, detalhes = _reconciliar_pedido_confirmado(db, pedido, [item])

    assert sucesso is False
    assert detalhes["motivo"] == "nf_ausente_ou_nao_autorizada"
