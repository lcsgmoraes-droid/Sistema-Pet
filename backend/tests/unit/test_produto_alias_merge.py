from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
import os

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.duplicatas_ignoradas_models import DuplicataIgnorada
from app.empresa_grupo_models import EmpresaGrupoEstoqueCompartilhado
from app.estoque_reserva_service import EstoqueReservaService
from app.models import Tenant, User
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.produto_identity_models import ProdutoFusaoLog, ProdutoSkuAlias
from app.produtos_models import (
    Produto,
    ProdutoBlingSync,
    ProdutoBlingSyncQueue,
    ProdutoFornecedor,
    ProdutoGranelVinculo,
    ProdutoImagem,
    ProdutoKitComponente,
    ProdutoListaPreco,
    ProdutoLote,
    EstoqueMovimentacao,
)
from app.produtos_estoque_models import ProdutoBlingCostSyncQueue
from app.services.produto_alias_service import (
    aplicar_alias,
    preview_alias,
    registrar_alias,
)
from app.services.produto_bling_identity_service import (
    produto_pedido_por_bling_retirado,
    validar_origem_bling_ativa,
)
from app.services.produto_merge_service import (
    executar_fusao_produtos,
    montar_preview_fusao_produtos,
)
from app.services.produto_sku_service import buscar_produto_por_sku
from app.services.ecommerceai_catalog_service import EcommerceAICatalogService
from app.tenancy.context import set_current_tenant


@pytest.fixture
def case():
    # Other unit modules may register related mappers during collection. Load the
    # canonical registry before constructing rows, independently of test order.
    import app.db.base  # noqa: F401

    pg_url = os.getenv("COREPET_MERGE_PG_URL")
    models = (
        Tenant,
        User,
        Produto,
        ProdutoImagem,
        ProdutoBlingSync,
        ProdutoBlingSyncQueue,
        ProdutoBlingCostSyncQueue,
        ProdutoSkuAlias,
        ProdutoFusaoLog,
        ProdutoFornecedor,
        ProdutoGranelVinculo,
        ProdutoKitComponente,
        ProdutoListaPreco,
        ProdutoLote,
        ProdutoConfigFiscal,
        PedidoIntegrado,
        PedidoIntegradoItem,
        EstoqueMovimentacao,
        DuplicataIgnorada,
        EmpresaGrupoEstoqueCompartilhado,
    )
    if pg_url:
        url = make_url(pg_url)
        if (
            url.host != "127.0.0.1"
            or url.port != 55487
            or url.database != "corepet_merge_test"
        ):
            pytest.fail(
                "PostgreSQL tests require the disposable database on 127.0.0.1:55487/corepet_merge_test"
            )
        engine = create_engine(pg_url)
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        tables = {model.__table__ for model in models}
        from app.veterinario_models import VetPartnerLink
        from app.empresa_grupo_models import EmpresaGrupoMembro
        from app.models import UserTenant

        tables.update(
            (
                VetPartnerLink.__table__,
                EmpresaGrupoMembro.__table__,
                UserTenant.__table__,
            )
        )
        while True:
            targets = {fk.column.table for table in tables for fk in table.foreign_keys}
            if targets.issubset(tables):
                break
            tables.update(targets)
        Produto.metadata.create_all(engine, tables=list(tables))
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        for model in models:
            model.__table__.create(engine)
    tenant = uuid4()
    set_current_tenant(tenant)
    with Session(engine, expire_on_commit=False) as db:
        db.add(
            Tenant(
                id=str(tenant),
                name="Teste",
                name_normalized=str(tenant),
                ecommerce_usar_estoque_canal=False,
            )
        )
        db.add(
            User(
                id=1,
                tenant_id=tenant,
                email="merge-test@example.invalid",
                hashed_password="not-an-authenticated-password",
                nome="Test operator",
            )
        )
        primary = Produto(
            tenant_id=tenant,
            user_id=1,
            codigo="CANON",
            nome="Pacote 30 unidades",
            codigo_barras="7898396116978",
            tipo="produto",
            tipo_produto="SIMPLES",
            unidade="UN",
            estoque_atual=50,
            estoque_fisico=0,
            estoque_ecommerce=0,
            preco_custo=49.94,
            preco_venda=79.9,
            ativo=True,
            situacao=True,
        )
        duplicate = Produto(
            tenant_id=tenant,
            user_id=1,
            codigo="ANTIGO",
            nome="Mesmo pacote",
            tipo="produto",
            tipo_produto="SIMPLES",
            unidade="UN",
            estoque_atual=4,
            estoque_fisico=0,
            estoque_ecommerce=0,
            preco_custo=0,
            preco_venda=124.87,
            ativo=True,
            situacao=True,
        )
        db.add_all([primary, duplicate])
        db.flush()
        a = ProdutoBlingSync(
            tenant_id=tenant,
            produto_id=primary.id,
            bling_produto_id="BLING-A",
            sincronizar=True,
            status="ativo",
        )
        b = ProdutoBlingSync(
            tenant_id=tenant,
            produto_id=duplicate.id,
            bling_produto_id="BLING-B",
            sincronizar=True,
            status="ativo",
        )
        db.add_all([a, b])
        db.commit()
        yield SimpleNamespace(
            db=db,
            engine=engine,
            tenant=tenant,
            primary=primary,
            duplicate=duplicate,
            a=a,
            b=b,
        )
    engine.dispose()


def merge(case, **overrides):
    args = dict(
        tenant_id=case.tenant,
        principal_id=case.primary.id,
        duplicado_id=case.duplicate.id,
        estrategia_estoque="manter_principal",
    )
    preview = montar_preview_fusao_produtos(case.db, **args)
    return executar_fusao_produtos(
        case.db,
        **args,
        **(
            dict(
                decisoes_campos={
                    "preco_custo": "duplicado",
                    "preco_venda": "duplicado",
                },
                user_id=1,
                observacao="Contagem confirmada: 50 no total, duplicado espelha o saldo.",
                preview_token=preview["preview_token"],
                preservar_vinculo_bling_duplicado=True,
                aliases_sku=["SELLER-OLD"],
            )
            | overrides
        ),
    )


def add_reservations(case):
    for qty in (2, 1, 1):
        order = PedidoIntegrado(
            tenant_id=case.tenant,
            pedido_bling_id=str(uuid4()),
            canal="amazon",
            status="aberto",
            expira_em=datetime.utcnow() + timedelta(days=15),
            payload={},
        )
        case.db.add(order)
        case.db.flush()
        case.db.add(
            PedidoIntegradoItem(
                tenant_id=case.tenant,
                pedido_integrado_id=order.id,
                sku="SELLER-OLD",
                quantidade=qty,
            )
        )
    case.db.commit()


def test_merge_preserves_50_prices_and_reservations_without_public_54(case):
    add_reservations(case)
    items = case.db.query(PedidoIntegradoItem).all()
    original = [(i.id, i.sku, i.quantidade, i.reservado_em) for i in items]
    seen = []

    def after_flush(db, _ctx):
        seen.append(case.primary.estoque_atual)

    event.listen(case.db, "after_flush", after_flush)
    result = merge(case)
    assert case.primary.estoque_atual == 50
    assert seen and 54 not in seen
    assert case.duplicate.estoque_atual == 0
    assert case.duplicate.deleted_at and not case.duplicate.ativo
    assert (
        case.primary.codigo,
        case.primary.preco_custo,
        case.primary.preco_venda,
    ) == ("CANON", 49.94, 79.9)
    assert [(i.id, i.sku, i.quantidade, i.reservado_em) for i in items] == original
    assert all(i.liberado_em is None and i.vendido_em is None for i in items)
    assert EstoqueReservaService.mapa_reservas_ativas_por_produto(
        case.db, case.tenant
    ) == {case.primary.id: 4.0}
    catalog = EcommerceAICatalogService(
        case.db, tenant_id=case.tenant, public_api_url="https://example.com/api"
    ).list_products()
    assert catalog["products"][0]["stock"]["available"] == "46.0"
    assert result["auditoria_id"]
    audit = case.db.query(ProdutoFusaoLog).one()
    assert audit.antes["duplicado"]["estoque_atual"] == 4
    assert audit.depois["principal"]["estoque_atual"] == 50


def test_retains_bling_id_queue_and_history_without_remote_authority(case):
    queue = ProdutoBlingSyncQueue(
        tenant_id=case.tenant,
        produto_id=case.duplicate.id,
        sync_id=case.b.id,
        estoque_novo=2,
        status="sucesso",
        tentativas=1,
    )
    movement = EstoqueMovimentacao(
        tenant_id=case.tenant,
        produto_id=case.duplicate.id,
        tipo="saida",
        motivo="venda",
        quantidade=1,
        quantidade_anterior=5,
        quantidade_nova=4,
        user_id=1,
    )
    case.db.add_all([queue, movement])
    case.db.commit()
    merge(case)
    case.db.expire_all()
    assert case.db.query(ProdutoBlingSync).count() == 2
    assert case.b.bling_produto_id == "BLING-B"
    assert case.b.retirado_para_produto_id == case.primary.id and not case.b.sincronizar
    assert (
        queue.produto_id == case.duplicate.id
        and queue.sync_id == case.b.id
        and queue.status == "sucesso"
    )
    assert movement.produto_id == case.primary.id and movement.quantidade_nova == 4
    assert (
        produto_pedido_por_bling_retirado(
            case.db, tenant_id=case.tenant, bling_produto_id="BLING-B"
        ).id
        == case.primary.id
    )
    with pytest.raises(ValueError, match="retirada"):
        validar_origem_bling_ativa(
            case.db, tenant_id=case.tenant, bling_produto_id="BLING-B"
        )
    assert case.primary.estoque_atual == 50


def test_repeated_merge_is_rejected_without_adding_stock(case):
    merge(case)
    with pytest.raises(ValueError, match="arquivado|fundido"):
        merge(case)
    case.db.rollback()
    assert case.primary.estoque_atual == 50
    assert case.db.query(ProdutoFusaoLog).count() == 1


@pytest.mark.parametrize("reason", [None, "", "ok"])
def test_preserving_count_requires_explicit_evidence_before_any_mutation(case, reason):
    with pytest.raises(ValueError, match="evidencia"):
        merge(case, observacao=reason)
    assert case.primary.estoque_atual == 50 and case.duplicate.estoque_atual == 4
    assert case.duplicate.deleted_at is None
    assert case.db.query(ProdutoSkuAlias).count() == 0


def test_stale_preview_rejected_before_alias_or_archive(case):
    preview = montar_preview_fusao_produtos(
        case.db,
        tenant_id=case.tenant,
        principal_id=case.primary.id,
        duplicado_id=case.duplicate.id,
        estrategia_estoque="manter_principal",
    )
    case.primary.estoque_atual = 49
    case.db.commit()
    with pytest.raises(ValueError, match="alterado"):
        merge(case, preview_token=preview["preview_token"])
    assert case.duplicate.deleted_at is None
    assert case.db.query(ProdutoSkuAlias).count() == 0


def test_autocreate_rechecks_alias_registered_while_fetching_bling(case, monkeypatch):
    from app.services.bling_nf import autocadastro

    def remote_reply(_sku):
        with Session(case.engine) as concurrent:
            registrar_alias(
                concurrent,
                tenant_id=case.tenant,
                produto_id=case.primary.id,
                sku="LATE-ALIAS",
                user_id=1,
                motivo="Identidade confirmada enquanto a consulta remota aguardava.",
            )
            concurrent.commit()
        return {
            "id": "NEW-BLING",
            "codigo": "LATE-ALIAS",
            "saldoFisicoTotal": 2,
            "preco": 1,
        }

    monkeypatch.setattr(autocadastro, "_buscar_produto_bling_por_sku", remote_reply)
    result = autocadastro.criar_produto_automatico_do_bling(
        case.db, case.tenant, "LATE-ALIAS"
    )
    assert result.id == case.primary.id
    assert case.db.query(Produto).count() == 2
    assert (result.estoque_atual, result.preco_custo, result.preco_venda) == (
        50,
        49.94,
        79.9,
    )


@pytest.mark.parametrize("status", ["pendente", "processando", "erro"])
def test_pending_queue_blocks_merge(case, status):
    case.db.add(
        ProdutoBlingSyncQueue(
            tenant_id=case.tenant,
            produto_id=case.duplicate.id,
            sync_id=case.b.id,
            estoque_novo=4,
            status=status,
        )
    )
    case.db.commit()
    with pytest.raises(ValueError, match="filas"):
        merge(case)
    assert case.primary.estoque_atual == 50 and case.duplicate.deleted_at is None


def test_alias_preview_read_only_and_confirmed_apply_is_normalized(case):
    preview = preview_alias(
        case.db, tenant_id=case.tenant, produto_id=case.primary.id, sku="  Mixed-Case  "
    )
    assert case.db.query(ProdutoSkuAlias).count() == 0
    aplicar_alias(
        case.db,
        tenant_id=case.tenant,
        produto_id=case.primary.id,
        sku="  Mixed-Case  ",
        preview_token=preview["preview_token"],
        user_id=1,
        motivo="Identidade comprovada pelo operador.",
    )
    assert (
        buscar_produto_por_sku(case.db, tenant_id=case.tenant, sku="mixed-case").id
        == case.primary.id
    )
    alias = case.db.query(ProdutoSkuAlias).one()
    assert alias.sku_normalizado == "mixed-case" and alias.user_id == 1
    assert (
        case.primary.codigo_barras == "7898396116978"
        and case.primary.codigos_barras_alternativos is None
    )


def test_alias_collision_and_cross_tenant_fail_closed(case):
    with pytest.raises(ValueError, match="outro produto"):
        registrar_alias(
            case.db,
            tenant_id=case.tenant,
            produto_id=case.primary.id,
            sku="antigo",
            user_id=1,
            motivo="Confirmed identity",
        )
    with pytest.raises(ValueError, match="tenant"):
        registrar_alias(
            case.db,
            tenant_id=uuid4(),
            produto_id=case.primary.id,
            sku="X",
            user_id=1,
            motivo="Confirmed identity",
        )
    assert case.db.query(ProdutoSkuAlias).count() == 0


def test_next_bling_order_resolves_alias_and_retired_id_without_copying(case):
    from app.services.bling_nf.autocadastro import (
        criar_produto_automatico_do_bling_por_item,
    )

    merge(case)
    for payload in (
        {"id": "BLING-B", "codigo": "OTHER", "estoque": 2, "preco": 1},
        {"codigo": "ANTIGO", "estoque": 2, "preco": 1},
    ):
        found = criar_produto_automatico_do_bling_por_item(
            case.db, case.tenant, payload
        )
        assert found.id == case.primary.id
        assert (found.estoque_atual, found.preco_custo, found.preco_venda) == (
            50,
            49.94,
            79.9,
        )
    assert case.db.query(Produto).count() == 2


def test_same_bling_id_stays_active_for_survivor(case):
    case.b.bling_produto_id = case.a.bling_produto_id
    case.db.commit()
    merge(case)
    validar_origem_bling_ativa(
        case.db,
        tenant_id=case.tenant,
        bling_produto_id=case.a.bling_produto_id,
        produto=case.primary,
        sync=case.a,
    )
    assert case.a.sincronizar and not case.b.sincronizar


def test_only_duplicate_bling_link_moves_with_consistent_historical_queue(case):
    case.db.delete(case.a)
    queue = ProdutoBlingSyncQueue(
        tenant_id=case.tenant,
        produto_id=case.duplicate.id,
        sync_id=case.b.id,
        estoque_novo=4,
        status="sucesso",
    )
    case.db.add(queue)
    case.db.commit()
    merge(case)
    case.db.expire_all()
    assert (
        case.b.produto_id == case.primary.id and case.b.retirado_para_produto_id is None
    )
    assert queue.produto_id == case.primary.id and queue.sync_id == case.b.id


def test_chained_merge_preserves_old_skus_and_bling_order_identities(case):
    merge(case)
    previous = case.primary
    newest = Produto(
        tenant_id=case.tenant,
        user_id=1,
        codigo="NEW-CANON",
        nome="Pacote 30",
        tipo="produto",
        tipo_produto="SIMPLES",
        unidade="UN",
        estoque_atual=50,
        preco_custo=49.94,
        preco_venda=79.9,
        ativo=True,
    )
    case.db.add(newest)
    case.db.flush()
    case.db.add(
        ProdutoBlingSync(
            tenant_id=case.tenant,
            produto_id=newest.id,
            bling_produto_id="BLING-C",
            sincronizar=True,
        )
    )
    case.db.commit()
    case.primary, case.duplicate = newest, previous
    merge(case)
    assert (
        produto_pedido_por_bling_retirado(
            case.db, tenant_id=case.tenant, bling_produto_id="BLING-B"
        ).id
        == newest.id
    )
    assert (
        produto_pedido_por_bling_retirado(
            case.db, tenant_id=case.tenant, bling_produto_id="BLING-A"
        ).id
        == newest.id
    )
    assert (
        buscar_produto_por_sku(case.db, tenant_id=case.tenant, sku="ANTIGO").id
        == newest.id
    )
    assert (
        buscar_produto_por_sku(case.db, tenant_id=case.tenant, sku="SELLER-OLD").id
        == newest.id
    )
