"""O desconto de um produto nao muda o valor dos demais produtos."""

from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.venda_rentabilidade_snapshot_service import (
    build_venda_rentabilidade_snapshot,
    get_or_build_venda_rentabilidade_snapshot,
)
from app.services.venda_descontos import ratear_descontos_venda, resumo_descontos_venda
from app.vendas.devolucao_valores import ratear_valor_pago_por_item
from app.vendas.regras import calcular_totais_venda
from app.vendas.regras import resolver_descontos_atualizacao
from app.vendas.schemas import CriarVendaRequest


def _venda(*, global_valor=9, cupom=9):
    itens = [
        SimpleNamespace(
            id=1,
            quantidade=1,
            preco_unitario=50,
            desconto_item=10,
            subtotal=40,
            produto_id=10,
            produto=SimpleNamespace(nome="A", preco_custo=0),
        ),
        SimpleNamespace(
            id=2,
            quantidade=1,
            preco_unitario=50,
            desconto_item=0,
            subtotal=50,
            produto_id=20,
            produto=SimpleNamespace(nome="B", preco_custo=0),
        ),
    ]
    return SimpleNamespace(
        id=1,
        numero_venda="QA-DESCONTO",
        status="finalizada",
        data_venda=None,
        cliente=None,
        itens=itens,
        pagamentos=[],
        subtotal=90,
        desconto_venda_valor=global_valor,
        desconto_valor=10 + global_valor + cupom,
        cupom_discount_applied=cupom,
        cupom_code="QA" if cupom else None,
        taxa_entrega=10,
        valor_taxa_entregador=0,
        tem_entrega=False,
        entregador_id=None,
        total=100 - 10 - global_valor - cupom + 10,
    )


def _snapshot(venda):
    return build_venda_rentabilidade_snapshot(
        venda,
        SimpleNamespace(),
        "tenant-qa",
        impostos_percentual=0,
        formas_pagamento_map={},
        custo_campanha=venda.cupom_discount_applied,
        cupom_desconto=venda.cupom_discount_applied,
        comissao_total=0,
        estoque_custos_por_produto={},
    )


def test_totais_nao_confiam_no_subtotal_cliente_e_separam_di_g_c():
    venda = _venda()
    venda.itens[0].subtotal = 1  # subtotal recebido inconsistente
    totais = calcular_totais_venda(
        venda.itens, 999, 99, 10, desconto_venda_valor=9, cupom_discount_applied=9
    )
    assert totais == {"subtotal": 90, "desconto_valor": 28, "total": 82}


def test_desconto_exclusivo_do_item_nao_vaza_para_outra_linha():
    partes = ratear_descontos_venda(_venda(global_valor=0, cupom=0))
    assert [parte["total"] for parte in partes] == [Decimal("10"), Decimal("0")]
    snapshot = _snapshot(_venda(global_valor=0, cupom=0))
    assert [item["desconto"] for item in snapshot["itens"]] == [10, 0]
    assert snapshot["venda_bruta"] == 100
    assert snapshot["venda_liquida"] == 100  # 90 produtos + 10 frete


def test_so_desconto_global_e_cupom_sao_rateados_sobre_liquidos():
    venda = _venda()
    partes = ratear_descontos_venda(venda)
    assert [parte["desconto_item"] for parte in partes] == [10, 0]
    assert [parte["desconto_venda"] for parte in partes] == [4, 5]
    assert [parte["cupom"] for parte in partes] == [4, 5]
    assert [parte["total"] for parte in partes] == [18, 10]
    snapshot = _snapshot(venda)
    assert snapshot["desconto"] == 19
    assert snapshot["cupom_desconto"] == snapshot["custo_campanha"] == 9
    assert snapshot["venda_liquida"] == 82
    assert [item["desconto"] for item in snapshot["itens"]] == [14, 5]
    assert [item["campanha"] for item in snapshot["itens"]] == [4, 5]
    assert sum(item["valor_liquido"] for item in snapshot["itens"]) == 82
    assert resumo_descontos_venda(venda) == {
        "desconto_itens_valor": 10,
        "desconto_venda_valor": 9,
        "desconto_origem_legado": False,
    }


def test_aplicar_remover_reaplicar_cupom_preserva_di_de_cada_item():
    venda = _venda()
    antes = [(item.desconto_item, item.subtotal) for item in venda.itens]
    for cupom in [9, 0, 9]:
        venda.cupom_discount_applied = cupom
        totais = calcular_totais_venda(
            venda.itens, 0, 0, 10, desconto_venda_valor=9, cupom_discount_applied=cupom
        )
        venda.total = totais["total"]
        venda.desconto_valor = totais["desconto_valor"]
        assert [(item.desconto_item, item.subtotal) for item in venda.itens] == antes
        assert (
            sum(parte["total"] for parte in ratear_descontos_venda(venda)) == 19 + cupom
        )


def test_devolucao_e_snapshot_usam_mesmo_rateio_de_centavos_independente_da_ordem():
    venda = _venda(global_valor=0, cupom=2)
    venda.itens = [
        SimpleNamespace(
            id=i, quantidade=1, preco_unitario=1, desconto_item=0, subtotal=1
        )
        for i in [3, 1, 2]
    ]
    venda.desconto_valor = 2
    venda.total = 11  # 1 produtos + 10 frete
    partes = ratear_descontos_venda(venda)
    pagos = ratear_valor_pago_por_item(venda, venda.itens)
    assert pagos == {1: Decimal("0.34"), 2: Decimal("0.33"), 3: Decimal("0.33")}
    assert {
        item.id: Decimal("1") - parte["total"]
        for item, parte in zip(venda.itens, partes)
    } == pagos
    assert sum(parte["cupom"] for parte in partes) == 2


@pytest.mark.parametrize(
    "global_valor,cupom,di",
    [(-1, 0, 10), (0, -1, 10), (91, 0, 10), (0, 91, 10), (0, 0, -1), (0, 0, 51)],
)
def test_descontos_invalidos_nao_criam_totais_negativos(global_valor, cupom, di):
    venda = _venda()
    venda.itens[0].desconto_item = di
    with pytest.raises(ValueError):
        calcular_totais_venda(
            venda.itens,
            0,
            0,
            10,
            desconto_venda_valor=global_valor,
            cupom_discount_applied=cupom,
        )


def test_legado_mantem_numeros_e_nao_afirma_origem_manual_dos_itens():
    venda = _venda(global_valor=0, cupom=0)
    venda.desconto_venda_valor = None
    antes = deepcopy(venda)
    partes = ratear_descontos_venda(venda)
    assert [parte["total"] for parte in partes] == [10, 0]
    assert all(parte["legado"] and parte["desconto_venda"] is None for parte in partes)
    assert venda.total == antes.total
    assert [item.subtotal for item in venda.itens] == [
        item.subtotal for item in antes.itens
    ]
    assert resumo_descontos_venda(venda)["desconto_origem_legado"] is True


def test_snapshot_historico_v5_permanece_congelado_sem_reprecificar():
    venda = _venda()
    venda.desconto_venda_valor = None
    original = {
        "snapshot_version": 5,
        "taxa_cartao": 0,
        "venda_liquida": 82,
        "lucro": 30,
        "itens": [],
    }
    venda.rentabilidade_snapshot = original
    assert (
        get_or_build_venda_rentabilidade_snapshot(venda, SimpleNamespace(), "tenant-qa")
        == original
    )


def _dados(**extras):
    return CriarVendaRequest(
        itens=[
            dict(
                tipo="produto",
                quantidade=1,
                preco_unitario=50,
                desconto_item=10,
                subtotal=40,
            )
        ],
        **extras,
    )


def test_cliente_antigo_omitindo_g_c_preserva_descontos_canonicos_existentes():
    venda = _venda()
    assert resolver_descontos_atualizacao(venda, _dados()) == {
        "desconto_venda_valor": 9,
        "cupom_discount_applied": 9,
        "cupom_code": "QA",
    }


def test_cliente_pode_remover_cupom_explicitamente_sem_apagar_g_ou_di():
    venda = _venda()
    assert resolver_descontos_atualizacao(venda, _dados(cupom_code=None)) == {
        "desconto_venda_valor": 9,
        "cupom_discount_applied": 0,
        "cupom_code": None,
    }
    assert venda.itens[0].desconto_item == 10


def test_null_explicito_mantem_contrato_legado_sem_inferir_origens():
    venda = _venda()
    assert resolver_descontos_atualizacao(venda, _dados(desconto_venda_valor=None)) == {
        "desconto_venda_valor": None,
        "cupom_discount_applied": None,
        "cupom_code": None,
    }


def test_cupons_detalhes_isola_tenant_e_cliente_preservando_ordem_e_tipo(
    tenant_context,
):
    from app.campaigns.models import Coupon, CouponTypeEnum, CouponStatusEnum
    from app.vendas.cupons_detalhes import carregar_cupons_detalhes_venda

    tenant = uuid4()
    tenant_context(tenant)
    engine = create_engine("sqlite://")
    Coupon.__table__.create(engine)
    with Session(engine) as db:
        db.execute(
            Coupon.__table__.insert(),
            [
                dict(
                    id=1,
                    tenant_id=tenant,
                    code="FIXO",
                    customer_id=1,
                    coupon_type=CouponTypeEnum.fixed,
                    discount_value=5,
                    discount_percent=None,
                    status=CouponStatusEnum.used,
                ),
                dict(
                    id=2,
                    tenant_id=tenant,
                    code="PERCENT",
                    customer_id=None,
                    coupon_type=CouponTypeEnum.percent,
                    discount_value=None,
                    discount_percent=10,
                    status=CouponStatusEnum.active,
                ),
                dict(
                    id=3,
                    tenant_id=tenant,
                    code="ALHEIO",
                    customer_id=2,
                    coupon_type=CouponTypeEnum.fixed,
                    discount_value=100,
                    discount_percent=None,
                    status=CouponStatusEnum.active,
                ),
                dict(
                    id=4,
                    tenant_id=uuid4(),
                    code="OUTRO-TENANT",
                    customer_id=1,
                    coupon_type=CouponTypeEnum.fixed,
                    discount_value=200,
                    discount_percent=None,
                    status=CouponStatusEnum.active,
                ),
            ],
        )
        db.commit()
        venda = SimpleNamespace(
            tenant_id=tenant,
            cliente_id=1,
            cupom_code="PERCENT,FIXO,ALHEIO,OUTRO-TENANT",
        )
        assert carregar_cupons_detalhes_venda(db, venda, tenant) == [
            {
                "code": "PERCENT",
                "coupon_type": "percent",
                "discount_value": None,
                "discount_percent": 10,
            },
            {
                "code": "FIXO",
                "coupon_type": "fixed",
                "discount_value": 5,
                "discount_percent": None,
            },
        ]
        assert carregar_cupons_detalhes_venda(db, venda, uuid4()) == []
    engine.dispose()


def test_relatorio_categoria_e_lista_financeira_mantem_di_no_produto(monkeypatch):
    from app import relatorio_vendas_builder as relatorio

    venda = _venda()
    venda.data_venda = datetime(2026, 10, 9, 12)
    venda.user_id = 1
    venda.usuario = SimpleNamespace(nome="Operador")
    venda.canal = "loja_fisica"
    venda.loja_origem = None
    for campo in ("nfe_tipo", "nfe_status", "nfe_numero", "nfe_chave", "nfe_bling_id"):
        setattr(venda, campo, None)
    for item in venda.itens:
        item.produto.id = item.produto_id
        item.produto.categoria = SimpleNamespace(nome=item.produto.nome)
        item.produto.marca = None
    monkeypatch.setattr(relatorio, "carregar_vendas_relatorio", lambda **kw: [venda])
    monkeypatch.setattr(
        relatorio,
        "carregar_contexto_relatorio_vendas",
        lambda **kw: {
            "impostos_percentual_global": 0,
            "comissao_total_por_venda": {},
            "formas_pagamento_map": {},
            "cashback_por_venda": {},
            "cupons_por_venda": {},
            "entregadores_map": {},
            "estoque_custos_por_venda": {},
        },
    )
    resultado = relatorio.montar_relatorio_vendas(
        data_inicio="2026-10-09",
        data_fim="2026-10-09",
        canal_venda=None,
        db=SimpleNamespace(flush=lambda: None),
        tenant_id="tenant-qa",
    )
    grupos = {grupo["grupo"]: grupo for grupo in resultado["vendas_por_grupo"]}
    assert grupos["A"]["desconto"] == 18
    assert grupos["B"]["desconto"] == 10
    categorias = {
        categoria["categoria"]: categoria
        for categoria in resultado["produtos_detalhados"]
    }
    assert categorias["A"]["total_desconto"] == 18
    assert categorias["B"]["total_desconto"] == 10
    financeira = resultado["lista_vendas"][0]
    assert financeira["desconto_itens_valor"] == 10
    assert financeira["desconto_venda_valor"] == 9
    assert financeira["cupom_discount_applied"] == 9
    assert [item["desconto_item"] for item in financeira["itens"]] == [10, 0]


@pytest.mark.parametrize(
    "g,c,esperados",
    [(0, 0, [40, 50]), (9, 9, [32, 40]), (0.75, 0, [3.00]), (3.75, 0, [0.00])],
)
def test_comissao_recebe_liquido_do_proprio_item_sem_ratear_di(
    monkeypatch, tenant_context, g, c, esperados
):
    from app import comissoes_geracao_service as comissoes

    tenant = uuid4()
    tenant_context(tenant)
    chamadas = []
    gravados = []
    fracionado = len(esperados) == 1
    linhas = (
        [(1, 10, 0.375, 9.99, 3.75, 0, "A", 0, 0)]
        if fracionado
        else [
            (1, 10, 1, 50, 40, 0, "A", 0, 10),
            (2, 20, 1, 50, 50, 0, "B", 0, 0),
        ]
    )
    subtotal = 3.75 if fracionado else 90
    di = 0 if fracionado else 10

    def resultado(row=None, rows=None):
        return SimpleNamespace(fetchone=lambda: row, fetchall=lambda: rows or [])

    def executar(db, sql, params, **kw):
        assert kw["tenant_id"] == tenant
        if "FROM venda_itens" in sql:
            return resultado(rows=linhas)
        if "FROM vendas" in sql:
            return resultado(
                row=(
                    1,
                    subtotal - g - c,
                    "finalizada",
                    di + g + c,
                    0,
                    False,
                    datetime(2026, 10, 9),
                    tenant,
                    None,
                    g,
                    c,
                )
            )
        if "COUNT(*)" in sql:
            return resultado(row=(0,))
        if "FROM formas_pagamento" in sql:
            return resultado(row=(0, "PIX"))
        if "INSERT INTO comissoes_itens" in sql:
            gravados.append(params)
            return resultado()
        raise AssertionError(sql)

    def calcular(**kw):
        chamadas.append(kw)
        liquido = float(kw["valor_liquido_item"])
        return {
            "base_calculo": liquido,
            "valor_comissao": liquido / 10,
            "tipo_calculo": "percentual",
            "percentual": 10,
            "valor_liquido": liquido,
            "custo_item": 0,
        }

    monkeypatch.setattr(comissoes, "execute_tenant_safe", executar)
    monkeypatch.setattr(
        comissoes,
        "buscar_configuracao_comissao",
        lambda *a, **kw: {"comissao_venda_parcial": True},
    )
    monkeypatch.setattr(comissoes, "calcular_comissao_item", calcular)
    monkeypatch.setattr(
        "app.comissoes_provisao.provisionar_comissoes_venda",
        lambda **kw: {"success": False, "message": "fixture"},
    )
    query = SimpleNamespace(
        filter=lambda *a: SimpleNamespace(
            first=lambda: SimpleNamespace(aliquota_simples_vigente=0)
        )
    )
    db = SimpleNamespace(
        query=lambda *a: query, commit=lambda: None, rollback=lambda: None
    )
    resultado_final = comissoes.gerar_comissoes_venda(
        venda_id=1,
        funcionario_id=1,
        forma_pagamento="PIX",
        tenant_id=tenant,
        db=db,
    )
    assert resultado_final["success"] is True
    assert [float(kw["valor_liquido_item"]) for kw in chamadas] == esperados
    assert [row["valor_venda"] for row in gravados] == esperados


@pytest.mark.parametrize("g,esperados", [(9, [32, 40]), (0.75, [3.00]), (3.75, [0.00])])
def test_analise_pdv_usa_di_g_c_frete_e_mesma_base_de_comissao(
    monkeypatch, g, esperados
):
    from app.formas_pagamento_routes_parts.analise_routes import analisar_venda
    from app.formas_pagamento_routes_parts.schemas import AnaliseVendaRequest
    from app.produtos_models import Produto

    fracionado = len(esperados) == 1
    dados = AnaliseVendaRequest(
        items=[dict(produto_id=10, quantidade=0.375, preco_venda=9.99)]
        if fracionado
        else [
            dict(produto_id=10, quantidade=1, preco_venda=50, desconto_item=10),
            dict(produto_id=20, quantidade=1, preco_venda=50),
        ],
        desconto=999,
        desconto_venda_valor=g,
        cupom_discount_applied=0 if fracionado else 9,
        taxa_entrega=0 if fracionado else 10,
        vendedor_id=1,
    )
    recebidos = []

    def query(model):
        valor = (
            SimpleNamespace(preco_custo=0, nome="Produto") if model is Produto else None
        )
        return SimpleNamespace(filter=lambda *a: SimpleNamespace(first=lambda: valor))

    def calculo(**kw):
        recebidos.append(kw["valor_liquido_item"])
        return {
            "valor_comissao": float(kw["valor_liquido_item"]) / 10,
            "percentual": 10,
        }

    monkeypatch.setattr(
        "app.comissoes_service.buscar_configuracao_comissao",
        lambda *a, **kw: {"percentual": 10},
    )
    monkeypatch.setattr("app.comissoes_service.calcular_comissao_item", calculo)
    resposta = analisar_venda.__wrapped__(
        dados=dados,
        db=SimpleNamespace(query=query),
        user_and_tenant=(SimpleNamespace(id=1), uuid4()),
    )
    assert resposta.composicao["total_produtos"] == (3.75 if fracionado else 100)
    assert resposta.composicao["desconto"] == (g if fracionado else 28)
    assert resposta.composicao["subtotal"] == (sum(esperados) if fracionado else 82)
    assert resposta.composicao["desconto_itens_valor"] == (0 if fracionado else 10)
    assert (
        (
            resposta.composicao["desconto_venda_valor"]
            == resposta.composicao["cupom_discount_applied"]
            == 9
        )
        if not fracionado
        else resposta.composicao["desconto_venda_valor"] == g
    )
    assert recebidos == [Decimal(str(valor)) for valor in esperados]
    assert resposta.deducoes["comissao"]["valor"] == pytest.approx(sum(esperados) / 10)


@pytest.mark.parametrize(
    "qty,preco,qty_salva,preco_salvo,total",
    [(2, 1.005, 2, 1.01, 2.02), (0.33333, 100, 0.333, 100, 33.30)],
)
def test_precisao_canonica_corresponde_a_que_sera_persistida(
    qty, preco, qty_salva, preco_salvo, total
):
    from app.formas_pagamento_routes_parts.schemas import AnaliseVendaRequest

    dados = CriarVendaRequest(
        desconto_venda_valor=0,
        itens=[
            dict(tipo="produto", quantidade=qty, preco_unitario=preco, subtotal=999)
        ],
    )
    item = dados.itens[0]
    assert item.quantidade == qty_salva
    assert item.preco_unitario == preco_salvo
    assert item.subtotal == total
    assert (
        calcular_totais_venda(dados.itens, 0, 0, 0, desconto_venda_valor=0)["total"]
        == total
    )
    analise = AnaliseVendaRequest(
        items=[dict(produto_id=1, quantidade=qty, preco_venda=preco)],
        desconto_venda_valor=0,
    )
    assert analise.items[0].quantidade == qty_salva
    assert analise.items[0].preco_venda == preco_salvo


@pytest.mark.parametrize(
    "qty,preco,g",
    [(0.0004, 10, 0), (1e30, 1, 0), (1, 1e30, 0), (1, 10, 1e30), (1, float("nan"), 0)],
)
def test_canonico_rejeita_zero_apos_arredondamento_e_limites_do_decimal(qty, preco, g):
    with pytest.raises(ValueError):
        CriarVendaRequest(
            desconto_venda_valor=g,
            itens=[
                dict(tipo="produto", quantidade=qty, preco_unitario=preco, subtotal=0)
            ],
        )
