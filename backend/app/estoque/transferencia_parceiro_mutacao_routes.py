"""Mutacoes de transferencia de estoque para parceiro."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_estoque_sync import sincronizar_bling_background
from app.db import get_session
from app.estoque.service import EstoqueService
from app.estoque.transferencia_parceiro_schemas import TransferenciaParceiroRequest
from app.estoque.transferencia_parceiro_support import (
    _MOTIVO_TRANSFERENCIA_PARCEIRO_EDICAO,
    _MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
    _REFERENCIA_TRANSFERENCIA_PARCEIRO_EDICAO,
    _buscar_conta_transferencia_parceiro,
    _gerar_codigo_transferencia_parceiro,
    _montar_observacoes_transferencia_parceiro,
    _obter_dre_subcategoria_receita_padrao,
    _obter_ou_criar_categoria_financeira_transferencia,
    _preparar_itens_transferencia_parceiro,
    _restaurar_lotes_consumidos_transferencia,
    _texto_limpo,
)
from app.financeiro_models import ContaReceber
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao
from app.security.permissions_decorator import require_permission
import logging


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Estoque - Transferencia Parceiro"])

__all__ = [
    "editar_transferencia_parceiro",
    "router",
    "transferir_estoque_para_parceiro",
]


@router.post("/transferencia-parceiro", status_code=status.HTTP_201_CREATED)
@require_permission("produtos.editar")
def transferir_estoque_para_parceiro(
    payload: TransferenciaParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Transfere estoque para um parceiro pelo custo.

    Regras:
    - baixa estoque via FIFO/lotes;
    - nao cria venda nem entra no faturamento do PDV;
    - gera um contas a receber separado para o ressarcimento do parceiro.
    """
    current_user, tenant_id = user_and_tenant

    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == payload.parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    itens_validos = [item for item in payload.itens if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    codigo_transferencia = (
        _texto_limpo(payload.documento) or _gerar_codigo_transferencia_parceiro()
    )
    conta_existente = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.documento == codigo_transferencia,
        )
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um registro financeiro com este documento",
        )

    try:
        itens_processados, total_transferencia = _preparar_itens_transferencia_parceiro(
            db,
            tenant_id=tenant_id,
            itens_validos=itens_validos,
        )

        categoria_financeira = _obter_ou_criar_categoria_financeira_transferencia(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        dre_subcategoria_id = (
            categoria_financeira.dre_subcategoria_id
            or _obter_dre_subcategoria_receita_padrao(db, tenant_id)
        )

        conta_receber = ContaReceber(
            tenant_id=str(tenant_id),
            descricao=f"Transferencia para parceiro - {parceiro.nome}",
            cliente_id=parceiro.id,
            categoria_id=categoria_financeira.id,
            dre_subcategoria_id=dre_subcategoria_id,
            canal="transferencia_parceiro",
            valor_original=total_transferencia,
            valor_recebido=Decimal("0"),
            valor_final=total_transferencia,
            data_emissao=date.today(),
            data_vencimento=payload.data_vencimento or date.today(),
            status="pendente",
            documento=codigo_transferencia,
            observacoes=_montar_observacoes_transferencia_parceiro(
                payload.observacao,
                itens_processados,
            ),
            user_id=current_user.id,
        )
        db.add(conta_receber)
        db.flush()

        for item in itens_processados:
            observacao_item = (
                f"Transferencia para parceiro {parceiro.nome} pelo custo. "
                f"Conta a receber #{conta_receber.id}."
            )
            if payload.observacao:
                observacao_item = f"{observacao_item} {payload.observacao}"

            resultado_baixa = EstoqueService.baixar_estoque(
                produto_id=item["produto_id"],
                quantidade=item["quantidade"],
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                referencia_id=conta_receber.id,
                referencia_tipo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=codigo_transferencia,
                observacao=observacao_item,
                custo_unitario_override=item["custo_unitario"],
                valor_total_override=item["total_item"],
            )
            item["movimentacao_id"] = resultado_baixa["movimentacao_id"]
            item["estoque_novo"] = resultado_baixa["estoque_novo"]

        db.commit()

        for item in itens_processados:
            try:
                sincronizar_bling_background(
                    item["produto_id"],
                    item["estoque_novo"],
                    "transferencia_parceiro",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "documento": codigo_transferencia,
            "conta_receber_id": conta_receber.id,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "codigo": getattr(parceiro, "codigo", None),
                "email": getattr(parceiro, "email", None),
            },
            "data_vencimento": conta_receber.data_vencimento.isoformat()
            if conta_receber.data_vencimento
            else None,
            "total_ressarcimento": float(total_transferencia),
            "itens": itens_processados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao registrar transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel registrar a transferencia para parceiro",
        )


@router.put("/transferencia-parceiro/{conta_receber_id}")
@require_permission("produtos.editar")
def editar_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Edita uma transferencia ainda sem baixa, preservando estoque e financeiro."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)

    if float(conta.valor_recebido or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta transferencia ja possui recebimento registrado. "
                "Remova ou trate a baixa financeira antes de editar o lancamento."
            ),
        )

    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    if status_atual in {"cancelado", "cancelada"}:
        raise HTTPException(
            status_code=400,
            detail="Transferencia cancelada nao pode ser editada.",
        )

    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == payload.parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    itens_validos = [item for item in payload.itens if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    codigo_transferencia = (
        _texto_limpo(payload.documento)
        or _texto_limpo(conta.documento)
        or _gerar_codigo_transferencia_parceiro()
    )
    conta_existente = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.documento == codigo_transferencia,
            ContaReceber.id != conta.id,
        )
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um registro financeiro com este documento",
        )

    movimentacoes_anteriores = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id == conta.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )

    try:
        estoques_finais: dict[int, float] = {}
        produtos_tocados: set[int] = set()
        lotes_restaurados = 0

        for movimentacao in movimentacoes_anteriores:
            produtos_tocados.add(int(movimentacao.produto_id))
            lotes_restaurados += _restaurar_lotes_consumidos_transferencia(
                db, movimentacao
            )
            resultado_estorno = EstoqueService.estornar_estoque(
                produto_id=movimentacao.produto_id,
                quantidade=float(movimentacao.quantidade or 0),
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_EDICAO,
                referencia_id=conta.id,
                referencia_tipo=_REFERENCIA_TRANSFERENCIA_PARCEIRO_EDICAO,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=conta.documento,
                observacao=(
                    f"Estorno temporario para edicao da transferencia "
                    f"{conta.documento or conta.id}"
                ),
                custo_unitario_override=float(movimentacao.custo_unitario or 0),
                valor_total_override=float(movimentacao.valor_total or 0),
            )
            estoques_finais[int(movimentacao.produto_id)] = resultado_estorno[
                "estoque_novo"
            ]
            db.delete(movimentacao)

        db.flush()

        itens_processados, total_transferencia = _preparar_itens_transferencia_parceiro(
            db,
            tenant_id=tenant_id,
            itens_validos=itens_validos,
        )

        categoria_financeira = None
        if not conta.categoria_id or not conta.dre_subcategoria_id:
            categoria_financeira = _obter_ou_criar_categoria_financeira_transferencia(
                db,
                tenant_id=tenant_id,
                user_id=current_user.id,
            )

        if not conta.categoria_id and categoria_financeira:
            conta.categoria_id = categoria_financeira.id
        if not conta.dre_subcategoria_id:
            conta.dre_subcategoria_id = (
                categoria_financeira.dre_subcategoria_id
                if categoria_financeira
                else None
            ) or _obter_dre_subcategoria_receita_padrao(db, tenant_id)

        conta.descricao = f"Transferencia para parceiro - {parceiro.nome}"
        conta.cliente_id = parceiro.id
        conta.canal = "transferencia_parceiro"
        conta.valor_original = total_transferencia
        conta.valor_final = total_transferencia
        conta.valor_recebido = Decimal("0")
        conta.data_vencimento = (
            payload.data_vencimento or conta.data_vencimento or date.today()
        )
        conta.status = "pendente"
        conta.documento = codigo_transferencia
        conta.observacoes = _montar_observacoes_transferencia_parceiro(
            payload.observacao,
            itens_processados,
        )
        db.add(conta)
        db.flush()

        for item in itens_processados:
            produtos_tocados.add(int(item["produto_id"]))
            observacao_item = (
                f"Transferencia para parceiro {parceiro.nome} pelo custo. "
                f"Conta a receber #{conta.id}. Editada."
            )
            if payload.observacao:
                observacao_item = f"{observacao_item} {payload.observacao}"

            resultado_baixa = EstoqueService.baixar_estoque(
                produto_id=item["produto_id"],
                quantidade=item["quantidade"],
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                referencia_id=conta.id,
                referencia_tipo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=codigo_transferencia,
                observacao=observacao_item,
                custo_unitario_override=item["custo_unitario"],
                valor_total_override=item["total_item"],
            )
            item["movimentacao_id"] = resultado_baixa["movimentacao_id"]
            item["estoque_novo"] = resultado_baixa["estoque_novo"]
            estoques_finais[int(item["produto_id"])] = resultado_baixa["estoque_novo"]

        db.commit()

        for produto_id in produtos_tocados:
            estoque_novo = estoques_finais.get(produto_id)
            if estoque_novo is None:
                continue
            try:
                sincronizar_bling_background(
                    produto_id,
                    estoque_novo,
                    "transferencia_parceiro_edicao",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (edicao transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "editado": True,
            "documento": codigo_transferencia,
            "conta_receber_id": conta.id,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "codigo": getattr(parceiro, "codigo", None),
                "email": getattr(parceiro, "email", None),
            },
            "data_vencimento": conta.data_vencimento.isoformat()
            if conta.data_vencimento
            else None,
            "total_ressarcimento": float(total_transferencia),
            "lotes_restaurados": lotes_restaurados,
            "itens": itens_processados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao editar transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel editar a transferencia para parceiro",
        )
