"""Leituras repetidas cruzam Financial atual sem refazer venda ou CMV."""

from copy import deepcopy
from datetime import datetime
import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.dre_canais import agregacao
from app.dre_canais import detalhes as detalhes_dre
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dashboard import ponto_equilibrio_margem as pe
from app.dashboard import ponto_equilibrio_routes as pe_routes
from app.ia.aba6_chat_ia_parts import metricas
from app.integrations.ifood import pdv_pilot
from app.services import ifood_rentabilidade_contexto as contexto
from app.services.rentabilidade_pendencias import aplicar_pendencia_ifood


def _financial(*, complete=False):
    charges = [
        {
            "code": "ORDER_COMMISSION",
            "label": "Comissao iFood",
            "amount": 10,
            "classification": "commission",
            "signed_amount": -10,
            "status": "known",
        }
    ]
    if complete:
        charges.append(
            {
                "code": "PAYMENT_TRANSACTION_FEE",
                "label": "Taxa pagamento iFood",
                "amount": 2,
                "classification": "payment_fee",
                "signed_amount": -2,
                "status": "known",
            }
        )
    return {
        "complete": complete,
        "charges": charges,
        "pending_components": []
        if complete
        else [
            {
                "code": "PAYMENT_TRANSACTION_FEE",
                "label": "Taxa pagamento iFood",
                "reason": "Ainda nao recebida",
            }
        ],
        "fee_total": 12 if complete else None,
        "fee_known_total": 12 if complete else 10,
        "fingerprint": "revision-2" if complete else "revision-1",
        "simulated": False,
    }


def _sale():
    item = {
        "venda_item_id": 11,
        "produto_id": 10,
        "quantidade": 1,
        "venda_bruta": 100,
        "taxa_loja": 8,
        "desconto": 0,
        "taxa_entrega": 3,
        "taxa_operacional": 2,
        "taxa_cartao": 5,
        "taxa_cartao_local": 5,
        "comissao": 0,
        "imposto": 4,
        "campanha": 0,
        "custo_total": 40,
    }
    snapshot = {
        "snapshot_version": 6,
        "venda_id": 1,
        "numero_venda": "DEV1420",
        "venda_bruta": 100,
        "taxa_loja": 8,
        "desconto": 0,
        "taxa_entrega": 3,
        "taxa_operacional": 2,
        "taxa_cartao": 5,
        "taxa_cartao_local": 5,
        "comissao": 0,
        "imposto": 4,
        "custo_campanha": 0,
        "custo_produtos": 40,
        "venda_liquida": 94,
        "lucro": 54,
        "margem_sobre_venda": 54,
        "itens": [item],
    }
    produto = SimpleNamespace(
        id=10, nome="SKU piloto", preco_custo=999, categoria=SimpleNamespace(nome="Pet")
    )
    return SimpleNamespace(
        id=1,
        tenant_id="tenant-dev",
        canal="ifood",
        numero_venda="DEV1420",
        total=108,
        taxa_entrega=8,
        subtotal=100,
        desconto_valor=0,
        desconto_venda_valor=0,
        cupom_code=None,
        status="finalizada",
        pagamentos=[],
        entregador_id=None,
        tem_entrega=True,
        data_venda=datetime(2026, 10, 24, 12),
        cliente=None,
        rentabilidade_snapshot=snapshot,
        itens=[
            SimpleNamespace(
                id=11, produto_id=10, produto=produto, quantidade=1, subtotal=100
            )
        ],
    )


def _preloads(monkeypatch, module):
    monkeypatch.setattr(module, "_formas_pagamento_map", lambda *args: {})
    monkeypatch.setattr(module, "_impostos_percentual", lambda *args: 0)
    for name in (
        "_bulk_comissoes_por_venda",
        "_bulk_cupons_por_venda",
        "_bulk_cashback_por_venda",
        "_bulk_taxa_operacional_por_venda",
        "_bulk_estoque_custos_por_venda",
    ):
        monkeypatch.setattr(module, name, lambda *args: {})


def test_contexto_nao_consulta_financial_para_outros_canais_ou_ids_ausentes():
    db = MagicMock()
    vendas = [SimpleNamespace(id=2, canal="app"), SimpleNamespace(canal="ifood")]
    assert contexto.carregar_financial_das_vendas(db, "tenant-dev", vendas) == {}
    assert contexto.carregar_snapshots_ifood_vendas(db, "tenant-dev", vendas) == {}
    db.query.assert_not_called()
    db.execute.assert_not_called()


def test_dre_exibe_comissao_recebida_e_completa_nova_leitura_sem_mudar_cmv(monkeypatch):
    venda = _sale()
    original = deepcopy(venda.rentabilidade_snapshot)
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        venda
    ]
    _preloads(monkeypatch, agregacao)
    estado = {1: _financial()}
    calls = []
    monkeypatch.setattr(
        agregacao,
        "carregar_financial_das_vendas",
        lambda *args: calls.append(args[2]) or estado,
    )
    primeira = agregacao.obter_vendas_por_canal(db, 10, 2026, "tenant-dev")
    linhas, totais = montar_linhas_dre_competencia(primeira)
    taxas = {
        linha.campo: linha for linha in linhas if linha.campo and linha.canal == "ifood"
    }
    assert taxas["taxas_marketplace"].valor == 10
    assert taxas["taxas_cartao"].valor is None
    assert totais["lucro_liquido"] is None
    assert totais["cmv"] == 40

    estado[1] = _financial(complete=True)
    segunda = agregacao.obter_vendas_por_canal(db, 10, 2026, "tenant-dev")
    _, totais = montar_linhas_dre_competencia(segunda)
    assert totais["lucro_liquido"] == 42
    assert totais["cmv"] == 40
    assert totais["taxas_ifood_pendentes"] is False
    assert len(calls) == 2
    assert venda.rentabilidade_snapshot == original
    db.flush.assert_not_called()


def test_dre_nao_transforma_taxa_local_desconhecida_em_zero_ao_reaplicar_overlay(
    monkeypatch,
):
    venda = _sale()
    venda.rentabilidade_snapshot.pop("taxa_cartao_local")
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        venda
    ]
    _preloads(monkeypatch, agregacao)
    monkeypatch.setattr(
        agregacao,
        "carregar_financial_das_vendas",
        lambda *args: {1: _financial(complete=True)},
    )
    dados = agregacao.obter_vendas_por_canal(db, 10, 2026, "tenant-dev")
    linhas, totais = montar_linhas_dre_competencia(dados)
    card = next(
        row for row in linhas if row.canal == "ifood" and row.campo == "taxas_cartao"
    )
    assert card.valor is None
    assert totais["lucro_liquido"] is None
    assert totais["taxas_ifood_pendentes"]
    assert venda.rentabilidade_snapshot["taxa_cartao"] == 5


def test_pe_deduz_cada_taxa_uma_vez_e_nao_esconde_comissao_quando_falta_pagamento(
    monkeypatch,
):
    venda = _sale()
    _preloads(monkeypatch, pe)
    estado = {1: _financial()}
    monkeypatch.setattr(pe, "carregar_financial_das_vendas", lambda *args: estado)
    parcial = pe._preparar_snapshots_margem_vendas_pe(
        object(), "tenant-dev", [venda], "completo"
    )
    somado = pe._somar_componentes_margem_vendas_pe(parcial)
    assert somado["taxas_ifood"] == 10
    assert somado["taxas_cartao"] is None
    assert somado["margem_contribuicao"] is None

    estado[1] = _financial(complete=True)
    completas = pe._preparar_snapshots_margem_vendas_pe(
        object(), "tenant-dev", [venda], "completo"
    )
    somado = pe._somar_componentes_margem_vendas_pe(completas)
    assert somado["taxas_ifood"] == 10
    assert somado["taxas_cartao"] == 7  # 5 local congelado +2 iFood, nao +12.
    assert somado["margem_contribuicao"] == 42


@pytest.mark.parametrize("amount", [0, -2])
def test_detalhes_preservam_taxa_conhecida_zero_ou_credito_sem_ocultar_por_outra_pendencia(
    monkeypatch, amount
):
    venda = _sale()
    financial = _financial()
    financial["charges"][0]["amount"] = amount
    financial["fee_known_total"] = amount
    snapshot = aplicar_pendencia_ifood(
        venda, venda.rentabilidade_snapshot, financial=financial
    )
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        venda
    ]
    monkeypatch.setattr(
        detalhes_dre, "_preparar_snapshots_vendas", lambda *args: {1: snapshot}
    )
    rows = detalhes_dre._detalhes_vendas_campo(
        db, 10, 2026, "tenant-dev", "ifood", "taxas_marketplace"
    )
    assert len(rows) == 1 and rows[0].valor == amount
    assert rows[0].meta["rentabilidade_status"] == "complete"
    assert rows[0].meta["ifood_financial"] == financial
    totals = pe._somar_componentes_margem_vendas_pe([{"snapshot": snapshot}])
    details = totals["detalhes_margem"]["componentes"]["taxas_ifood"]
    assert len(details) == 1 and details[0]["valor"] == amount
    assert details[0]["ifood_financial"] == financial


def test_pe_detalhe_conhecido_nao_herda_pendencia_global_de_outro_componente(
    monkeypatch,
):
    async def resultado(**_kwargs):
        return {
            "periodo": {},
            "detalhes_margem": {
                "subtotais": [
                    {"id": "taxas_ifood", "label": "Comissao iFood", "valor": 10}
                ],
                "componentes": {"taxas_ifood": []},
            },
            "vendas_rentabilidade_pendente": 1,
            "pendencias_rentabilidade": ["Pagamento ainda nao informado"],
        }

    monkeypatch.setattr(pe_routes, "obter_ponto_equilibrio", resultado)
    detail = asyncio.run(
        pe_routes.obter_ponto_equilibrio_detalhes(
            grupo="taxas_ifood", db=object(), user_and_tenant=object()
        )
    )
    assert detail["total"] == 10
    assert detail["rentabilidade_status"] == "complete"
    assert detail["vendas_rentabilidade_pendente"] == 0
    assert detail["pendencias_rentabilidade"] == []


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def options(self, *args):
        return self

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class _Metricas(metricas.ChatIAMetricasMixin):
    def __init__(self, venda):
        from app.financeiro_models import ContaPagar

        self.db = SimpleNamespace(
            query=lambda model: _Query([] if model is ContaPagar else [venda])
        )


def test_ia_usa_taxas_e_cmv_congelado_sem_prender_status_ao_canal(monkeypatch):
    venda = _sale()
    estado = {
        1: aplicar_pendencia_ifood(
            venda, venda.rentabilidade_snapshot, financial=_financial()
        )
    }
    monkeypatch.setattr(
        metricas, "carregar_snapshots_ifood_vendas", lambda *args: estado
    )
    service = _Metricas(venda)
    periodo = ("tenant-dev", datetime(2026, 10, 1), datetime(2026, 10, 31))
    assert service._obter_produtos_periodo(*periodo)["top_margem"] == []
    estado[1] = aplicar_pendencia_ifood(
        venda, venda.rentabilidade_snapshot, financial=_financial(complete=True)
    )
    produtos = service._obter_produtos_periodo(*periodo)
    dre = service._obter_dre_simplificada_mes(*periodo)
    assert produtos["top_margem"][0]["lucro"] == 42
    assert (
        dre["cmv_estimado"] == 40
    )  # Cadastro atual =999, nao pode substituir a prova.
    assert dre["lucro_liquido_estimado"] == 42
    assert dre["taxas_ifood_pendentes"] is False
    assert (
        service._obter_rankings_periodo(*periodo)["top_categorias_margem"][0]["lucro"]
        == 42
    )


def test_pdv_consulta_taxas_atuais_sem_mudar_recebivel_auditado(monkeypatch):
    venda = _sale()
    bridge = SimpleNamespace(ifood_order_id="order1420")
    original = {
        "payment_mode": "online",
        "receivable": {"status": "awaiting_financial", "received_amount": 0},
    }
    saved = deepcopy(original)
    monkeypatch.setattr(pdv_pilot, "pilot_settings_reason", lambda **kwargs: None)
    monkeypatch.setattr(pdv_pilot, "_bridge", lambda *args, **kwargs: bridge)
    monkeypatch.setattr(pdv_pilot, "pdv_bridge_summary", lambda *args: original)
    snapshot = aplicar_pendencia_ifood(
        venda, venda.rentabilidade_snapshot, financial=_financial(complete=True)
    )
    monkeypatch.setattr(
        pdv_pilot, "carregar_snapshots_ifood_vendas", lambda *args: {1: snapshot}
    )
    db = MagicMock()
    resultado = pdv_pilot.pdv_sale_summary(db, venda)
    assert resultado["ifood_financial"]["complete"] is True
    assert resultado["ifood_rentabilidade"]["lucro"] == 42
    assert resultado["receivable"]["received_amount"] == 0
    assert original == saved
    db.flush.assert_not_called()
