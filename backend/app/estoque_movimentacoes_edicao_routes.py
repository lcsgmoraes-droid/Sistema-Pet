"""
Rotas de edicao e exclusao de movimentacoes de estoque.
"""

import json
import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_estoque_sync import sincronizar_bling_background
from app.db import get_session
from app.produtos_models import (
    EstoqueMovimentacao,
    Produto,
    ProdutoKitComponente,
    ProdutoLote,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])

REFERENCIAS_AUTOMATICAS_PROTEGIDAS = {
    "fracionamento_clinico",
    "procedimento_veterinario",
    "procedimento_internacao",
}


def _buscar_movimentacao(db: Session, movimentacao_id: int, tenant_id: int):
    movimentacao = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.id == movimentacao_id,
            EstoqueMovimentacao.tenant_id == tenant_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentacao nao encontrada")
    return movimentacao


def _validar_movimentacao_editavel(movimentacao) -> None:
    if movimentacao.referencia_tipo in REFERENCIAS_AUTOMATICAS_PROTEGIDAS:
        raise HTTPException(
            status_code=409,
            detail=(
                "Movimentacao automatica protegida. Corrija ou estorne pelo fluxo "
                "clinico que originou o lancamento."
            ),
        )


def _buscar_produto(db: Session, produto_id: int, tenant_id: int, *, bloquear=False):
    query = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
    )
    if bloquear:
        query = query.with_for_update().populate_existing()
    return query.first()


def _buscar_produto_obrigatorio(db: Session, produto_id: int, tenant_id: int):
    produto = _buscar_produto(db, produto_id, tenant_id, bloquear=True)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return produto


def _buscar_lote(db: Session, lote_id: int, movimentacao):
    return (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.id == lote_id,
            ProdutoLote.produto_id == movimentacao.produto_id,
            ProdutoLote.tenant_id == movimentacao.tenant_id,
        )
        .with_for_update()
        .first()
    )


def _movimentacao_retorna_componentes(movimentacao) -> bool:
    return (
        movimentacao.tipo == "saida"
        and movimentacao.observacao
        and "componentes retornados" in movimentacao.observacao.lower()
    )


def _registrar_componente_estornado(
    componentes_estornados,
    componente_produto,
    quantidade,
    estoque_anterior,
    acao: str,
):
    componentes_estornados.append(
        {
            "nome": componente_produto.nome,
            "quantidade": quantidade,
            "estoque_anterior": estoque_anterior,
            "estoque_novo": componente_produto.estoque_atual,
            "acao": acao,
        }
    )


def _ajustar_componente_kit(
    componentes_estornados,
    componente_produto,
    quantidade,
    delta,
    acao: str,
    log_acao: str,
):
    estoque_anterior = componente_produto.estoque_atual
    componente_produto.estoque_atual += delta
    sinal = "+" if delta >= 0 else "-"
    logger.info(
        "%s: %s -> %s (%s%s) [%s]",
        componente_produto.nome,
        estoque_anterior,
        componente_produto.estoque_atual,
        sinal,
        quantidade,
        log_acao,
    )
    _registrar_componente_estornado(
        componentes_estornados,
        componente_produto,
        quantidade,
        estoque_anterior,
        acao,
    )


def _estornar_componentes_kit_fisico(
    db: Session, produto, movimentacao, tenant_id: int
):
    componentes_estornados = []
    if produto.tipo_produto != "KIT" or produto.tipo_kit != "FISICO":
        return componentes_estornados

    componentes_kit = (
        db.query(ProdutoKitComponente)
        .filter(
            ProdutoKitComponente.kit_id == produto.id,
        )
        .all()
    )
    if not componentes_kit:
        return componentes_estornados

    logger.info("KIT FISICO detectado - Estornando componentes...")
    for comp in componentes_kit:
        componente_produto = _buscar_produto(
            db,
            comp.produto_componente_id,
            tenant_id,
        )
        if not componente_produto:
            continue

        quantidade_componente = comp.quantidade * movimentacao.quantidade
        if movimentacao.tipo == "entrada":
            _ajustar_componente_kit(
                componentes_estornados,
                componente_produto,
                quantidade_componente,
                quantidade_componente,
                "devolvido",
                "devolvido",
            )
        elif _movimentacao_retorna_componentes(movimentacao):
            _ajustar_componente_kit(
                componentes_estornados,
                componente_produto,
                quantidade_componente,
                -quantidade_componente,
                "estornado",
                "estornando retorno",
            )

    logger.info("KIT FISICO: %s componentes estornados", len(componentes_estornados))
    return componentes_estornados


def _reverter_estoque_produto(produto, movimentacao):
    estoque_anterior = produto.estoque_atual
    if movimentacao.tipo == "entrada":
        delta = -movimentacao.quantidade
    elif movimentacao.tipo == "saida":
        delta = movimentacao.quantidade
    else:
        return

    if estoque_anterior + delta < -1e-9:
        raise HTTPException(
            status_code=400, detail="A exclusao deixaria o estoque negativo"
        )
    produto.estoque_atual += delta
    sinal = "+" if delta >= 0 else "-"
    logger.info(
        "Estoque %s: %s -> %s (%s%s)",
        produto.nome,
        estoque_anterior,
        produto.estoque_atual,
        sinal,
        movimentacao.quantidade,
    )


def _lotes_consumidos_saida(db: Session, movimentacao):
    """Resolve somente lotes do produto e tenant da movimentacao."""
    if not movimentacao.lotes_consumidos:
        return []
    try:
        consumidos = json.loads(movimentacao.lotes_consumidos)
        if not isinstance(consumidos, list):
            raise ValueError("Formato de lotes invalido")
        resolvidos = []
        for item in consumidos:
            lote = (
                db.query(ProdutoLote)
                .filter(
                    ProdutoLote.id == int(item["lote_id"]),
                    ProdutoLote.produto_id == movimentacao.produto_id,
                    ProdutoLote.tenant_id == movimentacao.tenant_id,
                )
                .with_for_update()
                .first()
            )
            if lote is None:
                raise ValueError("Lote de origem nao encontrado")
            quantidade = float(item["quantidade"])
            if not math.isfinite(quantidade) or quantidade <= 0:
                raise ValueError("Quantidade de lote invalida")
            resolvidos.append((lote, quantidade))
        return resolvidos
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail="Historico de lotes invalido; regularize antes de alterar a saida",
        ) from exc


def _restaurar_lotes_saida(db: Session, movimentacao):
    lotes = _lotes_consumidos_saida(db, movimentacao)
    for lote, quantidade in lotes:
        lote.quantidade_disponivel += quantidade
        lote.status = "ativo"
    return bool(lotes)


def _reverter_lote_por_exclusao(db: Session, movimentacao):
    if movimentacao.tipo == "saida" and _restaurar_lotes_saida(db, movimentacao):
        return
    if not movimentacao.lote_id:
        return

    lote = _buscar_lote(db, movimentacao.lote_id, movimentacao)
    if not lote:
        return

    if movimentacao.tipo == "entrada":
        if lote.quantidade_disponivel - movimentacao.quantidade < -1e-9:
            raise HTTPException(
                status_code=400, detail="O lote desta entrada ja foi consumido"
            )
        lote.quantidade_disponivel -= movimentacao.quantidade
        lote.quantidade_inicial -= movimentacao.quantidade
        if lote.quantidade_disponivel <= 0:
            lote.status = "esgotado"
    elif movimentacao.tipo == "saida":
        lote.quantidade_disponivel += movimentacao.quantidade
        lote.status = "ativo"


def _ajustar_lote_por_edicao(db: Session, movimentacao, diferenca):
    if not movimentacao.lote_id:
        return

    lote = _buscar_lote(db, movimentacao.lote_id, movimentacao)
    if not lote:
        return

    if movimentacao.tipo == "entrada":
        if lote.quantidade_disponivel + diferenca < -1e-9:
            raise HTTPException(
                status_code=400,
                detail="A quantidade informada e menor que o consumo do lote",
            )
        lote.quantidade_disponivel += diferenca
        lote.quantidade_inicial += diferenca
        lote.status = "ativo" if lote.quantidade_disponivel > 0 else "esgotado"
    elif movimentacao.tipo == "saida":
        lote.quantidade_disponivel -= diferenca


def _aplicar_edicao_quantidade(produto, movimentacao, quantidade_nova, db: Session):
    diferenca = quantidade_nova - movimentacao.quantidade
    delta = diferenca if movimentacao.tipo == "entrada" else -diferenca
    if produto.estoque_atual + delta < -1e-9:
        raise HTTPException(
            status_code=400, detail="A quantidade informada deixaria o estoque negativo"
        )
    if movimentacao.tipo == "entrada":
        produto.estoque_atual += diferenca
    elif movimentacao.tipo == "saida":
        produto.estoque_atual -= diferenca

    if movimentacao.tipo == "saida" and movimentacao.lotes_consumidos:
        _restaurar_lotes_saida(db, movimentacao)
        lotes = (
            db.query(ProdutoLote)
            .filter(
                ProdutoLote.produto_id == produto.id,
                ProdutoLote.tenant_id == movimentacao.tenant_id,
            )
            .order_by(ProdutoLote.ordem_entrada, ProdutoLote.id)
            .with_for_update()
            .all()
        )
        restante = quantidade_nova
        consumidos = []
        for lote in lotes:
            if restante <= 0:
                break
            disponivel = float(lote.quantidade_disponivel or 0)
            if disponivel <= 0 or lote.status != "ativo":
                continue
            retirar = min(disponivel, restante)
            lote.quantidade_disponivel -= retirar
            restante -= retirar
            if lote.quantidade_disponivel <= 0:
                lote.status = "esgotado"
            consumidos.append(
                {
                    "lote_id": lote.id,
                    "nome_lote": lote.nome_lote,
                    "quantidade": retirar,
                    "saldo_anterior": disponivel,
                }
            )
        movimentacao.lotes_consumidos = json.dumps(consumidos)
    else:
        _ajustar_lote_por_edicao(db, movimentacao, diferenca)
    movimentacao.quantidade = quantidade_nova
    movimentacao.quantidade_nova = produto.estoque_atual


def _agendar_sync_bling(produto, origem: str, log_contexto: str):
    try:
        sincronizar_bling_background(produto.id, produto.estoque_atual, origem)
    except Exception as e_sync:
        logger.warning(
            "[BLING-SYNC] Erro ao agendar sync (%s): %s",
            log_contexto,
            e_sync,
        )


@router.delete("/movimentacoes/{movimentacao_id}")
def excluir_movimentacao(
    movimentacao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui uma movimentacao de estoque e reverte o efeito no produto.
    """
    _current_user, tenant_id = user_and_tenant
    try:
        movimentacao = _buscar_movimentacao(db, movimentacao_id, tenant_id)
        _validar_movimentacao_editavel(movimentacao)
        produto = _buscar_produto_obrigatorio(db, movimentacao.produto_id, tenant_id)

        logger.info(
            "Excluindo movimentacao %s - Tipo: %s, Qtd: %s",
            movimentacao_id,
            movimentacao.tipo,
            movimentacao.quantidade,
        )

        componentes_estornados = _estornar_componentes_kit_fisico(
            db,
            produto,
            movimentacao,
            tenant_id,
        )
        _reverter_estoque_produto(produto, movimentacao)
        _reverter_lote_por_exclusao(db, movimentacao)

        db.delete(movimentacao)
        db.commit()

        logger.info("Movimentacao excluida")

        _agendar_sync_bling(produto, "exclusao_movimentacao", "exclusao_mov")

        return {
            "message": "Movimentacao excluida com sucesso",
            "componentes_estornados": componentes_estornados,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Erro ao excluir movimentacao: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class UpdateMovimentacaoRequest(BaseModel):
    quantidade: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    custo_unitario: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    observacao: Optional[str] = None


@router.patch("/movimentacoes/{movimentacao_id}")
def editar_movimentacao(
    movimentacao_id: int,
    dados: UpdateMovimentacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Edita uma movimentacao existente.
    """
    _current_user, tenant_id = user_and_tenant
    try:
        movimentacao = _buscar_movimentacao(db, movimentacao_id, tenant_id)
        _validar_movimentacao_editavel(movimentacao)
        produto = _buscar_produto_obrigatorio(db, movimentacao.produto_id, tenant_id)

        if dados.quantidade is not None and dados.quantidade != movimentacao.quantidade:
            _aplicar_edicao_quantidade(produto, movimentacao, dados.quantidade, db)

        if dados.custo_unitario is not None:
            movimentacao.custo_unitario = dados.custo_unitario
        if dados.quantidade is not None or dados.custo_unitario is not None:
            movimentacao.valor_total = (
                movimentacao.quantidade * movimentacao.custo_unitario
                if movimentacao.custo_unitario is not None
                else None
            )

        if dados.observacao is not None:
            movimentacao.observacao = dados.observacao

        db.commit()
        db.refresh(movimentacao)

        logger.info("Movimentacao editada")

        if dados.quantidade is not None:
            _agendar_sync_bling(produto, "edicao_movimentacao", "edicao_mov")

        return {
            "id": movimentacao.id,
            "quantidade": movimentacao.quantidade,
            "custo_unitario": movimentacao.custo_unitario,
            "observacao": movimentacao.observacao,
            "estoque_atual_produto": produto.estoque_atual,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Erro ao editar movimentacao: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
