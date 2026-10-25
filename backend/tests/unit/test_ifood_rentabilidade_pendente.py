"""Taxas desconhecidas nao viram lucro, inclusive em fotografias antigas."""

from copy import deepcopy
from datetime import datetime
import json
from types import SimpleNamespace

import pytest

from app import relatorio_vendas_builder as report
from app.services.rentabilidade_pendencias import aplicar_pendencia_ifood
from app.services.venda_rentabilidade_snapshot_service import (
    build_venda_rentabilidade_snapshot,
    get_or_build_venda_rentabilidade_snapshot,
)


@pytest.fixture(autouse=True)
def financial_sem_evidencia(monkeypatch):
    # Estes testes isolam as regras de calculo; os vinculos SQL sao exercidos
    # pela suite propria do resolver, com tenants UUID e tabelas reais.
    monkeypatch.setattr(
        "app.services.ifood_rentabilidade_contexto.carregar_financial_das_vendas",
        lambda *_args: {},
    )
    monkeypatch.setattr(report, "carregar_financial_das_vendas", lambda *_args: {})


class NoQueries:
    def __init__(self):
        self.flushes = 0

    def query(self, *_args):
        raise AssertionError(
            "A protecao de pendencia nao precisa consultar o banco/provedor"
        )

    def flush(self):
        self.flushes += 1


def sale(sale_id=1, canal="ifood", gateway_fee=None):
    produto = SimpleNamespace(
        id=10, nome="SKU teste", preco_custo=40, categoria=None, marca=None
    )
    return SimpleNamespace(
        id=sale_id,
        tenant_id="tenant-dev",
        numero_venda=f"DEV-{sale_id}",
        canal=canal,
        loja_origem=canal,
        status="finalizada",
        data_venda=datetime(2026, 10, 24, 12),
        cliente=None,
        subtotal=65,
        desconto_valor=0,
        total=73.9,
        taxa_entrega=8.9,
        valor_taxa_entregador=0,
        tem_entrega=True,
        entregador_id=None,
        user_id=None,
        usuario=None,
        vendedor_funcionario_id=None,
        funcionario_id=None,
        cupom_code=None,
        nfe_tipo=None,
        nfe_status=None,
        nfe_numero=None,
        nfe_chave=None,
        nfe_bling_id=None,
        pagamentos=[
            SimpleNamespace(
                forma_pagamento="iFood online" if canal == "ifood" else "PIX",
                valor=73.9,
                numero_parcelas=1,
                gateway_provider="ifood" if canal == "ifood" else "mercadopago",
                gateway_fee_amount=gateway_fee,
                gateway_net_amount=None,
            )
        ],
        itens=[
            SimpleNamespace(
                id=sale_id,
                produto_id=10,
                produto=produto,
                quantidade=1,
                preco_unitario=65,
                subtotal=65,
                desconto=0,
            )
        ],
        rentabilidade_snapshot=None,
    )


def build(venda, *, db=None, **extra):
    return build_venda_rentabilidade_snapshot(
        venda,
        db or NoQueries(),
        venda.tenant_id,
        impostos_percentual=0,
        formas_pagamento_map={},
        custo_campanha=0,
        cupom_desconto=0,
        comissao_total=0,
        taxa_operacional_entrega=0,
        estoque_custos_por_produto={},
        **extra,
    )


@pytest.mark.parametrize("gateway_fee", [None, 0, 2.5])
@pytest.mark.parametrize("online", [True, False])
def test_ifood_sem_fechamento_completo_nao_inventa_taxa_lucro_ou_margem(
    gateway_fee, online
):
    venda = sale(gateway_fee=gateway_fee)
    if not online:
        venda.pagamentos = []  # Comissao de marketplace tambem existe no pagamento na entrega.
    snapshot = build(venda)
    assert snapshot["rentabilidade_status"] == "pending_ifood_financial"
    assert snapshot["taxas_ifood_pendentes"] is True
    for campo in (
        "taxa_cartao",
        "taxa_ifood",
        "taxa_gateway",
        "venda_liquida",
        "lucro",
        "margem_sobre_venda",
        "margem_sobre_custo",
        "valor_liquido_gateway",
    ):
        assert snapshot[campo] is None, campo
    item = snapshot["itens"][0]
    for campo in (
        "taxa_cartao",
        "valor_liquido",
        "lucro",
        "lucro_unitario",
        "margem_sobre_venda",
    ):
        assert item[campo] is None, campo
    assert (
        snapshot["venda_bruta"],
        snapshot["taxa_loja"],
        snapshot["custo_produtos"],
    ) == (65, 8.9, 40)
    assert (item["quantidade"], item["custo_total"], item["venda_bruta"]) == (1, 40, 65)


@pytest.mark.parametrize("version", [5, 6])
@pytest.mark.parametrize("serialized", [False, True])
def test_snapshot_legado_incorreto_e_protegido_sem_mudar_custos_congelados(
    version, serialized
):
    venda = sale()
    antigo = build(sale(canal="loja_fisica", gateway_fee=0))
    antigo.update(snapshot_version=version, custo_produtos=30, gateway_provider=None)
    original = deepcopy(antigo)
    venda.rentabilidade_snapshot = json.dumps(antigo) if serialized else antigo
    db = NoQueries()
    protegido = get_or_build_venda_rentabilidade_snapshot(venda, db, venda.tenant_id)
    assert protegido["lucro"] is None
    assert protegido["custo_produtos"] == 30
    assert protegido["itens"][0]["lucro"] is None
    assert antigo == original
    assert db.flushes == 0


@pytest.mark.parametrize("canal", ["loja_fisica", "app", "ecommerce"])
def test_taxa_real_zero_dos_demais_canais_continua_valida(canal):
    snapshot = build(sale(canal=canal, gateway_fee=0))
    assert snapshot["taxas_ifood_pendentes"] is False
    assert snapshot["lucro"] == pytest.approx(33.9)
    assert snapshot["taxa_cartao"] == 0
    assert snapshot["venda_liquida"] == 73.9


def test_gateway_ifood_em_canal_legado_tambem_e_protegido():
    venda = sale(canal="loja_fisica")
    venda.pagamentos[0].gateway_provider = "ifood"
    assert build(venda)["lucro"] is None


def test_colecao_mista_preserva_faturamento_sem_lucro_total_parcial(monkeypatch):
    vendas = [sale(), sale(sale_id=2, canal="loja_fisica", gateway_fee=0)]
    monkeypatch.setattr(report, "carregar_vendas_relatorio", lambda **_: vendas)
    contexto = {
        "impostos_percentual_global": 0,
        **{
            key: {}
            for key in (
                "comissao_total_por_venda",
                "formas_pagamento_map",
                "cashback_por_venda",
                "cupons_por_venda",
                "entregadores_map",
                "estoque_custos_por_venda",
            )
        },
    }
    monkeypatch.setattr(
        report, "carregar_contexto_relatorio_vendas", lambda **_: contexto
    )
    monkeypatch.setattr(
        report, "_enriquecer_itens_promocionais", lambda _, itens: itens
    )
    resultado = report.montar_relatorio_vendas(
        data_inicio="2026-10-24",
        data_fim="2026-10-24",
        canal_venda=None,
        db=NoQueries(),
        tenant_id="tenant-dev",
    )
    resumo = resultado["resumo"]
    assert resumo["vendas_rentabilidade_pendente"] == 1
    assert resumo["venda_bruta"] == 130
    assert resumo["custo_total"] == 80
    assert resumo["taxa_loja_total"] == 17.8
    for campo in ("lucro_total", "margem_media", "taxa_cartao_total", "venda_liquida"):
        assert resumo[campo] is None
    por_id = {v["id"]: v for v in resultado["lista_vendas"]}
    assert por_id[1]["lucro"] is None
    assert por_id[2]["lucro"] == 33.9
    assert resultado["produtos_analise"][0]["taxas_ifood_pendentes"] is True
    assert resultado["produtos_analise"][0]["valor_total"] == 130


def test_mascara_repetida_nao_muda_fotografia_ou_pagamento():
    venda = sale()
    snapshot = build(sale(canal="loja_fisica", gateway_fee=0))
    original = deepcopy(snapshot)
    pagamentos = deepcopy(vars(venda.pagamentos[0]))
    protegido = aplicar_pendencia_ifood(venda, snapshot)
    assert aplicar_pendencia_ifood(venda, protegido) == protegido
    assert snapshot == original
    assert vars(venda.pagamentos[0]) == pagamentos


def test_reprocessamento_forcado_mantem_lucro_pendente(monkeypatch):
    from app.services import venda_rentabilidade_reprocessamento_service as service

    venda = sale()
    db = NoQueries()
    monkeypatch.setattr(service, "_buscar_vendas", lambda *_args, **_kwargs: [venda])
    monkeypatch.setattr(
        service, "_corrigir_movimentacoes_custo_atual", lambda *_args: {}
    )

    def get_snapshot(venda, db, tenant, **kwargs):
        assert kwargs["force_refresh"] is True
        assert kwargs["persist_if_missing"] is True
        return get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant,
            **kwargs,
            impostos_percentual=0,
            formas_pagamento_map={},
            custo_campanha=0,
            cupom_desconto=0,
            comissao_total=0,
            taxa_operacional_entrega=0,
        )

    monkeypatch.setattr(
        service, "get_or_build_venda_rentabilidade_snapshot", get_snapshot
    )
    resultado = service.reprocessar_rentabilidade_vendas(
        db, tenant_id=venda.tenant_id, venda_ids=[1]
    )
    assert resultado["vendas"][0]["lucro_novo"] is None
    assert venda.rentabilidade_snapshot["lucro"] is None
    assert venda.rentabilidade_snapshot["custo_produtos"] == 40
    assert db.flushes == 1


def test_resumo_gestor_nao_reconstitui_margem_nos_clientes_antigos(monkeypatch):
    from datetime import date
    from app.routes import app_mobile_gestor_routes as gestor

    totais = {
        "receita_bruta": 65,
        "receita_liquida": 73.9,
        "cmv": 40,
        **dict.fromkeys(
            (
                "despesas_variaveis",
                "despesas_operacionais",
                "lucro_bruto",
                "resultado_operacional",
                "lucro_liquido",
                "margem_bruta",
                "margem_liquida",
            )
        ),
    }
    monkeypatch.setattr(
        gestor,
        "gerar_dre_por_canais",
        lambda **_: SimpleNamespace(
            totais=totais,
            periodo="10/2026",
            taxas_ifood_pendentes=True,
            rentabilidade_status="pending_ifood_financial",
            vendas_rentabilidade_pendente=1,
            pendencias_rentabilidade=["Cobrancas iFood pendentes"],
        ),
    )
    resultado = gestor._resumo_dre(
        None, None, "tenant-dev", date(2026, 10, 1), date(2026, 10, 24)
    )
    assert resultado.disponivel is False
    assert resultado.lucro_liquido is None
    assert resultado.despesas_variaveis is None
    assert resultado.receita_bruta == 65
    assert resultado.receita_liquida == 73.9
    assert resultado.cmv == 40
    assert resultado.vendas_rentabilidade_pendente == 1


def financial(
    *, commission=None, payment=None, complete=False, revision=1, simulated=False
):
    charges = [
        {
            "code": code,
            "label": label,
            "amount": amount,
            "signed_amount": -amount,
            "classification": classification,
            "status": "simulated" if simulated else "known",
            "source": "synthetic" if simulated else "ifood_financial_events",
            "revision": revision,
        }
        for code, label, classification, amount in (
            ("ORDER_COMMISSION", "Comissão iFood", "commission", commission),
            (
                "PAYMENT_TRANSACTION_FEE",
                "Taxa de pagamento iFood",
                "payment_fee",
                payment,
            ),
        )
        if amount is not None
    ]
    pending = [
        {"code": code, "label": label, "reason": "Ainda não recebida."}
        for code, label, amount in (
            ("ORDER_COMMISSION", "Comissão iFood", commission),
            ("PAYMENT_TRANSACTION_FEE", "Taxa de pagamento iFood", payment),
        )
        if amount is None
    ]
    total = sum(charge["amount"] for charge in charges)
    return {
        "charges": charges,
        "pending_components": pending,
        "fee_known_total": total,
        "fee_total": total if complete else None,
        "complete": complete,
        "simulated": simulated,
        "fingerprint": f"revision-{revision}",
    }


@pytest.mark.parametrize("commission,payment", [(6.5, None), (None, 0), (0, None)])
def test_taxa_recebida_aparece_mesmo_faltando_outro_componente(commission, payment):
    venda = sale()
    base = build(venda)
    resultado = aplicar_pendencia_ifood(
        venda, base, financial=financial(commission=commission, payment=payment)
    )
    assert resultado["taxa_ifood"] == commission
    assert resultado["taxa_cartao"] == payment
    assert resultado["lucro"] is None
    assert resultado["taxas_ifood_pendentes"] is True
    assert len(resultado["ifood_financial"]["pending_components"]) == 1


def test_financial_tardio_e_revisao_atualizam_cache_sem_reprocessar_cmv(monkeypatch):
    venda = sale()
    venda.rentabilidade_snapshot = build(venda)
    original = deepcopy(venda.rentabilidade_snapshot)
    recebido = {}
    monkeypatch.setattr(
        "app.services.ifood_rentabilidade_contexto.carregar_financial_das_vendas",
        lambda *_: {1: recebido},
    )
    db = NoQueries()
    assert (
        get_or_build_venda_rentabilidade_snapshot(venda, db, venda.tenant_id)["lucro"]
        is None
    )
    recebido.update(financial(commission=6.5))
    parcial = get_or_build_venda_rentabilidade_snapshot(venda, db, venda.tenant_id)
    assert parcial["taxa_ifood"] == 6.5 and parcial["lucro"] is None
    recebido.clear()
    recebido.update(financial(commission=6.5, payment=0, complete=True, revision=2))
    venda.itens[0].produto.preco_custo = 9999  # Custo atual nao substitui o congelado.
    completo = get_or_build_venda_rentabilidade_snapshot(venda, db, venda.tenant_id)
    assert completo["taxas_ifood_pendentes"] is False
    assert completo["lucro"] == 27.4
    assert completo["itens"][0]["lucro"] == 27.4
    assert completo["taxa_cartao"] == 0
    recebido.clear()
    recebido.update(financial(commission=7.5, payment=0, complete=True, revision=3))
    revisado = get_or_build_venda_rentabilidade_snapshot(venda, db, venda.tenant_id)
    assert revisado["lucro"] == 26.4  # Substitui 6.50; nao acumula 6.50 + 7.50.
    recebido.clear()  # Uma revisao sem prova nao reutiliza o lucro anterior.
    assert (
        get_or_build_venda_rentabilidade_snapshot(venda, db, venda.tenant_id)["lucro"]
        is None
    )
    assert venda.rentabilidade_snapshot == original
    assert db.flushes == 0


def test_taxa_local_e_comissao_interna_nao_se_confundem_com_ifood():
    venda = sale()
    base = build(venda)
    base.update(taxa_cartao_local=1, comissao=2)
    base["itens"][0]["comissao"] = 2
    resultado = aplicar_pendencia_ifood(
        venda, base, financial=financial(commission=6.5, payment=0, complete=True)
    )
    assert resultado["taxa_cartao"] == 1
    assert resultado["taxa_ifood"] == 6.5
    assert resultado["comissao"] == 2
    assert resultado["lucro"] == 24.4
    assert resultado["itens"][0]["lucro"] == 24.4


def test_overlay_completo_nunca_e_persistido_como_base(monkeypatch):
    venda = sale()
    db = NoQueries()
    monkeypatch.setattr(
        "app.services.ifood_rentabilidade_contexto.carregar_financial_das_vendas",
        lambda *_: {1: financial(commission=6.5, payment=0, complete=True)},
    )
    resultado = get_or_build_venda_rentabilidade_snapshot(
        venda,
        db,
        venda.tenant_id,
        impostos_percentual=0,
        formas_pagamento_map={},
        custo_campanha=0,
        cupom_desconto=0,
        comissao_total=0,
        taxa_operacional_entrega=0,
        estoque_custos_por_produto={},
    )
    assert resultado["lucro"] == 27.4
    assert venda.rentabilidade_snapshot["lucro"] is None
    assert venda.rentabilidade_snapshot["taxa_cartao_local"] == 0
    assert db.flushes == 1


def test_simulacao_explicitamente_marcada_nao_libera_lucro_real():
    venda = sale()
    resultado = aplicar_pendencia_ifood(
        venda,
        build(venda),
        financial=financial(commission=6.5, payment=0, complete=True, simulated=True),
    )
    assert resultado["ifood_financial"]["simulated"] is True
    assert resultado["lucro"] is None
    assert resultado["taxa_ifood"] == 6.5


def test_rateio_das_taxas_fecha_centavos_sem_duplicar_valor():
    venda = sale()
    base = build(venda)
    base.update(venda_bruta=3, taxa_loja=0, custo_produtos=0)
    item = base["itens"][0]
    base["itens"] = [
        {**item, "venda_bruta": 1, "taxa_loja": 0, "custo_total": 0} for _ in range(3)
    ]
    resultado = aplicar_pendencia_ifood(
        venda, base, financial=financial(commission=1, payment=0, complete=True)
    )
    assert resultado["lucro"] == 2
    assert [item["taxa_ifood"] for item in resultado["itens"]] == [0.33, 0.33, 0.34]
    assert sum(item["lucro"] for item in resultado["itens"]) == 2


def test_relatorio_misto_preserva_taxa_pagamento_conhecida_e_outra_pendente(
    monkeypatch,
):
    vendas = [sale(), sale(sale_id=2, canal="loja_fisica", gateway_fee=0)]
    monkeypatch.setattr(report, "carregar_vendas_relatorio", lambda **_: vendas)
    monkeypatch.setattr(
        report, "carregar_financial_das_vendas", lambda *_: {1: financial(payment=0)}
    )
    contexto = {
        "impostos_percentual_global": 0,
        **{
            key: {}
            for key in (
                "comissao_total_por_venda",
                "formas_pagamento_map",
                "cashback_por_venda",
                "cupons_por_venda",
                "entregadores_map",
                "estoque_custos_por_venda",
            )
        },
    }
    monkeypatch.setattr(
        report, "carregar_contexto_relatorio_vendas", lambda **_: contexto
    )
    monkeypatch.setattr(
        report, "_enriquecer_itens_promocionais", lambda _, itens: itens
    )
    resultado = report.montar_relatorio_vendas(
        data_inicio="2026-10-24",
        data_fim="2026-10-24",
        canal_venda=None,
        db=NoQueries(),
        tenant_id="tenant-dev",
    )
    assert resultado["resumo"]["taxa_cartao_total"] == 0
    assert resultado["resumo"]["taxa_ifood_total"] is None
    assert resultado["resumo"]["lucro_total"] is None
    assert resultado["resumo"]["ifood_financial_resumo"]["charges"][0]["amount"] == 0


def test_taxa_ifood_chegada_depois_nao_vira_credito_local_no_cache_legado():
    venda = sale()
    base = build(venda)
    base.pop("taxa_cartao_local")
    base.pop("ifood_financial")
    base["taxa_cartao"] = 0
    venda.pagamentos[0].gateway_fee_amount = 3
    resultado = aplicar_pendencia_ifood(
        venda, base, financial=financial(commission=6.5, payment=3, complete=True)
    )
    assert resultado["taxa_cartao_local"] == 0
    assert resultado["lucro"] == 24.4


def test_subtotal_conta_pedidos_sem_perder_linhas_legitimas_repetidas():
    from app.services.rentabilidade_pendencias import resumir_financial_ifood

    dados = financial(commission=2, payment=0, complete=True)
    dados["charges"].append(deepcopy(dados["charges"][0]))
    dados.update(fee_known_total=4, fee_total=4)
    resumo = resumir_financial_ifood([dados])
    comissao = next(c for c in resumo["charges"] if c["code"] == "ORDER_COMMISSION")
    assert comissao["amount"] == 4
    assert comissao["orders"] == 1


def test_taxa_local_desconhecida_nao_vira_zero_no_segundo_overlay():
    venda = sale()
    base = build(venda)
    base.pop("taxa_cartao_local")
    base.pop("ifood_financial")
    venda.pagamentos = []
    base["taxa_cartao"] = 5
    recebido = financial(commission=6.5, payment=0, complete=True)
    primeiro = aplicar_pendencia_ifood(venda, base, financial=recebido)
    segundo = aplicar_pendencia_ifood(venda, primeiro, financial=recebido)
    assert primeiro["taxa_cartao_local"] is None
    assert segundo["taxa_cartao_local"] is None
    assert segundo["lucro"] is None
