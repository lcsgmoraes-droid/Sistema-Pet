from pathlib import Path

import pytest
from pydantic import ValidationError

from app.nao_venda_models import NaoVenda, NaoVendaItem
from app.nao_venda_schemas import NaoVendaCreate, NaoVendaItemCreate


ROOT = Path(__file__).resolve().parents[2]


def test_schema_permite_atendimento_anonimo_sem_produto():
    payload = NaoVendaCreate(motivo="cliente_pesquisando")

    assert payload.cliente_id is None
    assert payload.itens == []


def test_schema_aceita_produto_livre_e_rejeita_item_vazio():
    item = NaoVendaItemCreate(
        produto_nome="  Ração que a loja não trabalha  ",
        marca_nome="  Marca nova ",
    )

    assert item.produto_nome == "Ração que a loja não trabalha"
    assert item.marca_nome == "Marca nova"

    with pytest.raises(ValidationError, match="Informe ou selecione o produto"):
        NaoVendaItemCreate()


def test_schema_rejeita_motivo_fora_da_lista_controlada():
    with pytest.raises(ValidationError, match="Motivo de não venda inválido"):
        NaoVendaCreate(motivo="qualquer_texto")


def test_modelos_sao_multitenant_e_rotas_filtram_tenant_explicitamente():
    assert "tenant_id" in NaoVenda.__table__.columns
    assert "tenant_id" in NaoVendaItem.__table__.columns

    routes = (ROOT / "app" / "nao_venda_routes.py").read_text(encoding="utf-8")
    service = (ROOT / "app" / "services" / "nao_venda_service.py").read_text(
        encoding="utf-8"
    )
    migration = (
        ROOT / "alembic" / "versions" / "zxh20260827a1_create_nao_vendas.py"
    ).read_text(encoding="utf-8")

    assert "NaoVenda.tenant_id == tenant" in routes
    assert "Cliente.tenant_id == tenant_id" in service
    assert "Produto.tenant_id == tenant_id" in service
    assert "PendenciaEstoque.tenant_id == tenant_id" in service
    assert 'table_names=("nao_vendas", "nao_venda_itens")' in migration
    assert migration.count("postgresql.UUID(as_uuid=True)") == 2
    assert "_tenant_id_type" not in migration
