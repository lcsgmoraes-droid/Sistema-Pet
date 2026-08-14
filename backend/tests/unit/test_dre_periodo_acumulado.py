from datetime import date, datetime

from app.dre_canais import detalhes, routes
from app.dre_canais.base import _novo_canal, _periodo_label_intervalo, _periodo_meses


def test_periodo_acumulado_termina_no_dia_informado():
    inicio, fim_exclusivo = _periodo_meses(
        1,
        8,
        2026,
        data_final=date(2026, 8, 14),
    )

    assert inicio == datetime(2026, 1, 1)
    assert fim_exclusivo == datetime(2026, 8, 15)
    assert (
        _periodo_label_intervalo(1, 8, 2026, date(2026, 8, 14))
        == "01/01/2026 a 14/08/2026"
    )


def test_endpoint_dre_repassa_intervalo_anual_para_todos_os_calculos(monkeypatch):
    chamadas = []

    def obter_vendas(db, mes, ano, tenant_id, **kwargs):
        chamadas.append(("vendas", mes, ano, tenant_id, kwargs))
        return {"loja_fisica": _novo_canal()}

    def agregar_contas(db, mes, ano, tenant_id, dados_canais, **kwargs):
        chamadas.append(("contas", mes, ano, tenant_id, kwargs))

    def agregar_fretes(db, mes, ano, tenant_id, dados_canais, **kwargs):
        chamadas.append(("fretes", mes, ano, tenant_id, kwargs))

    monkeypatch.setattr(routes, "obter_vendas_por_canal", obter_vendas)
    monkeypatch.setattr(routes, "agregar_contas_pagar_por_canal", agregar_contas)
    monkeypatch.setattr(routes, "agregar_fretes_sobre_compras", agregar_fretes)

    resposta = routes.gerar_dre_por_canais(
        ano=2026,
        mes=8,
        mes_inicial=1,
        data_final=date(2026, 8, 14),
        canais="loja_fisica",
        db=object(),
        user_and_tenant=(object(), "tenant-teste"),
    )

    assert resposta.periodo == "01/01/2026 a 14/08/2026"
    assert resposta.mes_inicial == 1
    assert resposta.mes == 8
    assert resposta.data_final == date(2026, 8, 14)
    assert [chamada[0] for chamada in chamadas] == ["vendas", "contas", "fretes"]
    for _, mes, ano, tenant_id, kwargs in chamadas:
        assert (mes, ano, tenant_id) == (8, 2026, "tenant-teste")
        assert kwargs == {
            "mes_inicial": 1,
            "data_final": date(2026, 8, 14),
        }


def test_detalhamento_mantem_o_mesmo_periodo_acumulado(monkeypatch):
    chamada = {}

    def buscar_detalhes(db, mes, ano, tenant_id, canal, campo, **kwargs):
        chamada.update(
            {
                "mes": mes,
                "ano": ano,
                "tenant_id": tenant_id,
                "canal": canal,
                "campo": campo,
                **kwargs,
            }
        )
        return []

    monkeypatch.setattr(detalhes, "_detalhes_vendas_campo", buscar_detalhes)

    resposta = detalhes.detalhar_linha_dre_por_canal(
        ano=2026,
        mes=8,
        mes_inicial=1,
        data_final=date(2026, 8, 14),
        canal="loja_fisica",
        campo="receita_produtos",
        page=1,
        page_size=30,
        db=object(),
        user_and_tenant=(object(), "tenant-teste"),
    )

    assert resposta.periodo == "01/01/2026 a 14/08/2026"
    assert resposta.total == 0
    assert resposta.total_itens == 0
    assert chamada == {
        "mes": 8,
        "ano": 2026,
        "tenant_id": "tenant-teste",
        "canal": "loja_fisica",
        "campo": "receita_produtos",
        "mes_inicial": 1,
        "data_final": date(2026, 8, 14),
    }
