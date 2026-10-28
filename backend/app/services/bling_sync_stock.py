"""Saldo vendavel e propagacao de alteracoes dos componentes para kits virtuais."""

from __future__ import annotations

import logging
from contextlib import nullcontext

from sqlalchemy import event

from app.produtos_models import Produto, ProdutoBlingSync, ProdutoKitComponente
from app.services.kit_estoque_service import KitEstoqueService
from app.services.produto_bling_identity_service import (
    produto_arquivado,
    vinculo_retirado,
)
from app.tenancy.context import get_current_tenant, tenant_context

logger = logging.getLogger(__name__)
_PENDENCIAS = "bling_kits_componentes_pendentes"
_LISTENERS = "bling_kits_componentes_listeners"


def carregar_produto_sync(db, produto_id):
    """Mantem a ordem produto -> vinculo usada tambem pela fusao."""
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id)
        .populate_existing()
        .with_for_update(of=Produto)
        .first()
    )
    if not produto:
        return None, None
    sync = (
        db.query(ProdutoBlingSync)
        .filter(ProdutoBlingSync.produto_id == produto_id)
        .populate_existing()
        .with_for_update(of=ProdutoBlingSync)
        .first()
    )
    return produto, None if produto_arquivado(produto) or vinculo_retirado(
        sync
    ) else sync


def enfileirar_sync_background(service, abrir_sessao, produto_id, **kwargs):
    db = abrir_sessao()
    try:
        resultado = service.queue_product_sync(db, produto_id=produto_id, **kwargs)
        kits = enfileirar_kits_dependentes(
            db,
            produto_id,
            enfileirar=service.queue_product_sync,
            motivo=kwargs.get("motivo", ""),
            origem=kwargs.get("origem", "evento"),
        )
        if not resultado.get("ok") and not kits:
            db.rollback()
            return
        db.commit()
    except Exception as error:
        db.rollback()
        logger.warning("[BLING SYNC] Falha ao enfileirar sync: %s", error)
    finally:
        db.close()


def produto_kit_virtual(produto) -> bool:
    return (
        getattr(produto, "tipo_produto", None) in ("KIT", "VARIACAO")
        and getattr(produto, "tipo_kit", None) == "VIRTUAL"
    )


def estoque_produto_bling(db, produto, estoque_novo=None) -> float:
    """Kits compartilham o saldo livre dos componentes, nunca um saldo proprio."""
    if produto_kit_virtual(produto):
        saldos = KitEstoqueService.calcular_estoques_virtuais_em_lote(
            db, [produto], tenant_id=produto.tenant_id
        )
        return float(saldos.get(produto.id, 0))
    return float((produto.estoque_atual or 0) if estoque_novo is None else estoque_novo)


def estoques_produtos_bling(db, produtos, *, tenant_id):
    """A listagem compartilha uma consulta de componentes e uma de reservas."""
    virtuais = KitEstoqueService.calcular_estoques_virtuais_em_lote(
        db, produtos, tenant_id=tenant_id
    )
    return {
        produto.id: float(virtuais.get(produto.id, produto.estoque_atual or 0))
        for produto in produtos
    }


def enfileirar_kits_dependentes(
    db, produto_id, *, enfileirar, motivo="", origem="evento"
):
    """Inclui pacotes/caixas mesmo quando o componente nao tem vinculo Bling."""
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto or produto_arquivado(produto):
        return []
    kits = (
        db.query(Produto)
        .join(ProdutoKitComponente, ProdutoKitComponente.kit_id == Produto.id)
        .filter(
            ProdutoKitComponente.produto_componente_id == produto_id,
            ProdutoKitComponente.tenant_id == produto.tenant_id,
            Produto.tenant_id == produto.tenant_id,
            Produto.tipo_produto.in_(["KIT", "VARIACAO"]),
            Produto.tipo_kit == "VIRTUAL",
            Produto.id != produto_id,
        )
        .order_by(Produto.id.asc())
        .all()
    )
    resultados = []
    for kit in kits:
        resultado = enfileirar(
            db,
            produto_id=kit.id,
            motivo=motivo or "alteracao_componente",
            origem=origem,
        )
        if resultado.get("ok"):
            resultados.append(resultado)
    return resultados


def _enfileirar_antes_do_commit(db):
    # before_commit tambem roda ao liberar SAVEPOINTs. Esperar o commit externo
    # evita travar kits enquanto ainda faltam baixar outros componentes da venda.
    if db.in_nested_transaction():
        return
    pendentes = db.info.pop(_PENDENCIAS, {})
    if not pendentes:
        return
    try:
        with db.begin_nested():
            for (_tenant_key, produto_id), config in sorted(pendentes.items()):
                tenant_id = config.pop("tenant_id")
                contexto = (
                    tenant_context(tenant_id)
                    if tenant_id is not None
                    else nullcontext()
                )
                with contexto:
                    enfileirar_kits_dependentes(db, produto_id, **config)
    except Exception as error:
        logger.warning("[BLING SYNC] Falha ao enfileirar kits dependentes: %s", error)


def _limpar_pendencias(db, transaction):
    if transaction.parent is None:
        db.info.pop(_PENDENCIAS, None)


def agendar_kits_dependentes(db, produto_id, *, enfileirar, motivo="", origem="evento"):
    """Propaga uma vez por componente, depois de terminar as baixas da transacao."""
    if not db.info.get(_LISTENERS):
        event.listen(db, "before_commit", _enfileirar_antes_do_commit)
        event.listen(db, "after_transaction_end", _limpar_pendencias)
        db.info[_LISTENERS] = True
    tenant_id = get_current_tenant()
    db.info.setdefault(_PENDENCIAS, {})[(str(tenant_id or ""), produto_id)] = {
        "tenant_id": tenant_id,
        "enfileirar": enfileirar,
        "motivo": motivo,
        "origem": origem,
    }
