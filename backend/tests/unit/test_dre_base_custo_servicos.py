from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app import dre_base_routes
from app.dre_canais.base import CANAIS_CONFIG
from app.dre_calculos import calcular_cmv, calcular_custo_servicos
from app.vendas_models import Venda, VendaItem


def test_custo_mercadorias_e_servicos_sao_separados():
    produto = SimpleNamespace(
        tipo="produto", quantidade=2, produto=SimpleNamespace(preco_custo=5)
    )
    servico = SimpleNamespace(
        tipo="servico", quantidade=1, produto=SimpleNamespace(preco_custo=8)
    )
    db = MagicMock()
    consultas = {Venda: [SimpleNamespace(id=10)], VendaItem: [produto, servico]}
    db.query.side_effect = lambda modelo: _consulta_com_resultado(consultas[modelo])

    assert calcular_cmv(db, 10, 2026, "tenant-teste") == Decimal("10")
    assert calcular_custo_servicos(db, 10, 2026, "tenant-teste") == Decimal("8")


def _consulta_com_resultado(resultado):
    consulta = MagicMock()
    consulta.filter.return_value.all.return_value = resultado
    return consulta


def test_dre_base_consulta_fonte_canonica_em_todos_os_canais(monkeypatch):
    chamadas = []
    resposta = object()

    def adaptador(**kwargs):
        chamadas.append(kwargs)
        return resposta

    monkeypatch.setattr(dre_base_routes, "_dre_para_exportacao", adaptador)
    db = object()
    usuario = (object(), "tenant-teste")

    assert (
        dre_base_routes.gerar_dre(ano=2026, mes=10, db=db, user_and_tenant=usuario)
        is resposta
    )
    assert chamadas == [
        {
            "ano": 2026,
            "mes": 10,
            "mes_inicial": 10,
            "data_final": None,
            "canais": ",".join(CANAIS_CONFIG),
            "db": db,
            "user_and_tenant": usuario,
        }
    ]
