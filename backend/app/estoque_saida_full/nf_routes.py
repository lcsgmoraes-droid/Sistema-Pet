"""Rotas de baixa FULL por NF."""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from ..auth.dependencies import get_current_user_and_tenant
from ..bling_estoque_sync import sincronizar_bling_background
from ..db import get_session
from ..financeiro_models import ContaPagar, LancamentoManual
from ..produtos_models import EstoqueMovimentacao
from .common import _CANAL_LABELS, _texto_limpo
from .estoque import (
    _problemas_estoque_saida_full_nf,
    _processar_item_saida_full_nf,
    _sku_produto,
    _validar_estoque_saida_full_nf,
)
from .financeiro import (
    _buscar_conta_tarifa_full_nf,
    _criar_conta_pagar_tarifa_full_nf,
    _observacao_conta_tarifa_full_nf_com_canal,
    _resolver_classificacao_tarifa_full_nf,
)
from .schemas import (
    SaidaFullNFCanalUpdateRequest,
    SaidaFullNFRequest,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def _observacao_full_nf(
    numero_nf: str, plataforma: Optional[str], observacao: Optional[str]
) -> str:
    base = f"Saida FULL por NF {numero_nf} | plataforma: {plataforma or 'full'}"
    if observacao:
        return f"{base} | {observacao}"
    return base


def _observacao_full_nf_com_canal_atualizado(
    numero_nf: str,
    observacao: Optional[str],
    plataforma: str,
) -> str:
    texto = _texto_limpo(observacao)
    if texto:
        if re.search(r"plataforma:\s*[^|]+", texto, flags=re.IGNORECASE):
            return re.sub(
                r"plataforma:\s*[^|]+",
                f"plataforma: {plataforma}",
                texto,
                count=1,
                flags=re.IGNORECASE,
            )
        return f"{texto} | plataforma: {plataforma}"
    return _observacao_full_nf(numero_nf, plataforma, None)


def _canal_saida_full_por_observacao(observacao: Optional[str]) -> Optional[str]:
    texto = _texto_limpo(observacao)
    if not texto:
        return None
    match = re.search(r"plataforma:\s*([^|]+)", texto, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().lower() or None


def _buscar_baixas_full_nf(db: Session, tenant_id, numero_nf: str):
    return (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.documento == numero_nf,
            EstoqueMovimentacao.motivo == "full_nfe_saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.created_at.desc(), EstoqueMovimentacao.id.desc())
        .all()
    )


@router.get("/saida-full-nf/historico")
def historico_saida_full_por_nf(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista baixas FULL por NF ja processadas, agrupadas por NF."""
    _current_user, tenant_id = user_and_tenant

    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .options(joinedload(EstoqueMovimentacao.produto))
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.motivo == "full_nfe_saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(
            desc(EstoqueMovimentacao.created_at),
            desc(EstoqueMovimentacao.id),
        )
        .limit(max(limit * 30, 300))
        .all()
    )

    grupos = {}
    for mov in movimentacoes:
        documento = _texto_limpo(mov.documento) or f"MOV-{mov.id}"
        canal = _canal_saida_full_por_observacao(mov.observacao) or "full"
        if documento not in grupos:
            grupos[documento] = {
                "numero_nf": documento,
                "processado_em": mov.created_at.isoformat() if mov.created_at else None,
                "plataforma": canal,
                "plataforma_label": _CANAL_LABELS.get(canal, canal),
                "observacao": mov.observacao,
                "total_itens": 0,
                "baixas_estoque": 0,
                "lancamentos_financeiros": 0,
                "valor_estoque": 0.0,
                "itens": [],
                "tarifa_envio": None,
            }

        grupo = grupos[documento]
        grupo["total_itens"] += 1
        grupo["baixas_estoque"] += 1
        grupo["valor_estoque"] += float(mov.valor_total or 0)
        grupo["itens"].append(
            {
                "movimentacao_id": mov.id,
                "produto_id": mov.produto_id,
                "sku": _sku_produto(mov.produto) if mov.produto else None,
                "nome": mov.produto.nome if mov.produto else None,
                "quantidade": float(mov.quantidade or 0),
                "estoque_anterior": float(mov.quantidade_anterior or 0),
                "estoque_novo": float(mov.quantidade_nova or 0),
            }
        )

    documentos = list(grupos.keys())
    if documentos:
        contas_tarifa = (
            db.query(ContaPagar)
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.documento.in_(documentos),
                ContaPagar.descricao.ilike("Tarifa envio FULL NF%"),
            )
            .all()
        )

        for conta in contas_tarifa:
            documento = _texto_limpo(conta.documento)
            if not documento or documento not in grupos:
                continue
            grupo = grupos[documento]
            grupo["lancamentos_financeiros"] += 1
            canal = _texto_limpo(conta.canal)
            if canal:
                grupo["plataforma"] = canal
                grupo["plataforma_label"] = _CANAL_LABELS.get(canal, canal)
            valor = float(conta.valor_final or conta.valor_original or 0)
            if not grupo["tarifa_envio"]:
                grupo["tarifa_envio"] = {
                    "conta_pagar_id": conta.id,
                    "valor": valor,
                    "status": conta.status,
                    "data_vencimento": conta.data_vencimento.isoformat()
                    if conta.data_vencimento
                    else None,
                }

    items = list(grupos.values())[:limit]
    return {"items": items, "total": len(grupos)}


@router.put("/saida-full-nf/{numero_nf}/canal")
def atualizar_canal_saida_full_por_nf(
    numero_nf: str,
    payload: SaidaFullNFCanalUpdateRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Corrige canal/origem de uma baixa FULL ja processada."""
    _current_user, tenant_id = user_and_tenant
    canal = (payload.plataforma or "").strip().lower()
    if not canal:
        raise HTTPException(status_code=400, detail="Selecione o novo canal/origem.")
    if canal not in _CANAL_LABELS:
        raise HTTPException(status_code=400, detail="Canal/origem invalido.")

    baixas = _buscar_baixas_full_nf(db, tenant_id, numero_nf)
    if not baixas:
        raise HTTPException(
            status_code=404, detail=f"Nenhuma baixa encontrada para a NF {numero_nf}."
        )

    canal_anterior = _canal_saida_full_por_observacao(baixas[0].observacao)
    plataforma_label = _CANAL_LABELS.get(canal, canal)
    for movimentacao in baixas:
        movimentacao.observacao = _observacao_full_nf_com_canal_atualizado(
            numero_nf,
            movimentacao.observacao,
            canal,
        )

    conta_tarifa = _buscar_conta_tarifa_full_nf(db, tenant_id, numero_nf)
    lancamentos_financeiros = 0
    if conta_tarifa:
        conta_tarifa.canal = canal
        conta_tarifa.observacoes = _observacao_conta_tarifa_full_nf_com_canal(
            conta_tarifa.observacoes,
            plataforma_label,
        )
        lancamentos_financeiros = 1

        lancamentos_manuais = (
            db.query(LancamentoManual)
            .filter(
                LancamentoManual.tenant_id == tenant_id,
                LancamentoManual.documento == numero_nf,
                LancamentoManual.descricao == f"Tarifa envio FULL NF {numero_nf}",
            )
            .all()
        )
        for lancamento in lancamentos_manuais:
            lancamento.observacoes = (
                f"Gerado automaticamente da conta a pagar #{conta_tarifa.id}. "
                f"Canal/origem corrigido para {plataforma_label}."
            )

    db.commit()

    return {
        "success": True,
        "message": f"Canal da NF {numero_nf} atualizado para {plataforma_label}.",
        "numero_nf": numero_nf,
        "plataforma": canal,
        "plataforma_label": plataforma_label,
        "plataforma_anterior": canal_anterior,
        "plataforma_anterior_label": _CANAL_LABELS.get(canal_anterior, canal_anterior)
        if canal_anterior
        else None,
        "baixas_estoque": len(baixas),
        "lancamentos_financeiros": lancamentos_financeiros,
        "total_itens": len(baixas),
        "tarifa_envio": (
            {
                "conta_pagar_id": conta_tarifa.id,
                "valor": float(
                    conta_tarifa.valor_final or conta_tarifa.valor_original or 0
                ),
            }
            if conta_tarifa
            else None
        ),
    }


@router.post("/saida-full-nf/validar-estoque")
def validar_estoque_saida_full_por_nf(
    payload: SaidaFullNFRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Valida se os itens da NF possuem estoque suficiente, sem gerar baixa."""
    _current_user, tenant_id = user_and_tenant
    itens_validos = [
        item for item in payload.itens if item.quantidade and item.quantidade > 0
    ]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    problemas = _problemas_estoque_saida_full_nf(db, tenant_id, itens_validos)
    return {
        "ok": len(problemas) == 0,
        "total_itens": len(itens_validos),
        "problemas": problemas,
    }


@router.post("/saida-full-nf", status_code=status.HTTP_201_CREATED)
def saida_full_por_nf(
    payload: SaidaFullNFRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Baixa estoque em lote por NF de saida (operacao FULL).

    Regras:
    - Cada item baixa apenas estoque (sem gerar financeiro).
    - Se qualquer item falhar, toda a transacao e cancelada.
    """
    current_user, tenant_id = user_and_tenant

    canal = (payload.plataforma or "").strip().lower()
    canais_validos = set(_CANAL_LABELS.keys())
    if not canal:
        raise HTTPException(
            status_code=400, detail="Selecione o canal/origem da movimentacao FULL."
        )
    if canal not in canais_validos:
        raise HTTPException(
            status_code=400, detail="Canal/origem da movimentacao FULL invalido."
        )
    payload.plataforma = canal

    itens_validos = [
        item for item in payload.itens if item.quantidade and item.quantidade > 0
    ]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    processados = []
    observacao_movimentacao = _observacao_full_nf(
        payload.numero_nf, payload.plataforma, payload.observacao
    )
    tarifa_valor = float(payload.tarifa_envio or 0)
    baixas_existentes = _buscar_baixas_full_nf(db, tenant_id, payload.numero_nf)
    classificacao_tarifa = None
    if tarifa_valor > 0:
        classificacao_tarifa = _resolver_classificacao_tarifa_full_nf(
            db,
            tenant_id,
            categoria_tarifa_id=payload.categoria_tarifa_id,
            dre_subcategoria_tarifa_id=payload.dre_subcategoria_tarifa_id,
        )

    try:
        if baixas_existentes:
            conta_tarifa_existente = _buscar_conta_tarifa_full_nf(
                db, tenant_id, payload.numero_nf
            )

            if tarifa_valor > 0 and classificacao_tarifa and not conta_tarifa_existente:
                categoria_tarifa, subcategoria_tarifa = classificacao_tarifa
                conta_tarifa = _criar_conta_pagar_tarifa_full_nf(
                    db,
                    tenant_id=tenant_id,
                    current_user=current_user,
                    payload=payload,
                    categoria=categoria_tarifa,
                    subcategoria=subcategoria_tarifa,
                )
                db.commit()
                return {
                    "success": True,
                    "message": (
                        f"NF {payload.numero_nf} ja tinha baixa de estoque. "
                        "Apenas a tarifa pendente foi lancada no financeiro."
                    ),
                    "numero_nf": payload.numero_nf,
                    "plataforma": payload.plataforma,
                    "plataforma_label": _CANAL_LABELS.get(
                        payload.plataforma, payload.plataforma
                    ),
                    "estoque_ja_baixado": True,
                    "baixas_estoque": 0,
                    "lancamentos_financeiros": 1,
                    "total_itens": len(baixas_existentes),
                    "itens": [
                        {
                            "produto_id": mov.produto_id,
                            "sku": None,
                            "nome": None,
                            "quantidade": float(mov.quantidade or 0),
                            "estoque_anterior": float(mov.quantidade_anterior or 0),
                            "estoque_novo": float(mov.quantidade_nova or 0),
                        }
                        for mov in baixas_existentes
                    ],
                    "tarifa_envio": {
                        "conta_pagar_id": conta_tarifa.id,
                        "valor": tarifa_valor,
                    },
                }

            detalhe_tarifa = (
                " A tarifa de envio ja esta lancada no financeiro."
                if conta_tarifa_existente
                else " Se ficou faltando tarifa, informe valor e categoria com DRE para lancar somente o financeiro."
            )
            raise HTTPException(
                status_code=409,
                detail=(
                    f"NF {payload.numero_nf} ja possui baixa de estoque registrada. "
                    f"O sistema bloqueou o reprocessamento para evitar baixa duplicada.{detalhe_tarifa}"
                ),
            )

        if not payload.permitir_estoque_negativo:
            _validar_estoque_saida_full_nf(db, tenant_id, itens_validos)

        for item in itens_validos:
            processados.append(
                _processar_item_saida_full_nf(
                    db=db,
                    tenant_id=tenant_id,
                    item=item,
                    numero_nf=payload.numero_nf,
                    observacao_movimentacao=observacao_movimentacao,
                    current_user=current_user,
                    permitir_estoque_negativo=payload.permitir_estoque_negativo,
                )
            )

        conta_tarifa = None
        if classificacao_tarifa:
            categoria_tarifa, subcategoria_tarifa = classificacao_tarifa
            conta_tarifa = _criar_conta_pagar_tarifa_full_nf(
                db,
                tenant_id=tenant_id,
                current_user=current_user,
                payload=payload,
                categoria=categoria_tarifa,
                subcategoria=subcategoria_tarifa,
            )

        db.commit()

        for item in processados:
            sync_itens = item.get("sync_itens") or [
                {
                    "produto_id": item["produto_id"],
                    "estoque_novo": item["estoque_novo"],
                }
            ]
            for sync_item in sync_itens:
                try:
                    sincronizar_bling_background(
                        sync_item["produto_id"],
                        sync_item["estoque_novo"],
                        "saida_full_nfe",
                    )
                except Exception as e_sync:
                    logger.warning(
                        f"[BLING-SYNC] Erro ao agendar sync (saida-full-nf): {e_sync}"
                    )

        return {
            "success": True,
            "message": "Baixa de estoque por NF concluida",
            "numero_nf": payload.numero_nf,
            "plataforma": payload.plataforma,
            "plataforma_label": _CANAL_LABELS.get(
                payload.plataforma, payload.plataforma
            ),
            "baixas_estoque": len(processados),
            "lancamentos_financeiros": 1 if conta_tarifa else 0,
            "total_itens": len(processados),
            "itens": processados,
            "tarifa_envio": (
                {
                    "conta_pagar_id": conta_tarifa.id,
                    "valor": tarifa_valor,
                }
                if conta_tarifa
                else None
            ),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro na baixa FULL por NF: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar baixa por NF: {str(e)}"
        )
