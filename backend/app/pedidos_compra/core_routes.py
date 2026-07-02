"""Rotas principais de listagem e CRUD de pedidos de compra."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..models import Cliente
from ..produtos_models import PedidoCompra, PedidoCompraItem, Produto
from .exportacao import _montar_resposta_pedido_detalhada
from .quantidades import (
    calcular_quantidade_total_unidades,
    normalizar_quantidade_por_embalagem,
    normalizar_unidade_compra,
)
from .schemas import PedidoCompraRequest, PedidoCompraResponse
from .sugestao_queries import _resolver_fornecedores_compra

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# LISTAR PEDIDOS
# ============================================================================


@router.get("/", response_model=List[PedidoCompraResponse])
def listar_pedidos(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    fornecedor_id: Optional[int] = Query(None, description="Filtrar por fornecedor"),
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    busca: Optional[str] = Query(
        None, description="Buscar por numero, fornecedor ou observacao"
    ),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista pedidos de compra com filtros"""
    current_user, tenant_id = current_user_and_tenant
    logger.info("Listando pedidos de compra")

    query = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens))
        .filter(PedidoCompra.tenant_id == tenant_id)
    )

    # Filtros
    if status:
        query = query.filter(PedidoCompra.status == status)
    if fornecedor_id:
        query = query.filter(PedidoCompra.fornecedor_id == fornecedor_id)
    if data_inicio:
        try:
            data = datetime.strptime(data_inicio, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="data_inicio invalida. Use YYYY-MM-DD"
            ) from exc
        query = query.filter(PedidoCompra.data_pedido >= data)
    if data_fim:
        try:
            data = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="data_fim invalida. Use YYYY-MM-DD"
            ) from exc
        query = query.filter(PedidoCompra.data_pedido < data)
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        fornecedor_ids = db.query(Cliente.id).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
            or_(
                Cliente.nome.ilike(termo),
                Cliente.razao_social.ilike(termo),
                Cliente.nome_fantasia.ilike(termo),
                Cliente.cnpj.ilike(termo),
                Cliente.cpf.ilike(termo),
            ),
        )
        query = query.filter(
            or_(
                PedidoCompra.numero_pedido.ilike(termo),
                PedidoCompra.observacoes.ilike(termo),
                PedidoCompra.fornecedor_id.in_(fornecedor_ids),
            )
        )

    # Ordenar por data decrescente
    query = query.order_by(desc(PedidoCompra.data_pedido))

    # Paginação
    total = query.count()
    pedidos = query.offset(offset).limit(limit).all()

    # Formatar resposta
    resultado = []
    for pedido in pedidos:
        resultado.append(
            PedidoCompraResponse(
                id=pedido.id,
                numero_pedido=pedido.numero_pedido,
                fornecedor_id=pedido.fornecedor_id,
                status=pedido.status,
                valor_total=pedido.valor_total,
                valor_frete=pedido.valor_frete,
                valor_desconto=pedido.valor_desconto,
                valor_final=pedido.valor_final,
                data_pedido=pedido.data_pedido,
                data_prevista_entrega=pedido.data_prevista_entrega,
                observacoes=pedido.observacoes,
                itens_count=len(pedido.itens),
            )
        )

    logger.info(f"✅ {len(resultado)} pedidos encontrados (total: {total})")
    return resultado


@router.get("/rascunho/fornecedor/{fornecedor_id}")
def buscar_rascunho_fornecedor(
    fornecedor_id: int,
    incluir_grupo_fornecedor: bool = Query(default=False),
    fornecedor_grupo_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o rascunho mais recente de um fornecedor, se existir."""
    current_user, tenant_id = current_user_and_tenant
    logger.info("Buscando rascunho em aberto do fornecedor")

    fornecedor = (
        db.query(Cliente)
        .filter(
            Cliente.id == fornecedor_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor",
        )
        .first()
    )

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    fornecedor_ids, grupo = _resolver_fornecedores_compra(
        db,
        tenant_id,
        fornecedor,
        incluir_grupo_fornecedor=incluir_grupo_fornecedor,
        fornecedor_grupo_id=fornecedor_grupo_id,
    )

    rascunhos_query = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens).joinedload(PedidoCompraItem.produto))
        .filter(
            PedidoCompra.tenant_id == tenant_id,
            PedidoCompra.fornecedor_id.in_(fornecedor_ids),
            PedidoCompra.status == "rascunho",
        )
    )

    total_rascunhos = rascunhos_query.count()
    pedido = rascunhos_query.order_by(
        desc(PedidoCompra.updated_at), desc(PedidoCompra.id)
    ).first()

    if not pedido:
        return {
            "existe": False,
            "total_rascunhos": 0,
            "pedido": None,
            "fornecedor_ids_considerados": fornecedor_ids,
            "fornecedor_grupo": {
                "id": grupo.id,
                "nome": grupo.nome,
            }
            if grupo
            else None,
        }

    return {
        "existe": True,
        "total_rascunhos": total_rascunhos,
        "pedido": _montar_resposta_pedido_detalhada(pedido),
        "fornecedor_ids_considerados": fornecedor_ids,
        "fornecedor_grupo": {
            "id": grupo.id,
            "nome": grupo.nome,
        }
        if grupo
        else None,
    }


# ============================================================================
# BUSCAR PEDIDO POR ID
# ============================================================================


@router.get("/{pedido_id}")
def buscar_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Busca pedido completo com itens"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"🔍 Buscando pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens).joinedload(PedidoCompraItem.produto))
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    return _montar_resposta_pedido_detalhada(pedido)


# ============================================================================
# CRIAR PEDIDO
# ============================================================================


@router.post("/")
def criar_pedido(
    request: PedidoCompraRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria novo pedido de compra"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📝 Criando pedido de compra - Fornecedor: {request.fornecedor_id}")

    # Validar fornecedor
    fornecedor = (
        db.query(Cliente)
        .filter(Cliente.id == request.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    # Validar produtos
    if not request.itens or len(request.itens) == 0:
        raise HTTPException(status_code=400, detail="Pedido deve ter pelo menos 1 item")

    for item_req in request.itens:
        produto = (
            db.query(Produto)
            .filter(Produto.id == item_req.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if not produto:
            raise HTTPException(
                status_code=404, detail=f"Produto {item_req.produto_id} não encontrado"
            )

    # Gerar número do pedido
    ultimo_pedido = db.query(PedidoCompra).order_by(desc(PedidoCompra.id)).first()
    numero = 1 if not ultimo_pedido else ultimo_pedido.id + 1
    numero_pedido = f"PC{datetime.now().year}{numero:05d}"

    # Calcular totais
    valor_total = sum(
        (item.preco_unitario - item.desconto_item)
        * calcular_quantidade_total_unidades(
            item.quantidade_pedida,
            item.unidade_compra,
            item.quantidade_por_embalagem,
        )
        for item in request.itens
    )
    valor_final = valor_total + request.valor_frete - request.valor_desconto

    # Criar pedido
    pedido = PedidoCompra(
        numero_pedido=numero_pedido,
        fornecedor_id=request.fornecedor_id,
        status="rascunho",
        valor_total=valor_total,
        valor_frete=request.valor_frete,
        valor_desconto=request.valor_desconto,
        valor_final=valor_final,
        data_pedido=datetime.utcnow(),
        data_prevista_entrega=request.data_prevista_entrega,
        observacoes=request.observacoes,
        sugestao_ia=request.sugestao_ia,
        confianca_ia=request.confianca_ia,
        dados_ia=request.dados_ia,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    db.add(pedido)
    db.flush()  # Para obter o ID

    # Criar itens
    for item_req in request.itens:
        unidade_compra = normalizar_unidade_compra(item_req.unidade_compra)
        quantidade_por_embalagem = normalizar_quantidade_por_embalagem(
            unidade_compra, item_req.quantidade_por_embalagem
        )
        quantidade_total_unidades = calcular_quantidade_total_unidades(
            item_req.quantidade_pedida,
            unidade_compra,
            quantidade_por_embalagem,
        )
        valor_item = (
            item_req.preco_unitario - item_req.desconto_item
        ) * quantidade_total_unidades

        item = PedidoCompraItem(
            pedido_compra_id=pedido.id,
            produto_id=item_req.produto_id,
            quantidade_pedida=item_req.quantidade_pedida,
            quantidade_recebida=0,
            unidade_compra=unidade_compra,
            quantidade_por_embalagem=quantidade_por_embalagem,
            quantidade_total_unidades=quantidade_total_unidades,
            preco_unitario=item_req.preco_unitario,
            desconto_item=item_req.desconto_item,
            valor_total=valor_item,
            status="pendente",
            sugestao_ia=item_req.sugestao_ia,
            motivo_ia=item_req.motivo_ia,
            tenant_id=tenant_id,
        )
        db.add(item)

    db.commit()
    db.refresh(pedido)

    logger.info(f"✅ Pedido {pedido.numero_pedido} criado com sucesso")

    return {
        "message": "Pedido criado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "valor_final": pedido.valor_final,
        "itens_count": len(request.itens),
    }


# ============================================================================
# ATUALIZAR PEDIDO
# ============================================================================


@router.put("/{pedido_id}")
def atualizar_pedido(
    pedido_id: int,
    request: PedidoCompraRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza pedido (apenas se status = rascunho)"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"✏️ Atualizando pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status != "rascunho":
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser editado no status '{pedido.status}'",
        )

    # Recalcular totais
    valor_total = sum(
        (item.preco_unitario - item.desconto_item)
        * calcular_quantidade_total_unidades(
            item.quantidade_pedida,
            item.unidade_compra,
            item.quantidade_por_embalagem,
        )
        for item in request.itens
    )
    valor_final = valor_total + request.valor_frete - request.valor_desconto

    # Atualizar pedido
    pedido.fornecedor_id = request.fornecedor_id
    pedido.valor_total = valor_total
    pedido.valor_frete = request.valor_frete
    pedido.valor_desconto = request.valor_desconto
    pedido.valor_final = valor_final
    pedido.data_prevista_entrega = request.data_prevista_entrega
    pedido.observacoes = request.observacoes
    pedido.updated_at = datetime.utcnow()

    # Remover itens antigos
    db.query(PedidoCompraItem).filter(
        PedidoCompraItem.pedido_compra_id == pedido_id
    ).delete()

    # Adicionar novos itens
    for item_req in request.itens:
        unidade_compra = normalizar_unidade_compra(item_req.unidade_compra)
        quantidade_por_embalagem = normalizar_quantidade_por_embalagem(
            unidade_compra, item_req.quantidade_por_embalagem
        )
        quantidade_total_unidades = calcular_quantidade_total_unidades(
            item_req.quantidade_pedida,
            unidade_compra,
            quantidade_por_embalagem,
        )
        valor_item = (
            item_req.preco_unitario - item_req.desconto_item
        ) * quantidade_total_unidades

        item = PedidoCompraItem(
            pedido_compra_id=pedido.id,
            produto_id=item_req.produto_id,
            quantidade_pedida=item_req.quantidade_pedida,
            quantidade_recebida=0,
            unidade_compra=unidade_compra,
            quantidade_por_embalagem=quantidade_por_embalagem,
            quantidade_total_unidades=quantidade_total_unidades,
            preco_unitario=item_req.preco_unitario,
            desconto_item=item_req.desconto_item,
            valor_total=valor_item,
            status="pendente",
            sugestao_ia=item_req.sugestao_ia,
            motivo_ia=item_req.motivo_ia,
            tenant_id=tenant_id,
        )
        db.add(item)

    db.commit()

    logger.info(f"✅ Pedido {pedido.numero_pedido} atualizado")

    return {
        "message": "Pedido atualizado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
    }
