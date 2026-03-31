from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao
from app.services.pedido_integrado_consolidation_service import localizar_pedido_por_bling_id
from app.utils.logger import logger


_NFE_STATUS_AUTORIZADAS = ("autorizada",)


def _utc_now() -> datetime:
    return datetime.utcnow()


def _limite_data_recentes(dias: int) -> datetime:
    return _utc_now() - timedelta(days=max(int(dias or 1), 1))


def _garantir_registry_sqlalchemy_reconciliacao() -> None:
    from app.services.bling_flow_monitor_service import _garantir_registry_sqlalchemy_auditoria

    _garantir_registry_sqlalchemy_auditoria()


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _coerce_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _buscar_nfes_autorizadas_recentes(
    db: Session,
    tenant_id,
    *,
    dias: int,
    limite_notas: int,
) -> list[BlingNotaFiscalCache]:
    return (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.data_emissao.isnot(None),
            BlingNotaFiscalCache.data_emissao >= _limite_data_recentes(dias),
            func.lower(BlingNotaFiscalCache.status).in_(_NFE_STATUS_AUTORIZADAS),
        )
        .order_by(BlingNotaFiscalCache.data_emissao.desc(), BlingNotaFiscalCache.id.desc())
        .limit(max(int(limite_notas or 0), 1))
        .all()
    )


def _deduplicar_registros_nfe_por_pedido(registros: list[BlingNotaFiscalCache]) -> list[BlingNotaFiscalCache]:
    selecionados: list[BlingNotaFiscalCache] = []
    chaves_vistas: set[str] = set()

    for registro in registros:
        refs = _extrair_referencias_nf_cache(registro)
        chave = (
            _text(refs.get("pedido_bling_id"))
            or f"loja::{_text(refs.get('numero_pedido_loja'))}::{_text(refs.get('loja_id')) or 'sem_loja'}"
            or f"nf::{_text(refs.get('nf_bling_id'))}"
        )
        if not chave or chave in chaves_vistas:
            continue
        chaves_vistas.add(chave)
        selecionados.append(registro)

    return selecionados


def listar_tenants_com_nfes_autorizadas_recentes(db: Session, *, dias: int) -> list:
    _garantir_registry_sqlalchemy_reconciliacao()
    return [
        tenant_id
        for (tenant_id,) in (
            db.query(BlingNotaFiscalCache.tenant_id)
            .filter(
                BlingNotaFiscalCache.data_emissao.isnot(None),
                BlingNotaFiscalCache.data_emissao >= _limite_data_recentes(dias),
                func.lower(BlingNotaFiscalCache.status).in_(_NFE_STATUS_AUTORIZADAS),
            )
            .distinct()
            .all()
        )
    ]


def _extrair_referencias_nf_cache(registro: BlingNotaFiscalCache) -> dict:
    from app.integracao_bling_nf_routes import _extrair_numero_pedido_loja_nf, _loja_id_nf_payload

    detalhe = _dict(getattr(registro, "detalhe_payload", None))
    resumo = _dict(getattr(registro, "resumo_payload", None))
    pedido_ref = _dict(
        detalhe.get("pedido")
        or detalhe.get("pedidoVenda")
        or detalhe.get("pedidoCompra")
        or resumo.get("pedido")
        or resumo.get("pedidoVenda")
        or resumo.get("pedidoCompra")
    )

    return {
        "nf_bling_id": _text(getattr(registro, "bling_id", None)),
        "nf_numero": _text(getattr(registro, "numero", None)) or _text(detalhe.get("numero")) or _text(resumo.get("numero")),
        "pedido_bling_id": (
            _text(getattr(registro, "pedido_bling_id_ref", None))
            or _text(pedido_ref.get("id"))
            or _text(detalhe.get("pedido_bling_id"))
            or _text(resumo.get("pedido_bling_id"))
        ),
        "pedido_bling_numero": (
            _text(pedido_ref.get("numero"))
            or _text(detalhe.get("pedido_bling_numero"))
            or _text(resumo.get("pedido_bling_numero"))
        ),
        "numero_pedido_loja": (
            _text(getattr(registro, "numero_pedido_loja", None))
            or _extrair_numero_pedido_loja_nf(detalhe)
            or _extrair_numero_pedido_loja_nf(resumo)
        ),
        "loja_id": (
            _loja_id_nf_payload(detalhe)
            or _loja_id_nf_payload(resumo)
        ),
        "dados_nf": detalhe or resumo or {},
        "situacao_num": _coerce_int(_dict(detalhe.get("situacao")).get("id"), _coerce_int(detalhe.get("situacao"), 5)),
    }


def _localizar_pedido_para_nf_cache(
    db: Session,
    *,
    tenant_id,
    pedido_bling_id: str | None,
    pedido_bling_numero: str | None,
    numero_pedido_loja: str | None,
    loja_id: str | None,
) -> PedidoIntegrado | None:
    from app.integracao_bling_nf_routes import (
        _localizar_pedido_local_por_numero_bling,
        _localizar_pedido_local_por_numero_loja,
    )

    pedido = None
    pedido_bling_id = _text(pedido_bling_id)
    if pedido_bling_id:
        pedido = localizar_pedido_por_bling_id(
            db,
            tenant_id=tenant_id,
            pedido_bling_id=pedido_bling_id,
        )
    if not pedido and pedido_bling_numero:
        pedido = _localizar_pedido_local_por_numero_bling(
            db,
            tenant_id=tenant_id,
            pedido_bling_numero=pedido_bling_numero,
        )
    if not pedido and numero_pedido_loja:
        pedido = _localizar_pedido_local_por_numero_loja(
            db,
            tenant_id=tenant_id,
            numero_pedido_loja=numero_pedido_loja,
            loja_id=loja_id,
        )
    return pedido


def _pedido_precisa_reconciliacao(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_bling_id: str | None,
    nf_numero: str | None,
) -> bool:
    from app.services.bling_nf_service import movimento_documentado_por_nf

    payload = pedido.payload if isinstance(pedido.payload, dict) else {}
    ultima_nf = _dict(payload.get("ultima_nf"))
    ultima_nf_id = _text(ultima_nf.get("id"))
    ultima_nf_numero = _text(ultima_nf.get("numero"))
    movimentacoes_saida = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .all()
    )
    possui_movimentacao_nf = any(
        movimento_documentado_por_nf(
            mov,
            nf_numero=nf_numero,
            nf_bling_id=nf_bling_id,
        )
        for mov in movimentacoes_saida
    )
    return bool(
        not ultima_nf_id
        or ultima_nf_id in {"0", "-1"}
        or (nf_bling_id and ultima_nf_id != nf_bling_id)
        or (nf_numero and ultima_nf_numero != nf_numero)
        or any(not getattr(item, "vendido_em", None) for item in itens)
        or not possui_movimentacao_nf
    )


def reconciliar_nf_autorizada_cache(
    db: Session,
    *,
    tenant_id,
    registro: BlingNotaFiscalCache,
) -> dict:
    from app.integracao_bling_nf_routes import _registrar_nf_no_pedido
    from app.services.bling_flow_monitor_service import (
        registrar_evento,
        registrar_vinculo_nf_pedido,
        resolver_incidentes_relacionados,
    )
    from app.services.bling_nf_service import processar_nf_autorizada

    refs = _extrair_referencias_nf_cache(registro)
    pedido = _localizar_pedido_para_nf_cache(
        db,
        tenant_id=tenant_id,
        pedido_bling_id=refs.get("pedido_bling_id"),
        pedido_bling_numero=refs.get("pedido_bling_numero"),
        numero_pedido_loja=refs.get("numero_pedido_loja"),
        loja_id=refs.get("loja_id"),
    )

    if not pedido:
        return {
            "success": False,
            "motivo": "pedido_nao_localizado",
            "nf_numero": refs.get("nf_numero"),
            "nf_bling_id": refs.get("nf_bling_id"),
            "numero_pedido_loja": refs.get("numero_pedido_loja"),
            "pedido_bling_numero": refs.get("pedido_bling_numero"),
        }

    itens = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .all()
    )
    if not itens:
        return {
            "success": False,
            "motivo": "pedido_sem_itens",
            "pedido_id": pedido.id,
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "nf_numero": refs.get("nf_numero"),
        }

    precisa_reconciliar = _pedido_precisa_reconciliacao(
        db,
        pedido=pedido,
        itens=itens,
        nf_bling_id=refs.get("nf_bling_id"),
        nf_numero=refs.get("nf_numero"),
    )

    if not getattr(registro, "pedido_bling_id_ref", None) and getattr(pedido, "pedido_bling_id", None):
        registro.pedido_bling_id_ref = pedido.pedido_bling_id
        db.add(registro)

    if not precisa_reconciliar:
        db.commit()
        return {
            "success": True,
            "motivo": "ja_conciliada",
            "pedido_id": pedido.id,
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "nf_numero": refs.get("nf_numero"),
            "nf_bling_id": refs.get("nf_bling_id"),
        }

    try:
        _registrar_nf_no_pedido(
            pedido=pedido,
            data=refs.get("dados_nf") or {},
            nf_id=refs.get("nf_bling_id") or "",
            situacao_num=_coerce_int(refs.get("situacao_num"), 5),
        )
        db.add(pedido)
        db.add(registro)
        db.flush()

        acao = processar_nf_autorizada(
            db=db,
            pedido=pedido,
            itens=itens,
            nf_id=refs.get("nf_bling_id") or "",
        )
        if acao not in {"venda_confirmada", "venda_ja_confirmada"}:
            db.rollback()
            return {
                "success": False,
                "motivo": "nf_nao_conciliada",
                "acao": acao,
                "pedido_id": pedido.id,
                "pedido_bling_numero": pedido.pedido_bling_numero,
                "nf_numero": refs.get("nf_numero"),
                "nf_bling_id": refs.get("nf_bling_id"),
            }

        registrar_vinculo_nf_pedido(
            pedido=pedido,
            source="scheduler",
            nf_bling_id=refs.get("nf_bling_id"),
            nf_numero=refs.get("nf_numero"),
            message="NF autorizada reconciliada a partir do cache local da nota.",
            payload={
                "link_source": "nf_cache_reconciliation",
                "numero_pedido_loja": refs.get("numero_pedido_loja"),
                "pedido_bling_numero": refs.get("pedido_bling_numero"),
                "acao": acao,
            },
            db=db,
            auto_fix_applied=True,
        )
        resolver_incidentes_relacionados(
            db,
            tenant_id=pedido.tenant_id,
            codes=[
                "NF_SEM_PEDIDO_VINCULADO",
                "NF_SEM_PEDIDO_LOCAL",
                "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO",
                "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
                "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
            ],
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=refs.get("nf_bling_id"),
            resolution_note="NF autorizada reconciliada automaticamente a partir do cache local.",
        )
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="scheduler",
            event_type="invoice.reconciled_from_cache",
            entity_type="nf",
            status="ok",
            severity="info",
            message="NF autorizada reconciliada a partir do cache local e estoque confirmado.",
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=refs.get("nf_bling_id"),
            payload={
                "nf_numero": refs.get("nf_numero"),
                "numero_pedido_loja": refs.get("numero_pedido_loja"),
                "pedido_bling_numero": pedido.pedido_bling_numero,
                "acao": acao,
            },
            db=db,
            auto_fix_applied=True,
        )
        db.commit()
        return {
            "success": True,
            "motivo": "reconciliada",
            "acao": acao,
            "pedido_id": pedido.id,
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "nf_numero": refs.get("nf_numero"),
            "nf_bling_id": refs.get("nf_bling_id"),
        }
    except Exception as exc:
        db.rollback()
        logger.warning(
            "nfe_auth_reconcile",
            (
                f"Falha ao reconciliar NF {refs.get('nf_numero') or refs.get('nf_bling_id')} "
                f"/ pedido {getattr(pedido, 'pedido_bling_numero', None)}: {exc}"
            ),
        )
        return {
            "success": False,
            "motivo": "falha_reconciliacao",
            "erro": str(exc),
            "pedido_id": pedido.id,
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "nf_numero": refs.get("nf_numero"),
            "nf_bling_id": refs.get("nf_bling_id"),
        }


def reconciliar_nfes_autorizadas_recentes(
    db: Session,
    tenant_id,
    *,
    dias: int = 3,
    limite_notas: int = 200,
) -> dict:
    _garantir_registry_sqlalchemy_reconciliacao()
    registros = _buscar_nfes_autorizadas_recentes(
        db,
        tenant_id,
        dias=dias,
        limite_notas=limite_notas,
    )
    registros = _deduplicar_registros_nfe_por_pedido(registros)
    resultados: list[dict] = []
    reconciliadas = 0

    for registro in registros:
        resultado = reconciliar_nf_autorizada_cache(
            db,
            tenant_id=tenant_id,
            registro=registro,
        )
        resultados.append(resultado)
        if resultado.get("success") and resultado.get("motivo") == "reconciliada":
            reconciliadas += 1

    return {
        "tenant_id": str(tenant_id),
        "dias": dias,
        "limite_notas": limite_notas,
        "notas_avaliadas": len(registros),
        "notas_reconciliadas": reconciliadas,
        "resultados": resultados,
    }


def executar_reconciliacao_automatica_nfes_autorizadas(
    db: Session,
    *,
    dias: int = 3,
    limite_notas_por_tenant: int = 200,
) -> dict:
    tenant_ids = listar_tenants_com_nfes_autorizadas_recentes(db, dias=dias)
    resultados: list[dict] = []

    for tenant_id in tenant_ids:
        try:
            resultados.append(
                reconciliar_nfes_autorizadas_recentes(
                    db,
                    tenant_id,
                    dias=dias,
                    limite_notas=limite_notas_por_tenant,
                )
            )
        except Exception as exc:
            logger.warning(
                "nfe_auth_reconcile",
                f"Falha ao reconciliar tenant {tenant_id}: {exc}",
            )
            db.rollback()
            resultados.append(
                {
                    "tenant_id": str(tenant_id),
                    "erro": str(exc),
                    "dias": dias,
                    "limite_notas": limite_notas_por_tenant,
                }
            )

    return {
        "tenants_processados": len(resultados),
        "tenants_com_notas": len(tenant_ids),
        "notas_reconciliadas_total": sum(int(item.get("notas_reconciliadas") or 0) for item in resultados),
        "resultados": resultados,
    }
