from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import contas_pagar_routes
from app.financeiro.contas_pagar_analise_routes import (
    _aplicar_grupo_detalhe,
    _referencia_origem,
)
from app.financeiro_models import ContaPagar


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_contas_pagar_registra_rota_de_analise_de_abertos():
    from app.financeiro import contas_pagar_analise_routes

    paths = {route.path for route in contas_pagar_routes.router.routes}

    assert "/contas-pagar/analise-abertos" in paths
    assert "/contas-pagar/analise-abertos/detalhes" in paths
    assert (
        contas_pagar_routes.analisar_contas_pagar_abertas
        is contas_pagar_analise_routes.analisar_contas_pagar_abertas
    )
    assert (
        contas_pagar_routes.detalhar_contas_pagar_abertas
        is contas_pagar_analise_routes.detalhar_contas_pagar_abertas
    )


def test_analise_contas_pagar_expoe_origem_dos_lancamentos_por_grupo():
    source = read_repo("backend/app/financeiro/contas_pagar_analise_routes.py")

    assert 'router.get("/analise-abertos/detalhes")' in source
    assert 'pattern="^(todos|periodo|mes|fornecedor|tipo_despesa|origem|tipo_custo)$"' in source
    assert "_aplicar_filtros_analise" in source
    assert "_aplicar_grupo_detalhe" in source
    assert '"saldo_aberto": saldo_aberto' in source
    assert '"origem_referencia": _referencia_origem' in source
    assert '"origem_lancamento_label"' in read_repo(
        "backend/app/financeiro/contas_pagar_origem.py"
    )
    assert 'page_size: int = Query(30, ge=1, le=100)' in source


@pytest.mark.parametrize(
    ("grupo", "grupo_id"),
    (
        ("todos", None),
        ("fornecedor", "123"),
        ("fornecedor", "sem_fornecedor"),
        ("tipo_despesa", "456"),
        ("tipo_despesa", "sem_tipo"),
        ("origem", "nota_entrada"),
        ("origem", "caixa_pdv"),
        ("origem", "manual"),
        ("tipo_custo", "fixo"),
        ("tipo_custo", "variavel"),
        ("tipo_custo", "sem_tipo_custo"),
        ("periodo", "vencido"),
        ("periodo", "hoje"),
        ("periodo", "amanha"),
        ("periodo", "proximos_7_dias"),
        ("periodo", "mes_atual"),
        ("periodo", "proximos_12_meses"),
        ("mes", "2026-07"),
    ),
)
def test_grupos_de_detalhe_geram_consultas_validas(grupo, grupo_id):
    session = Session()
    query = session.query(ContaPagar)

    query_filtrada = _aplicar_grupo_detalhe(query, grupo, grupo_id, date(2026, 7, 14))

    assert str(query_filtrada.statement)


def test_grupo_de_detalhe_rejeita_identificador_invalido():
    session = Session()

    with pytest.raises(HTTPException) as exc_info:
        _aplicar_grupo_detalhe(
            session.query(ContaPagar), "fornecedor", "nao-numerico", date(2026, 7, 14)
        )

    assert exc_info.value.status_code == 422


@pytest.mark.parametrize(
    ("origem", "nfe_numero", "nota_entrada_id", "documento", "esperado"),
    (
        ("caixa_pdv", None, None, None, "Caixa #10"),
        ("nota_entrada", "987", 42, None, "NF 987"),
        ("nota_entrada", None, 42, None, "Nota de entrada #42"),
        ("manual", None, None, "BOLETO-1", "BOLETO-1"),
    ),
)
def test_referencia_de_origem_identifica_documento_exibido(
    origem, nfe_numero, nota_entrada_id, documento, esperado
):
    conta = SimpleNamespace(
        nfe_numero=nfe_numero,
        nota_entrada_id=nota_entrada_id,
        documento=documento,
    )
    origem_info = {
        "origem_lancamento": origem,
        "caixa_referencia": "Caixa #10" if origem == "caixa_pdv" else None,
    }

    assert _referencia_origem(conta, origem_info) == esperado


def test_analise_contas_pagar_tem_filtros_de_exclusao_e_totalizadores():
    source = read_repo("backend/app/financeiro/contas_pagar_analise_routes.py")

    assert "fornecedor_ids: Optional[List[int]]" in source
    assert 'fornecedor_modo: str = Query("incluir"' in source
    assert 'fornecedor_modo_normalizado == "excluir"' in source
    assert "ContaPagar.fornecedor_id.notin_(fornecedor_ids)" in source
    assert 'ContaPagar.status.notin_(["pago", "cancelado"])' in source
    assert "ContaPagar.valor_final - ContaPagar.valor_pago" in source
    assert "vencido" in source
    assert "hoje" in source
    assert "amanha" in source
    assert "proximos_12_meses" in source
    assert "por_fornecedor" in source
    assert "por_tipo_despesa" in source
    assert "agenda_mensal" in source
