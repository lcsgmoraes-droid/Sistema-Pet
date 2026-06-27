"""Rotas de lotes e movimentacoes FIFO de produtos."""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.estoque_regras import mensagem_servico_sem_estoque, produto_eh_servico
from app.produtos.lotes import _consumir_lotes_fifo_produto
from app.produtos.schemas import (
    EntradaEstoqueRequest,
    LoteBase,
    LoteCreate,
    LoteResponse,
    SaidaEstoqueRequest,
)
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote

logger = logging.getLogger(__name__)

router = APIRouter()


def _bloquear_estoque_para_servico(produto: Produto) -> None:
    if produto_eh_servico(produto):
        raise HTTPException(
            status_code=400,
            detail=mensagem_servico_sem_estoque(produto),
        )


# ==========================================
# ENDPOINTS - LOTES E FIFO
# ==========================================


@router.post(
    "/{produto_id}/lotes",
    response_model=LoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_lote(
    produto_id: int,
    lote: LoteCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo lote para o produto"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    _bloquear_estoque_para_servico(produto)

    # Verificar se nÃºmero de lote jÃ¡ existe para este produto
    lote_existente = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.nome_lote == lote.nome_lote,
        )
        .first()
    )

    if lote_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Lote '{lote.nome_lote}' jÃ¡ cadastrado para este produto",
        )

    # Criar lote com timestamp para FIFO

    novo_lote = ProdutoLote(
        **lote.model_dump(),
        produto_id=produto_id,
        quantidade_disponivel=lote.quantidade,
        ordem_entrada=int(time.time()),  # Unix timestamp para FIFO
    )

    db.add(novo_lote)

    # Atualizar estoque do produto
    produto.estoque_atual += lote.quantidade
    produto.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(novo_lote)

    # Sincronizar estoque com Bling em background
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "criacao_lote"
        )
    except Exception:
        pass

    return novo_lote


@router.get("/{produto_id}/lotes", response_model=List[LoteResponse])
def listar_lotes(
    produto_id: int,
    apenas_disponiveis: bool = False,  # Mostrar todos por padrÃ£o
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista lotes de um produto"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    logger.info(
        f"ðŸ“¦ Listando lotes do produto {produto_id} - apenas_disponiveis={apenas_disponiveis}"
    )

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    query = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto_id,
        ProdutoLote.status != "excluido",  # Apenas lotes nÃ£o excluÃ­dos
    )

    if apenas_disponiveis:
        query = query.filter(ProdutoLote.quantidade_disponivel > 0)

    # Ordenar por FIFO (mais antigo primeiro)
    lotes = query.order_by(ProdutoLote.ordem_entrada).all()

    logger.info(f"âœ… Encontrados {len(lotes)} lotes")

    return lotes


@router.put("/{produto_id}/lotes/{lote_id}", response_model=LoteResponse)
def atualizar_lote(
    produto_id: int,
    lote_id: int,
    lote_data: LoteBase,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza informaÃ§Ãµes de um lote"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar lote
    lote = (
        db.query(ProdutoLote)
        .filter(ProdutoLote.id == lote_id, ProdutoLote.produto_id == produto_id)
        .first()
    )

    if not lote:
        raise HTTPException(status_code=404, detail="Lote nÃ£o encontrado")

    # Verificar se o produto pertence ao usuÃ¡rio
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    _bloquear_estoque_para_servico(produto)

    # Calcular diferenÃ§a de quantidade para ajustar estoque
    diferenca_quantidade = lote_data.quantidade_inicial - lote.quantidade_inicial

    # Atualizar campos
    lote.nome_lote = lote_data.nome_lote
    lote.quantidade_inicial = lote_data.quantidade_inicial
    lote.quantidade_disponivel = lote.quantidade_disponivel + diferenca_quantidade
    lote.data_fabricacao = lote_data.data_fabricacao
    lote.data_validade = lote_data.data_validade
    lote.custo_unitario = lote_data.custo_unitario

    # Atualizar estoque do produto
    produto.estoque_atual = produto.estoque_atual + diferenca_quantidade

    db.commit()
    db.refresh(lote)

    # Sincronizar estoque com Bling em background
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "edicao_lote"
        )
    except Exception:
        pass

    return lote


@router.delete("/{produto_id}/lotes/{lote_id}")
def excluir_lote(
    produto_id: int,
    lote_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exclui um lote (soft delete)"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar lote
    lote = (
        db.query(ProdutoLote)
        .filter(ProdutoLote.id == lote_id, ProdutoLote.produto_id == produto_id)
        .first()
    )

    if not lote:
        raise HTTPException(status_code=404, detail="Lote nÃ£o encontrado")

    # Verificar se o produto pertence ao usuÃ¡rio
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    _bloquear_estoque_para_servico(produto)

    # Atualizar estoque do produto (remover a quantidade do lote)
    produto.estoque_atual = produto.estoque_atual - lote.quantidade_disponivel

    # Soft delete - marcar como excluÃ­do
    lote.status = "excluido"
    lote.updated_at = datetime.utcnow()

    db.commit()

    # Sincronizar estoque com Bling em background
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "exclusao_lote"
        )
    except Exception:
        pass

    return {"message": "Lote excluÃ­do com sucesso"}


@router.post("/{produto_id}/entrada")
def entrada_estoque(
    produto_id: int,
    entrada: EntradaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registra entrada de estoque criando um lote"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    _bloquear_estoque_para_servico(produto)

    # VALIDAÃ‡ÃƒO: Produto PAI nÃ£o pode ter movimentaÃ§Ã£o de estoque
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail="Produto pai nÃ£o pode ter entrada de estoque. Realize a entrada nas variaÃ§Ãµes do produto.",
        )

    # Verificar se lote jÃ¡ existe
    lote_existente = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.nome_lote == entrada.nome_lote,
        )
        .first()
    )

    if lote_existente:
        # Se lote existe, adicionar quantidade
        lote_existente.quantidade_inicial += entrada.quantidade
        lote_existente.quantidade_disponivel += entrada.quantidade
        lote = lote_existente
    else:
        # Criar novo lote

        lote = ProdutoLote(
            produto_id=produto_id,
            nome_lote=entrada.nome_lote,
            quantidade_inicial=entrada.quantidade,
            quantidade_disponivel=entrada.quantidade,
            data_fabricacao=entrada.data_fabricacao,
            data_validade=entrada.data_validade
            or datetime.utcnow() + timedelta(days=365),  # Validade padrÃ£o 1 ano
            custo_unitario=entrada.preco_custo,
            ordem_entrada=int(time.time()),
        )
        db.add(lote)

    # Atualizar estoque do produto
    estoque_anterior = produto.estoque_atual
    produto.estoque_atual += entrada.quantidade
    produto.updated_at = datetime.utcnow()

    # Registrar movimentaÃ§Ã£o
    movimentacao = EstoqueMovimentacao(
        produto_id=produto_id,
        tipo="entrada",
        motivo="compra",
        quantidade=entrada.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=entrada.preco_custo,
        lote_id=lote.id,
        observacao=entrada.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)

    db.commit()
    db.refresh(lote)

    # Sincronizar estoque com Bling em background (fire-and-forget)
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "entrada_estoque"
        )
    except Exception:
        pass

    return {
        "sucesso": True,
        "mensagem": "Entrada registrada com sucesso",
        "lote_id": lote.id,
        "nome_lote": lote.nome_lote,
        "quantidade_entrada": entrada.quantidade,
        "estoque_atual": produto.estoque_atual,
    }


@router.post("/{produto_id}/saida-fifo")
def saida_estoque_fifo(
    produto_id: int,
    saida: SaidaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Registra saÃ­da de estoque usando FIFO
    Consome lotes mais antigos primeiro
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    _bloquear_estoque_para_servico(produto)

    # VALIDAÃ‡ÃƒO: Produto PAI nÃ£o pode ter movimentaÃ§Ã£o de estoque
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail="Produto pai nÃ£o pode ter saÃ­da de estoque. Realize a saÃ­da nas variaÃ§Ãµes do produto.",
        )

    # Verificar se hÃ¡ estoque suficiente
    if produto.estoque_atual < saida.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. DisponÃ­vel: {produto.estoque_atual}, Solicitado: {saida.quantidade}",
        )

    # Buscar lotes disponÃ­veis ordenados por FIFO (mais antigo primeiro)
    lotes = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto_id, ProdutoLote.quantidade_disponivel > 0
        )
        .order_by(ProdutoLote.ordem_entrada)
        .all()
    )

    if not lotes:
        raise HTTPException(status_code=400, detail="Nenhum lote disponÃ­vel")

    # Consumir lotes usando FIFO
    lotes_consumidos = _consumir_lotes_fifo_produto(lotes, saida.quantidade)

    # Atualizar estoque do produto
    estoque_anterior = produto.estoque_atual
    produto.estoque_atual -= saida.quantidade
    produto.updated_at = datetime.utcnow()

    # Registrar movimentaÃ§Ã£o

    movimentacao = EstoqueMovimentacao(
        produto_id=produto_id,
        tipo_movimentacao=saida.motivo,
        quantidade=saida.quantidade,
        estoque_anterior=estoque_anterior,
        estoque_resultante=produto.estoque_atual,
        numero_pedido=saida.numero_pedido,
        observacoes=saida.observacoes,
        usuario=current_user.nome,
        lotes_consumidos=json.dumps(lotes_consumidos),
    )
    db.add(movimentacao)

    db.commit()

    # Sincronizar estoque com Bling em background (fire-and-forget)
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "saida_fifo"
        )
    except Exception:
        pass

    return {
        "sucesso": True,
        "mensagem": "SaÃ­da registrada com sucesso usando FIFO",
        "quantidade_saida": saida.quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_atual": produto.estoque_atual,
        "lotes_consumidos": lotes_consumidos,
        "numero_pedido": saida.numero_pedido,
    }
