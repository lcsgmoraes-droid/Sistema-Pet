from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_custos_helpers import dec
from app.banho_tosa_models import BanhoTosaAtendimento, BanhoTosaInsumoUsado
from app.estoque.service import EstoqueService
from app.models import Cliente
from app.produtos_models import Produto


def query_insumos(db: Session, tenant_id, atendimento_id: int):
    return (
        db.query(BanhoTosaInsumoUsado)
        .options(joinedload(BanhoTosaInsumoUsado.produto), joinedload(BanhoTosaInsumoUsado.responsavel))
        .filter(
            BanhoTosaInsumoUsado.tenant_id == tenant_id,
            BanhoTosaInsumoUsado.atendimento_id == atendimento_id,
        )
    )


def obter_atendimento_ou_404(db: Session, tenant_id, atendimento_id: int):
    atendimento = db.query(BanhoTosaAtendimento).filter(
        BanhoTosaAtendimento.id == atendimento_id,
        BanhoTosaAtendimento.tenant_id == tenant_id,
    ).first()
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado")
    return atendimento


def obter_insumo_ou_404(db: Session, tenant_id, atendimento_id: int, insumo_id: int):
    insumo = query_insumos(db, tenant_id, atendimento_id).filter(BanhoTosaInsumoUsado.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo nao encontrado")
    return insumo


def obter_produto_ou_404(db: Session, tenant_id, produto_id: int):
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == str(tenant_id),
        Produto.ativo == True,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return produto


def validar_responsavel(db: Session, tenant_id, responsavel_id: int | None):
    if not responsavel_id:
        return
    pessoa = db.query(Cliente).filter(Cliente.id == responsavel_id, Cliente.tenant_id == tenant_id).first()
    if not pessoa:
        raise HTTPException(status_code=404, detail="Responsavel nao encontrado")


def validar_edicao_insumo(insumo: BanhoTosaInsumoUsado, payload: dict):
    if not insumo.movimentacao_estoque_id or insumo.movimentacao_estorno_id:
        return
    campos_protegidos = {"quantidade_usada", "quantidade_desperdicio", "custo_unitario_snapshot"}
    if campos_protegidos.intersection(payload):
        raise HTTPException(
            status_code=422,
            detail="Estorne a baixa de estoque antes de alterar quantidades ou custo.",
        )


def baixar_estoque_insumo(user, tenant_id, atendimento_id: int, produto, quantidade, custo_unitario, db: Session):
    try:
        movimento = EstoqueService.baixar_estoque(
            produto_id=produto.id,
            quantidade=float(quantidade),
            motivo="banho_tosa_insumo",
            referencia_id=atendimento_id,
            referencia_tipo="banho_tosa_atendimento",
            user_id=user.id,
            db=db,
            tenant_id=str(tenant_id),
            documento=f"BT-{atendimento_id}",
            observacao="Consumo registrado no atendimento de Banho & Tosa",
            custo_unitario_override=float(custo_unitario or 0),
        )
        return movimento.get("movimentacao_id")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def estornar_estoque_insumo_registrado(user, tenant_id, atendimento_id: int, insumo, db: Session):
    quantidade_total = dec(insumo.quantidade_usada) + dec(insumo.quantidade_desperdicio)
    if quantidade_total <= 0:
        raise HTTPException(status_code=422, detail="Insumo sem quantidade para estornar.")

    try:
        movimento = EstoqueService.estornar_estoque(
            produto_id=insumo.produto_id,
            quantidade=float(quantidade_total),
            motivo="estorno_banho_tosa_insumo",
            referencia_id=atendimento_id,
            referencia_tipo="banho_tosa_atendimento",
            user_id=user.id,
            db=db,
            tenant_id=str(tenant_id),
            documento=f"BT-{atendimento_id}",
            observacao=f"Estorno da baixa do insumo #{insumo.id}",
            custo_unitario_override=float(insumo.custo_unitario_snapshot or 0),
        )
        insumo.movimentacao_estorno_id = movimento.get("movimentacao_id")
        insumo.estoque_estornado_em = datetime.now()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def serializar_insumo(insumo: BanhoTosaInsumoUsado) -> dict:
    produto = insumo.produto
    responsavel = insumo.responsavel
    quantidade_total = dec(insumo.quantidade_usada) + dec(insumo.quantidade_desperdicio)
    return {
        "id": insumo.id,
        "atendimento_id": insumo.atendimento_id,
        "produto_id": insumo.produto_id,
        "produto_nome": produto.nome if produto else None,
        "produto_codigo": produto.codigo if produto else None,
        "unidade": produto.unidade if produto else None,
        "quantidade_prevista": insumo.quantidade_prevista,
        "quantidade_usada": insumo.quantidade_usada,
        "quantidade_desperdicio": insumo.quantidade_desperdicio,
        "custo_unitario_snapshot": insumo.custo_unitario_snapshot,
        "custo_total": quantidade_total * dec(insumo.custo_unitario_snapshot),
        "movimentacao_estoque_id": insumo.movimentacao_estoque_id,
        "movimentacao_estorno_id": insumo.movimentacao_estorno_id,
        "estoque_estornado_em": insumo.estoque_estornado_em,
        "responsavel_id": insumo.responsavel_id,
        "responsavel_nome": responsavel.nome if responsavel else None,
    }
