from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

import app.produtos_models  # noqa: F401 - registra relacionamentos de Produto no mapper
from app.api.endpoints.rotas_entrega_core_routes import (
    _hidratar_resumo_financeiro_rota,
    aplicar_filtros_ordenacao_rotas,
)
from app.rotas_entrega_models import RotaEntrega


def test_filtros_do_historico_incluem_legado_e_ordenam_por_entregas_reais():
    query = aplicar_filtros_ordenacao_rotas(
        Session().query(RotaEntrega),
        tenant_id=7,
        data_inicio=date(2026, 7, 1),
        data_fim=date(2026, 7, 17),
        busca="Maria",
        ordenar_por="entregas",
        direcao="desc",
    )

    sql = str(
        query.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    assert "rotas_entrega.endereco_destino ILIKE" in sql
    assert "vendas.numero_venda ILIKE" in sql
    assert "rotas_entrega.venda_id IS NOT NULL" in sql
    assert "2026-07-18 00:00:00" in sql
    assert "DESC" in sql


def test_resumo_preserva_taxa_historica_snapshot_da_rota():
    rota = SimpleNamespace(
        taxa_entrega_cliente=Decimal("22.50"),
        custo_real=Decimal("30"),
        custo_moto=Decimal("8"),
        total_entregas=2,
        data_inicio=None,
        data_conclusao=None,
    )
    vendas = [
        SimpleNamespace(total=Decimal("100"), taxa_entrega=Decimal("8")),
        SimpleNamespace(total=Decimal("150"), taxa_entrega=Decimal("9")),
    ]

    _hidratar_resumo_financeiro_rota(rota, vendas)

    assert rota.valor_total_vendas == Decimal("250")
    assert rota.taxa_total_entregas == Decimal("22.50")
    assert rota.custo_entregador == Decimal("22")
    assert rota.custo_por_entrega == Decimal("15.00")
