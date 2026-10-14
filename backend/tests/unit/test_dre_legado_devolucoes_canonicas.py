"""O endpoint legado e o canônico compartilham os números de competência."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import dre_base_routes
from app.dre_canais import agregacao, routes
from app.dre_canais.base import CANAIS_CONFIG, _novo_canal
from app.dre_schemas import DREResponse


@pytest.mark.parametrize(
    ("mes", "receita", "devolucoes", "cmv", "lucro_bruto"),
    [
        (9, 100, 0, 60, 40),
        (10, 0, 40, -24, -16),
    ],
)
def test_dre_legada_conciliada_com_canonica_no_mes_da_venda_e_da_devolucao(
    monkeypatch, mes, receita, devolucoes, cmv, lucro_bruto
):
    evento = SimpleNamespace(
        id=1,
        venda_id=123,
        data_competencia=date(2026, 10, 5),
        canal="loja_fisica",
        forma_estorno="dinheiro",
        motivo="Teste",
        valor_devolvido=Decimal("40.00"),
        custo_produtos_estornado=Decimal("24.00"),
        custo_servicos_estornado=Decimal("0"),
        custo_pendente=False,
        itens=[],
    )

    def vendas_do_mes(_db, mes_consulta, *_args, **_kwargs):
        if mes_consulta != 9:
            return {}
        canal = _novo_canal()
        canal["receita_produtos"] = Decimal("100")
        canal["cmv"] = Decimal("60")
        return {"loja_fisica": canal}

    monkeypatch.setattr(routes, "obter_vendas_por_canal", vendas_do_mes)
    monkeypatch.setattr(
        agregacao,
        "_devolucoes_periodo_query",
        lambda _db, _tenant, inicio, _fim: SimpleNamespace(
            all=lambda: [evento] if inicio.month == 10 else []
        ),
    )
    for nome in (
        "agregar_contas_receber_manuais_por_canal",
        "agregar_contas_pagar_por_canal",
        "agregar_fretes_sobre_compras",
    ):
        monkeypatch.setattr(routes, nome, lambda *_args, **_kwargs: None)

    parametros = {
        "ano": 2026,
        "mes": mes,
        "db": object(),
        "user_and_tenant": (object(), "tenant-teste"),
    }
    canonica = routes.gerar_dre_por_canais(
        **parametros,
        mes_inicial=mes,
        data_final=None,
        canais=",".join(CANAIS_CONFIG),
    )
    legada = dre_base_routes.gerar_dre(**parametros)

    assert isinstance(legada, DREResponse)
    assert legada.mes == mes
    assert legada.ano == 2026
    assert legada.receita_bruta == Decimal(receita)
    assert legada.devolucoes == Decimal(devolucoes)
    assert legada.cmv == Decimal(cmv)
    assert legada.lucro_bruto == Decimal(lucro_bruto)
    for campo in (
        "receita_bruta",
        "deducoes_total",
        "devolucoes",
        "receita_liquida",
        "cmv",
        "lucro_bruto",
        "lucro_liquido",
    ):
        assert getattr(legada, campo) == Decimal(str(canonica.totais[campo]))
    assert set(legada.model_dump()) == set(DREResponse.model_fields)
