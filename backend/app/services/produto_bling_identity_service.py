"""A retired Bling record can identify an order but cannot change a catalog."""

from app.produtos_models import Produto, ProdutoBlingSync


def produto_arquivado(produto):
    return bool(
        produto is not None and getattr(produto, "deleted_at", None) is not None
    )


def vinculo_retirado(sync):
    return bool(
        sync is not None and getattr(sync, "retirado_para_produto_id", None) is not None
    )


def ids_bling_retirados(db, tenant_id):
    retired = {
        str(row[0])
        for row in db.query(ProdutoBlingSync.bling_produto_id)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.retirado_para_produto_id.isnot(None),
        )
        .all()
        if row[0]
    }
    # Two historical local registrations may already point at the same Bling ID.
    # Retiring one registration must not withdraw the surviving primary source.
    active = {
        str(row[0])
        for row in db.query(ProdutoBlingSync.bling_produto_id)
        .join(
            Produto,
            (Produto.id == ProdutoBlingSync.produto_id)
            & (Produto.tenant_id == ProdutoBlingSync.tenant_id),
        )
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.retirado_para_produto_id.is_(None),
            Produto.deleted_at.is_(None),
        )
        .all()
        if row[0]
    }
    return retired - active


def validar_origem_bling_ativa(
    db, *, tenant_id, bling_produto_id=None, produto=None, sync=None
):
    if produto_arquivado(produto) or vinculo_retirado(sync):
        raise ValueError(
            "Produto ou origem Bling retirado por fusao; permitido somente como identidade historica de pedidos."
        )
    if bling_produto_id and str(bling_produto_id) in ids_bling_retirados(db, tenant_id):
        raise ValueError(
            "Origem Bling retirada por fusao; saldo, custo e cadastro nao podem ser importados nem religados."
        )


def produto_pedido_por_bling_retirado(db, *, tenant_id, bling_produto_id):
    if not bling_produto_id:
        return None
    sync = (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id == str(bling_produto_id),
            ProdutoBlingSync.retirado_para_produto_id.isnot(None),
        )
        .first()
    )
    if not sync:
        return None
    product = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id == sync.retirado_para_produto_id,
            Produto.deleted_at.is_(None),
        )
        .first()
    )
    if not product:
        raise ValueError(
            "Origem Bling retirada sem sucessor ativo; revisar identidade antes de processar o pedido."
        )
    return product
