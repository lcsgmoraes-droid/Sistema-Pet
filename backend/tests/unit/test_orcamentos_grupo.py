from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.orcamentos_grupo_pdf import gerar_pdf_orcamentos
from app.orcamentos_grupo_documentos import (
    ordenar_itens_documento,
    preparar_snapshot_documento,
    sortear_modelos_documento,
)
from app.orcamentos_grupo_schemas import OrcamentoGrupoConfiguracaoUpdate
from app.orcamentos_grupo_service import montar_itens_snapshot, sortear_percentual
from tests.route_contract_helpers import method_routes


def test_sorteio_respeita_limites_inclusive():
    assert sortear_percentual(10, 30, randbelow=lambda _limite: 0) == Decimal("10")
    assert sortear_percentual(10, 30, randbelow=lambda limite: limite - 1) == Decimal(
        "30"
    )


def test_precos_de_cada_empresa_recebem_um_unico_percentual_e_arredondamento():
    itens = [
        SimpleNamespace(
            ordem=1,
            descricao="Produto A",
            quantidade=Decimal("2"),
            unidade="un",
            preco_unitario_base=Decimal("10"),
        ),
        SimpleNamespace(
            ordem=2,
            descricao="Servico B",
            quantidade=Decimal("1.5"),
            unidade="h",
            preco_unitario_base=Decimal("20"),
        ),
    ]

    snapshots, total = montar_itens_snapshot(itens, Decimal("17.35"))

    assert snapshots[0]["preco_unitario"] == "11.74"
    assert snapshots[0]["preco_total"] == "23.48"
    assert snapshots[1]["preco_unitario"] == "23.47"
    assert snapshots[1]["preco_total"] == "35.21"
    assert total == Decimal("58.69")


def test_configuracao_rejeita_faixa_invertida():
    with pytest.raises(ValueError, match="maximo"):
        OrcamentoGrupoConfiguracaoUpdate(
            percentual_minimo=30,
            percentual_maximo=10,
            quantidade_empresas=2,
            validade_dias=15,
        )


def test_modelos_documento_sao_distintos_e_ficam_persistidos_no_snapshot():
    modelos = sortear_modelos_documento(5, randbelow=lambda _limite: 0)

    assert len(modelos) == len(set(modelos)) == 5
    empresa, itens = preparar_snapshot_documento(
        {"nome": "Empresa teste"},
        [
            {"ordem": 1, "descricao": "Item B"},
            {"ordem": 2, "descricao": "Item A"},
        ],
        "editorial_rubi",
    )
    assert empresa["modelo_documento"] == "editorial_rubi"
    assert [item["descricao"] for item in itens] == ["Item A", "Item B"]


def test_ordenacao_visual_nao_altera_o_conteudo_dos_itens():
    itens = [
        {"ordem": 1, "descricao": "Produto A", "preco_total": "10.00"},
        {"ordem": 2, "descricao": "Produto B", "preco_total": "20.00"},
    ]

    ordenados = ordenar_itens_documento(itens, "classico_azul")

    assert [item["descricao"] for item in ordenados] == ["Produto B", "Produto A"]
    assert sum(Decimal(item["preco_total"]) for item in ordenados) == Decimal("30")


def test_pdf_gera_documentos_separados_por_empresa():
    orcamento = SimpleNamespace(
        id=1,
        numero="ORC-20260915-000001",
        titulo="Orcamento",
        destinatario="Comprador de teste",
        data_emissao=date(2026, 9, 15),
        validade_dias=15,
        observacoes="Pagamento conforme combinado.",
    )
    cotacoes = [
        SimpleNamespace(
            empresa_snapshot={
                "nome": nome,
                "razao_social": f"{nome} LTDA",
                "cnpj": "00.000.000/0001-00",
            },
            itens_snapshot=[
                {
                    "descricao": "Produto",
                    "quantidade": "2.000",
                    "unidade": "un",
                    "preco_unitario": "10.00",
                    "preco_total": "20.00",
                }
            ],
            total=Decimal("20"),
        )
        for nome in ("Empresa principal", "Empresa do grupo")
    ]

    pdf = gerar_pdf_orcamentos(orcamento, cotacoes)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000


def test_rotas_do_piloto_estao_registradas():
    from app.main import app

    routes = set(method_routes(app.router))
    assert ("/orcamentos-grupo/status", "GET") in routes
    assert ("/orcamentos-grupo/configuracao", "GET") in routes
    assert ("/orcamentos-grupo/empresas", "POST") in routes
    assert ("/orcamentos-grupo", "POST") in routes
    assert ("/orcamentos-grupo/{orcamento_id}/pdf", "GET") in routes
