"""Rotas de estoque operacional do funcionario no app mobile."""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.bling_estoque_sync import sincronizar_bling_background
from app.db import get_session
from app.models import User
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.routes.app_mobile_funcionario_pdv_routes import (
    _barcode_filters_for_produto,
    _get_funcionario_operacional_or_403,
    _produto_busca_filtros_funcionario,
    _produto_busca_rank_funcionario,
)
from app.routes.ecommerce_auth import _get_current_ecommerce_user

router = APIRouter()
logger = logging.getLogger(__name__)


class FuncionarioProdutoEstoqueResponse(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    gtin_ean: Optional[str] = None
    unidade: str = "UN"
    preco_venda: float = 0
    preco_custo: float = 0
    estoque_atual: float = 0
    imagem_url: Optional[str] = None
    is_parent: bool = False
    tipo_produto: Optional[str] = None
    tipo_kit: Optional[str] = None
    permite_balanco: bool = True
    aviso: Optional[str] = None


class FuncionarioBalancoRequest(BaseModel):
    produto_id: int
    saldo_final: float = Field(ge=0)
    numero_lote: Optional[str] = None
    data_validade: Optional[str] = None
    observacao: Optional[str] = None


class FuncionarioBalancoResponse(BaseModel):
    status: str
    produto: FuncionarioProdutoEstoqueResponse
    estoque_anterior: float
    estoque_novo: float
    diferenca: float
    tipo_movimentacao: Optional[str] = None
    quantidade_movimentada: float = 0
    movimentacao_id: Optional[int] = None
    mensagem: str


def _produto_permite_balanco_funcionario(
    produto: Produto,
) -> tuple[bool, Optional[str]]:
    if getattr(produto, "is_parent", False):
        return False, "Produto pai: ajuste o estoque nas variacoes individuais."
    if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
        return False, "Kit virtual: ajuste os componentes que formam este kit."
    return True, None


def _serialize_funcionario_produto_estoque(produto: Produto) -> dict:
    permite_balanco, aviso = _produto_permite_balanco_funcionario(produto)
    return {
        "id": produto.id,
        "nome": produto.nome,
        "codigo": produto.codigo,
        "codigo_barras": produto.codigo_barras,
        "gtin_ean": produto.gtin_ean,
        "unidade": produto.unidade or "UN",
        "preco_venda": float(produto.preco_venda or 0),
        "preco_custo": float(produto.preco_custo or 0),
        "estoque_atual": float(produto.estoque_atual or 0),
        "imagem_url": produto.imagem_principal,
        "is_parent": bool(produto.is_parent),
        "tipo_produto": produto.tipo_produto,
        "tipo_kit": produto.tipo_kit,
        "permite_balanco": permite_balanco,
        "aviso": aviso,
    }


def _parse_data_validade_funcionario(valor: Optional[str]) -> Optional[datetime]:
    texto = str(valor or "").strip()
    if not texto:
        return None
    candidatos = [
        texto,
        texto.replace("Z", "+00:00"),
        texto.replace(" ", "T"),
        texto.split("T")[0],
    ]
    for candidato in candidatos:
        try:
            data = datetime.fromisoformat(candidato)
            return data.replace(tzinfo=None) if data.tzinfo else data
        except ValueError:
            continue
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail="Data de validade invalida.")


def _registrar_lote_balanco_funcionario(
    db: Session,
    produto: Produto,
    quantidade: float,
    numero_lote: Optional[str],
    data_validade: Optional[str],
) -> int | None:
    if quantidade <= 0 or not (numero_lote or data_validade):
        return None

    nome_lote = (
        numero_lote or f"{produto.codigo}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    ).strip()
    data_val = _parse_data_validade_funcionario(data_validade)
    produto.controle_lote = True

    lote = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto.id,
            ProdutoLote.nome_lote == nome_lote,
        )
        .first()
    )
    if lote:
        lote.quantidade_inicial = float(lote.quantidade_inicial or 0) + quantidade
        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        lote.data_validade = data_val or lote.data_validade
        lote.custo_unitario = lote.custo_unitario or produto.preco_custo
        lote.status = "ativo"
    else:
        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=nome_lote,
            quantidade_inicial=quantidade,
            quantidade_disponivel=quantidade,
            quantidade_reservada=0,
            data_validade=data_val,
            custo_unitario=produto.preco_custo,
            ordem_entrada=int(datetime.now().timestamp()),
            status="ativo",
        )
        db.add(lote)
        db.flush()
    return lote.id


def _consumir_lotes_balanco_funcionario(
    db: Session, produto: Produto, quantidade: float
) -> str | None:
    lotes_consumidos = []
    quantidade_restante = quantidade
    lotes_ativos = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto.id,
            ProdutoLote.quantidade_disponivel > 0,
            ProdutoLote.status == "ativo",
        )
        .order_by(ProdutoLote.ordem_entrada)
        .all()
    )
    for lote in lotes_ativos:
        if quantidade_restante <= 0:
            break
        saldo_anterior = float(lote.quantidade_disponivel or 0)
        quantidade_consumida = min(saldo_anterior, quantidade_restante)
        lote.quantidade_disponivel = saldo_anterior - quantidade_consumida
        quantidade_restante -= quantidade_consumida
        if lote.quantidade_disponivel <= 0:
            lote.status = "esgotado"
        lotes_consumidos.append(
            {
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "quantidade": quantidade_consumida,
                "saldo_anterior": saldo_anterior,
            }
        )
    return json.dumps(lotes_consumidos) if lotes_consumidos else None


@router.get(
    "/funcionario/estoque/produtos/buscar",
    response_model=list[FuncionarioProdutoEstoqueResponse],
)
def buscar_produtos_funcionario_estoque(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []

    filtros_busca = _produto_busca_filtros_funcionario(termo)
    rank_busca = _produto_busca_rank_funcionario(termo)
    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)
    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            or_(*filtros_busca),
        )
        .order_by(
            rank_busca.asc(),
            prioridade_estoque.asc(),
            Produto.is_parent.asc(),
            Produto.nome.asc(),
        )
        .limit(20)
        .all()
    )
    return [_serialize_funcionario_produto_estoque(produto) for produto in produtos]


@router.get(
    "/funcionario/estoque/produtos/barcode/{barcode}",
    response_model=FuncionarioProdutoEstoqueResponse,
)
def buscar_produto_funcionario_barcode(
    barcode: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    barcode = (barcode or "").strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Codigo de barras obrigatorio.")

    prioridade_estoque = case((func.coalesce(Produto.estoque_atual, 0) > 0, 0), else_=1)
    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            or_(*_barcode_filters_for_produto(barcode)),
        )
        .order_by(prioridade_estoque.asc(), Produto.is_parent.asc(), Produto.id.asc())
        .first()
    )
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto ERP nao encontrado para este codigo.",
        )
    return _serialize_funcionario_produto_estoque(produto)


@router.post("/funcionario/estoque/balanco", response_model=FuncionarioBalancoResponse)
def registrar_balanco_funcionario_estoque(
    payload: FuncionarioBalancoRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == payload.produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
        )
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")

    permite_balanco, aviso = _produto_permite_balanco_funcionario(produto)
    if not permite_balanco:
        raise HTTPException(status_code=400, detail=aviso)

    estoque_atual = float(produto.estoque_atual or 0)
    saldo_final = float(payload.saldo_final)
    diferenca = round(saldo_final - estoque_atual, 6)
    documento = f"APP-FUNC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    observacao_base = "App funcionario - balanco por camera"
    observacao = (
        observacao_base
        if not payload.observacao
        else f"{observacao_base}: {payload.observacao.strip()}"
    )

    if abs(diferenca) < 0.000001:
        return {
            "status": "sem_alteracao",
            "produto": _serialize_funcionario_produto_estoque(produto),
            "estoque_anterior": estoque_atual,
            "estoque_novo": saldo_final,
            "diferenca": 0,
            "tipo_movimentacao": None,
            "quantidade_movimentada": 0,
            "movimentacao_id": None,
            "mensagem": "Saldo final igual ao estoque atual. Nenhuma movimentacao registrada.",
        }

    tipo_movimentacao = "entrada" if diferenca > 0 else "saida"
    quantidade_movimentada = abs(diferenca)
    lote_id = None
    lotes_consumidos = None
    if tipo_movimentacao == "entrada":
        lote_id = _registrar_lote_balanco_funcionario(
            db,
            produto,
            quantidade_movimentada,
            payload.numero_lote,
            payload.data_validade,
        )
    else:
        lotes_consumidos = _consumir_lotes_balanco_funcionario(
            db, produto, quantidade_movimentada
        )

    produto.estoque_atual = saldo_final
    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo=tipo_movimentacao,
        motivo="balanco",
        quantidade=quantidade_movimentada,
        quantidade_anterior=estoque_atual,
        quantidade_nova=saldo_final,
        custo_unitario=produto.preco_custo,
        valor_total=quantidade_movimentada * float(produto.preco_custo or 0),
        lote_id=lote_id,
        lotes_consumidos=lotes_consumidos,
        documento=documento,
        observacao=observacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    db.refresh(produto)

    if tipo_movimentacao == "entrada" and estoque_atual <= 0 and saldo_final > 0:
        try:
            from app.services.pendencia_estoque_service import (
                verificar_e_notificar_pendencias,
            )

            verificar_e_notificar_pendencias(
                db=db,
                tenant_id=tenant_id,
                produto_id=produto.id,
                quantidade_entrada=quantidade_movimentada,
            )
        except Exception as exc:
            logger.warning(
                "[LISTA-ESPERA-PDV] Erro ao notificar clientes no balanco: %s",
                exc,
            )

    try:
        sincronizar_bling_background(produto.id, saldo_final, "balanco_app_funcionario")
    except Exception:
        pass

    return {
        "status": "registrado",
        "produto": _serialize_funcionario_produto_estoque(produto),
        "estoque_anterior": estoque_atual,
        "estoque_novo": saldo_final,
        "diferenca": diferenca,
        "tipo_movimentacao": tipo_movimentacao,
        "quantidade_movimentada": quantidade_movimentada,
        "movimentacao_id": movimentacao.id,
        "mensagem": f"Balanco registrado por {funcionario.nome or current_user.nome or current_user.email}.",
    }
