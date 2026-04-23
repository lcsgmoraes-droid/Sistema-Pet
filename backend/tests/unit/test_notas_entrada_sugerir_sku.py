import os
import sys
from pathlib import Path
from types import SimpleNamespace


os.environ["DEBUG"] = "false"
if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
    os.environ["DATABASE_URL"] = "postgresql://petshop_user:petshop_password@localhost:5432/petshop_db"

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import notas_entrada_routes as routes  # noqa: E402


def _criar_item(codigo_produto: str):
    return SimpleNamespace(
        id=7,
        codigo_produto=codigo_produto,
        descricao="AGUA SANITARIA RAJJA 3 X 5L",
        unidade="UN",
        valor_unitario=5.0,
        ncm="28289011",
        ean="7898285310579",
    )


def test_montar_sugestao_sku_marca_codigo_fornecedor_como_ocupado(monkeypatch):
    catalogo = {
        "579": SimpleNamespace(id=10, codigo="579", nome="Produto existente"),
        "RAJ-579": None,
        "579-RAJ": None,
        "RAJ-579-V1": None,
        "RAJ-00001": None,
    }

    monkeypatch.setattr(
        routes,
        "calcular_composicao_custos_nota",
        lambda nota: {7: {"custo_aquisicao_unitario": 5.0}},
    )
    monkeypatch.setattr(
        routes,
        "_buscar_produto_por_codigo_global",
        lambda db, codigo: catalogo.get((codigo or "").strip()),
    )
    monkeypatch.setattr(
        routes,
        "gerar_sku_automatico",
        lambda prefixo, db, user_id: f"{prefixo}-00001",
    )

    payload = routes._montar_sugestao_sku_produto(
        nota=SimpleNamespace(fornecedor_nome="Rajja Distribuidora"),
        item=_criar_item("579"),
        db=None,
        tenant_id="tenant-teste",
        user_id=99,
    )

    assert payload["ja_existe"] is True
    assert payload["sku_proposto"] == "579"
    assert payload["produto_existente"]["codigo"] == "579"
    assert payload["sugestoes"][0]["sku"] == "RAJ-579"
    assert payload["sugestoes"][0]["padrao"] is True


def test_montar_sugestao_sku_retorna_codigo_original_quando_esta_livre(monkeypatch):
    monkeypatch.setattr(
        routes,
        "calcular_composicao_custos_nota",
        lambda nota: {7: {"custo_aquisicao_unitario": 5.0}},
    )
    monkeypatch.setattr(
        routes,
        "_buscar_produto_por_codigo_global",
        lambda db, codigo: None,
    )

    payload = routes._montar_sugestao_sku_produto(
        nota=SimpleNamespace(fornecedor_nome="Rajja Distribuidora"),
        item=_criar_item("579"),
        db=None,
        tenant_id="tenant-teste",
        user_id=99,
    )

    assert payload["ja_existe"] is False
    assert payload["sku_proposto"] == "579"
    assert len(payload["sugestoes"]) == 1
    assert payload["sugestoes"][0]["sku"] == "579"
    assert payload["sugestoes"][0]["disponivel"] is True
    assert payload["sugestoes"][0]["padrao"] is True
