import importlib
import importlib.util
from pathlib import Path

from app import contas_receber_routes


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    full_path = REPO_ROOT / path
    assert full_path.exists(), f"Arquivo esperado nao existe: {path}"
    return full_path.read_text(encoding="utf-8")


def test_contas_receber_registra_rota_de_analise_de_abertos_antes_do_detalhe():
    spec = importlib.util.find_spec("app.contas_receber_analise_routes")
    assert spec is not None

    analise_routes = importlib.import_module("app.contas_receber_analise_routes")
    paths = [route.path for route in contas_receber_routes.router.routes]

    assert "/contas-receber/analise-abertos" in paths
    assert paths.index("/contas-receber/analise-abertos") < paths.index(
        "/contas-receber/{conta_id}"
    )
    assert (
        contas_receber_routes.analisar_contas_receber_abertas
        is analise_routes.analisar_contas_receber_abertas
    )


def test_analise_contas_receber_tem_filtros_de_exclusao_e_totalizadores():
    source = read_repo("backend/app/contas_receber_analise_routes.py")

    assert "cliente_ids: Optional[List[int]]" in source
    assert 'cliente_modo: str = Query("incluir"' in source
    assert 'cliente_modo_normalizado == "excluir"' in source
    assert "ContaReceber.cliente_id.notin_(cliente_ids)" in source
    assert (
        'ContaReceber.status.notin_(["recebido", "pago", "cancelado", "cancelada"])'
        in source
    )
    assert "ContaReceber.valor_final - ContaReceber.valor_recebido" in source
    assert "vencido" in source
    assert "hoje" in source
    assert "amanha" in source
    assert "proximos_12_meses" in source
    assert "agenda_mensal" in source
    assert "por_cliente" in source
    assert "por_forma_pagamento" in source
    assert "por_canal" in source
