"""
ROTAS DE PEDIDOS DE COMPRA - Sistema Pet Shop Pro
Gestão completa de pedidos de compra com estrutura para IA futura

Funcionalidades:
- CRUD completo de pedidos
- Controle de status (rascunho → enviado → confirmado → recebido)
- Recebimento parcial ou total
- Entrada automática no estoque
- Exportação PDF/Excel (TODO)
- Integração WhatsApp/Email (TODO)

TODO - Integração com IA (Fase Futura):
1. Vinculação automática pedido ↔ NF-e XML/PDF
2. Conferência inteligente: pedido vs nota fiscal
   - Detectar divergências de preço, quantidade, produtos
   - Alertar sobre aumentos de preço significativos
3. Ações automáticas sugeridas pela IA:
   - Gerar novo pedido com itens faltantes
   - Criar mensagem questionando fornecedor sobre diferenças
   - Sugerir fornecedores alternativos em caso de problemas
4. Análise de histórico de compras para:
   - Prever necessidade de reposição
   - Identificar padrões de preço
   - Recomendar melhores fornecedores por produto
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
import io
from io import BytesIO

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User, Cliente
from .produtos_models import (
    Produto, ProdutoLote, EstoqueMovimentacao, 
    PedidoCompra, PedidoCompraItem
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pedidos-compra", tags=["Pedidos de Compra"])

# ============================================================================
# SCHEMAS
# ============================================================================

class PedidoCompraItemRequest(BaseModel):
    """Schema para item do pedido"""
    produto_id: int
    quantidade_pedida: float = Field(gt=0)
    preco_unitario: float = Field(ge=0)
    desconto_item: float = Field(default=0, ge=0)
    
    # IA (futuro)
    sugestao_ia: bool = False
    motivo_ia: Optional[str] = None


class PedidoCompraRequest(BaseModel):
    """Schema para criar/editar pedido"""
    fornecedor_id: int
    data_prevista_entrega: Optional[datetime] = None
    valor_frete: float = Field(default=0, ge=0)
    valor_desconto: float = Field(default=0, ge=0)
    observacoes: Optional[str] = None
    itens: List[PedidoCompraItemRequest]
    
    # IA (futuro)
    sugestao_ia: bool = False
    confianca_ia: Optional[float] = None
    dados_ia: Optional[str] = None


class RecebimentoItemRequest(BaseModel):
    """Schema para receber item"""
    item_id: int
    quantidade_recebida: float = Field(gt=0)


class RecebimentoPedidoRequest(BaseModel):
    """Schema para recebimento de pedido"""
    itens: List[RecebimentoItemRequest]
    data_recebimento: Optional[datetime] = None


class PedidoCompraResponse(BaseModel):
    """Schema de resposta do pedido"""
    id: int
    numero_pedido: str
    fornecedor_id: int
    status: str
    valor_total: float
    valor_frete: float
    valor_desconto: float
    valor_final: float
    data_pedido: datetime
    data_prevista_entrega: Optional[datetime]
    observacoes: Optional[str]
    itens_count: int
    
    model_config = {"from_attributes": True}


# ============================================================================
# LISTAR PEDIDOS
# ============================================================================

@router.get("/", response_model=List[PedidoCompraResponse])
def listar_pedidos(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    fornecedor_id: Optional[int] = Query(None, description="Filtrar por fornecedor"),
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista pedidos de compra com filtros"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📋 Listando pedidos de compra - Usuário: {current_user.nome}")
    
    query = db.query(PedidoCompra).options(joinedload(PedidoCompra.itens)).filter(
        PedidoCompra.tenant_id == tenant_id
    )
    
    # Filtros
    if status:
        query = query.filter(PedidoCompra.status == status)
    if fornecedor_id:
        query = query.filter(PedidoCompra.fornecedor_id == fornecedor_id)
    if data_inicio:
        data = datetime.strptime(data_inicio, "%Y-%m-%d")
        query = query.filter(PedidoCompra.data_pedido >= data)
    if data_fim:
        data = datetime.strptime(data_fim, "%Y-%m-%d")
        query = query.filter(PedidoCompra.data_pedido <= data)
    
    # Ordenar por data decrescente
    query = query.order_by(desc(PedidoCompra.data_pedido))
    
    # Paginação
    total = query.count()
    pedidos = query.offset(offset).limit(limit).all()
    
    # Formatar resposta
    resultado = []
    for pedido in pedidos:
        resultado.append(PedidoCompraResponse(
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
            itens_count=len(pedido.itens)
        ))
    
    logger.info(f"✅ {len(resultado)} pedidos encontrados (total: {total})")
    return resultado


# ============================================================================
# BUSCAR PEDIDO POR ID
# ============================================================================

@router.get("/{pedido_id}")
def buscar_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Busca pedido completo com itens"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"🔍 Buscando pedido {pedido_id}")
    
    pedido = db.query(PedidoCompra).options(
        joinedload(PedidoCompra.itens).joinedload(PedidoCompraItem.produto)
    ).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).first()
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    # Formatar resposta detalhada
    resposta = {
        "id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "fornecedor_id": pedido.fornecedor_id,
        "status": pedido.status,
        "valor_total": pedido.valor_total,
        "valor_frete": pedido.valor_frete,
        "valor_desconto": pedido.valor_desconto,
        "valor_final": pedido.valor_final,
        "data_pedido": pedido.data_pedido,
        "data_prevista_entrega": pedido.data_prevista_entrega,
        "data_recebimento": pedido.data_recebimento,
        "observacoes": pedido.observacoes,
        "sugestao_ia": pedido.sugestao_ia,
        "confianca_ia": pedido.confianca_ia,
        "itens": []
    }
    
    for item in pedido.itens:
        resposta["itens"].append({
            "id": item.id,
            "produto_id": item.produto_id,
            "produto_nome": item.produto.nome if item.produto else None,
            "produto_codigo": item.produto.codigo if item.produto else None,
            "quantidade_pedida": item.quantidade_pedida,
            "quantidade_recebida": item.quantidade_recebida,
            "preco_unitario": item.preco_unitario,
            "desconto_item": item.desconto_item,
            "valor_total": item.valor_total,
            "status": item.status,
            "sugestao_ia": item.sugestao_ia,
            "motivo_ia": item.motivo_ia
        })
    
    return resposta


# ============================================================================
# CRIAR PEDIDO
# ============================================================================

@router.post("/")
def criar_pedido(
    request: PedidoCompraRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria novo pedido de compra"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📝 Criando pedido de compra - Fornecedor: {request.fornecedor_id}")
    
    # Validar fornecedor
    fornecedor = db.query(Cliente).filter(
        Cliente.id == request.fornecedor_id,
        Cliente.tenant_id == tenant_id
    ).first()
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    
    # Validar produtos
    if not request.itens or len(request.itens) == 0:
        raise HTTPException(status_code=400, detail="Pedido deve ter pelo menos 1 item")
    
    for item_req in request.itens:
        produto = db.query(Produto).filter(
            Produto.id == item_req.produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        if not produto:
            raise HTTPException(
                status_code=404, 
                detail=f"Produto {item_req.produto_id} não encontrado"
            )
    
    # Gerar número do pedido
    ultimo_pedido = db.query(PedidoCompra).order_by(desc(PedidoCompra.id)).first()
    numero = 1 if not ultimo_pedido else ultimo_pedido.id + 1
    numero_pedido = f"PC{datetime.now().year}{numero:05d}"
    
    # Calcular totais
    valor_total = sum(
        (item.preco_unitario - item.desconto_item) * item.quantidade_pedida 
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
        user_id=current_user.id
    )
    
    db.add(pedido)
    db.flush()  # Para obter o ID
    
    # Criar itens
    for item_req in request.itens:
        valor_item = (item_req.preco_unitario - item_req.desconto_item) * item_req.quantidade_pedida
        
        item = PedidoCompraItem(
            pedido_compra_id=pedido.id,
            produto_id=item_req.produto_id,
            quantidade_pedida=item_req.quantidade_pedida,
            quantidade_recebida=0,
            preco_unitario=item_req.preco_unitario,
            desconto_item=item_req.desconto_item,
            valor_total=valor_item,
            status="pendente",
            sugestao_ia=item_req.sugestao_ia,
            motivo_ia=item_req.motivo_ia,
            tenant_id=tenant_id
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
        "itens_count": len(request.itens)
    }


# ============================================================================
# ATUALIZAR PEDIDO
# ============================================================================

@router.put("/{pedido_id}")
def atualizar_pedido(
    pedido_id: int,
    request: PedidoCompraRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza pedido (apenas se status = rascunho)"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"✏️ Atualizando pedido {pedido_id}")
    
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    if pedido.status != "rascunho":
        raise HTTPException(
            status_code=400, 
            detail=f"Pedido não pode ser editado no status '{pedido.status}'"
        )
    
    # Recalcular totais
    valor_total = sum(
        (item.preco_unitario - item.desconto_item) * item.quantidade_pedida 
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
        valor_item = (item_req.preco_unitario - item_req.desconto_item) * item_req.quantidade_pedida
        
        item = PedidoCompraItem(
            pedido_compra_id=pedido.id,
            produto_id=item_req.produto_id,
            quantidade_pedida=item_req.quantidade_pedida,
            quantidade_recebida=0,
            preco_unitario=item_req.preco_unitario,
            desconto_item=item_req.desconto_item,
            valor_total=valor_item,
            status="pendente",
            sugestao_ia=item_req.sugestao_ia,
            motivo_ia=item_req.motivo_ia,
            tenant_id=tenant_id
        )
        db.add(item)
    
    db.commit()
    
    logger.info(f"✅ Pedido {pedido.numero_pedido} atualizado")
    
    return {
        "message": "Pedido atualizado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido
    }


# ============================================================================
# ENVIAR PEDIDO
# ============================================================================

@router.post("/{pedido_id}/enviar")
def enviar_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Marca pedido como enviado"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📤 Enviando pedido {pedido_id}")
    
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    if pedido.status != "rascunho":
        raise HTTPException(
            status_code=400, 
            detail=f"Pedido não pode ser enviado no status '{pedido.status}'"
        )
    
    pedido.status = "enviado"
    pedido.data_envio = datetime.utcnow()
    pedido.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"✅ Pedido {pedido.numero_pedido} enviado")
    
    return {
        "message": "Pedido enviado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status
    }


# ============================================================================
# CONFIRMAR PEDIDO
# ============================================================================

@router.post("/{pedido_id}/confirmar")
def confirmar_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Confirma pedido (fornecedor confirmou recebimento)"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"✅ Confirmando pedido {pedido_id}")
    
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    if pedido.status not in ["rascunho", "enviado"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Pedido não pode ser confirmado no status '{pedido.status}'"
        )
    
    pedido.status = "confirmado"
    pedido.data_confirmacao = datetime.utcnow()
    pedido.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"✅ Pedido {pedido.numero_pedido} confirmado")
    
    return {
        "message": "Pedido confirmado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status
    }


# ============================================================================
# CANCELAR PEDIDO
# ============================================================================

@router.post("/{pedido_id}/cancelar")
def cancelar_pedido(
    pedido_id: int,
    motivo: str = Query(..., min_length=10, description="Motivo do cancelamento"),
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cancela pedido"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"❌ Cancelando pedido {pedido_id}")
    
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    if pedido.status in ["recebido_total", "cancelado"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Pedido não pode ser cancelado no status '{pedido.status}'"
        )
    
    pedido.status = "cancelado"
    pedido.observacoes = f"{pedido.observacoes or ''}\n\nCANCELADO: {motivo}"
    pedido.updated_at = datetime.utcnow()
    
    # Cancelar todos os itens
    for item in pedido.itens:
        item.status = "cancelado"
    
    db.commit()
    
    logger.info(f"❌ Pedido {pedido.numero_pedido} cancelado")
    
    return {
        "message": "Pedido cancelado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status
    }


# ============================================================================
# RECEBER PEDIDO (com entrada automática no estoque)
# ============================================================================

@router.post("/{pedido_id}/receber")
def receber_pedido(
    pedido_id: int,
    request: RecebimentoPedidoRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Recebe pedido (total ou parcial) e dá entrada automática no estoque
    """
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📦 Recebendo pedido {pedido_id}")
    
    pedido = db.query(PedidoCompra).options(
        joinedload(PedidoCompra.itens)
    ).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).first()
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    if pedido.status not in ["confirmado", "recebido_parcial"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Pedido não pode ser recebido no status '{pedido.status}'"
        )
    
    data_recebimento = request.data_recebimento or datetime.utcnow()
    itens_recebidos = []
    
    # Processar cada item
    for receb_item in request.itens:
        # Buscar item
        item = db.query(PedidoCompraItem).filter(
            PedidoCompraItem.id == receb_item.item_id,
            PedidoCompraItem.pedido_compra_id == pedido_id
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=404, 
                detail=f"Item {receb_item.item_id} não encontrado no pedido"
            )
        
        # Validar quantidade
        quantidade_pendente = item.quantidade_pedida - item.quantidade_recebida
        if receb_item.quantidade_recebida > quantidade_pendente:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item.id}: quantidade recebida ({receb_item.quantidade_recebida}) "
                       f"maior que pendente ({quantidade_pendente})"
            )
        
        # Atualizar quantidade recebida
        item.quantidade_recebida += receb_item.quantidade_recebida
        
        # Atualizar status do item
        if item.quantidade_recebida >= item.quantidade_pedida:
            item.status = "recebido_total"
        else:
            item.status = "recebido_parcial"
        
        # DAR ENTRADA NO ESTOQUE
        produto = db.query(Produto).filter(
            Produto.id == item.produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        
        # Criar lote
        numero_lote = f"PC{pedido.id}-{item.id}"
        
        lote = ProdutoLote(
            produto_id=produto.id,
            numero_lote=numero_lote,
            quantidade_inicial=receb_item.quantidade_recebida,
            quantidade_atual=receb_item.quantidade_recebida,
            custo_unitario=item.preco_unitario - item.desconto_item,
            data_fabricacao=None,
            data_validade=None,
            fornecedor=f"Pedido {pedido.numero_pedido}",
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        db.add(lote)
        db.flush()
        
        # Atualizar estoque do produto
        produto.estoque_atual = (produto.estoque_atual or 0) + receb_item.quantidade_recebida
        
        # Recalcular custo médio ponderado
        if produto.custo_medio:
            estoque_anterior = (produto.estoque_atual or 0) - receb_item.quantidade_recebida
            valor_anterior = estoque_anterior * produto.custo_medio
            valor_entrada = receb_item.quantidade_recebida * lote.custo_unitario
            produto.custo_medio = (valor_anterior + valor_entrada) / produto.estoque_atual
        else:
            produto.custo_medio = lote.custo_unitario
        
        # Registrar movimentação
        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            lote_id=lote.id,
            tipo_movimentacao="entrada",
            quantidade=receb_item.quantidade_recebida,
            custo_unitario=lote.custo_unitario,
            motivo=f"Recebimento do pedido {pedido.numero_pedido}",
            documento=pedido.numero_pedido,
            estoque_anterior=(produto.estoque_atual or 0) - receb_item.quantidade_recebida,
            estoque_atual=produto.estoque_atual,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        db.add(movimentacao)
        
        itens_recebidos.append({
            "item_id": item.id,
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "quantidade_recebida": receb_item.quantidade_recebida,
            "lote": numero_lote,
            "status": item.status
        })
        
        logger.info(
            f"  ✅ Item {item.id}: {produto.nome} - "
            f"{receb_item.quantidade_recebida} unidades recebidas"
        )
    
    # Atualizar status do pedido
    todos_recebidos = all(item.status == "recebido_total" for item in pedido.itens)
    algum_recebido = any(item.quantidade_recebida > 0 for item in pedido.itens)
    
    if todos_recebidos:
        pedido.status = "recebido_total"
        pedido.data_recebimento = data_recebimento
    elif algum_recebido:
        pedido.status = "recebido_parcial"
        if not pedido.data_recebimento:
            pedido.data_recebimento = data_recebimento
    
    pedido.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"✅ Pedido {pedido.numero_pedido} recebido - Status: {pedido.status}")
    
    return {
        "message": "Recebimento processado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status,
        "itens_recebidos": len(itens_recebidos),
        "detalhes": itens_recebidos
    }


# ============================================================================
# EXPORTAÇÃO PDF/EXCEL
# ============================================================================

@router.get("/{pedido_id}/export/excel")
def exportar_excel(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Exporta pedido para Excel"""
    current_user, tenant_id = current_user_and_tenant
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).options(joinedload(PedidoCompra.itens)).first()
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="Biblioteca openpyxl não instalada. Execute: pip install openpyxl"
        )
    
    # Criar workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pedido de Compra"
    
    # Cabeçalho
    ws['A1'] = "PEDIDO DE COMPRA"
    ws['A1'].font = Font(size=16, bold=True)
    ws.merge_cells('A1:F1')
    
    # Dados do pedido
    row = 3
    ws[f'A{row}'] = "Número do Pedido:"
    ws[f'B{row}'] = pedido.numero_pedido
    ws[f'B{row}'].font = Font(bold=True)
    
    row += 1
    fornecedor = db.query(Cliente).filter(
        Cliente.id == pedido.fornecedor_id,
        Cliente.tenant_id == tenant_id
    ).first()
    ws[f'A{row}'] = "Fornecedor:"
    ws[f'B{row}'] = fornecedor.nome if fornecedor else f"ID {pedido.fornecedor_id}"
    
    row += 1
    ws[f'A{row}'] = "Data do Pedido:"
    ws[f'B{row}'] = pedido.data_pedido.strftime("%d/%m/%Y")
    
    row += 1
    ws[f'A{row}'] = "Status:"
    ws[f'B{row}'] = pedido.status.replace('_', ' ').upper()
    
    # Itens
    row += 2
    headers = ['Código', 'Produto', 'Quantidade', 'Preço Unit.', 'Desconto', 'Total']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    
    row += 1
    for item in pedido.itens:
        produto = db.query(Produto).filter(
            Produto.id == item.produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        ws.cell(row=row, column=1).value = produto.codigo if produto else ''
        ws.cell(row=row, column=2).value = produto.nome if produto else f"Produto {item.produto_id}"
        ws.cell(row=row, column=3).value = item.quantidade_pedida
        ws.cell(row=row, column=4).value = item.preco_unitario
        ws.cell(row=row, column=5).value = item.desconto_item
        ws.cell(row=row, column=6).value = item.valor_total
        row += 1
    
    # Totais
    row += 1
    ws[f'E{row}'] = "Frete:"
    ws[f'F{row}'] = pedido.valor_frete
    row += 1
    ws[f'E{row}'] = "Desconto:"
    ws[f'F{row}'] = pedido.valor_desconto
    row += 1
    ws[f'E{row}'] = "TOTAL:"
    ws[f'E{row}'].font = Font(bold=True, size=12)
    ws[f'F{row}'] = pedido.valor_final
    ws[f'F{row}'].font = Font(bold=True, size=12)
    
    # Ajustar larguras
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    
    # Salvar em bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"pedido_{pedido.numero_pedido}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{pedido_id}/export/pdf")
def exportar_pdf(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Exporta pedido para PDF"""
    current_user, tenant_id = current_user_and_tenant
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).options(joinedload(PedidoCompra.itens)).first()
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab não instalada. Execute: pip install reportlab"
        )
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a56db'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("PEDIDO DE COMPRA", title_style))
    elements.append(Spacer(1, 10*mm))
    
    # Info do pedido
    fornecedor = db.query(Cliente).filter(
        Cliente.id == pedido.fornecedor_id,
        Cliente.tenant_id == tenant_id
    ).first()
    fornecedor_nome = fornecedor.nome if fornecedor else f"ID {pedido.fornecedor_id}"
    
    info_data = [
        ['Número do Pedido:', pedido.numero_pedido],
        ['Fornecedor:', fornecedor_nome],
        ['Data do Pedido:', pedido.data_pedido.strftime("%d/%m/%Y %H:%M")],
        ['Status:', pedido.status.replace('_', ' ').upper()],
    ]
    
    info_table = Table(info_data, colWidths=[40*mm, 120*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Tabela de itens
    table_data = [['Código', 'Produto', 'Qtd', 'Preço Unit.', 'Desc.', 'Total']]
    
    # Estilo para nome do produto (permite quebra de linha)
    produto_style = ParagraphStyle(
        'ProdutoStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
    )
    
    for item in pedido.itens:
        produto = db.query(Produto).filter(
            Produto.id == item.produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        nome_produto = produto.nome if produto else f"Produto {item.produto_id}"
        
        # Usar Paragraph para quebrar linha automaticamente
        nome_produto_paragraph = Paragraph(nome_produto, produto_style)
        
        table_data.append([
            produto.codigo if produto else '',
            nome_produto_paragraph,
            f"{item.quantidade_pedida:.0f}",
            f"R$ {item.preco_unitario:.2f}",
            f"R$ {item.desconto_item:.2f}",
            f"R$ {item.valor_total:.2f}"
        ])
    
    items_table = Table(table_data, colWidths=[20*mm, 70*mm, 15*mm, 23*mm, 18*mm, 23*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 5*mm))
    
    # Totais
    totals_data = [
        ['', '', '', '', 'Frete:', f"R$ {pedido.valor_frete:.2f}"],
        ['', '', '', '', 'Desconto:', f"R$ {pedido.valor_desconto:.2f}"],
        ['', '', '', '', 'TOTAL:', f"R$ {pedido.valor_final:.2f}"],
    ]
    
    totals_table = Table(totals_data, colWidths=[20*mm, 70*mm, 20*mm, 25*mm, 20*mm, 25*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (4, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (4, -1), (-1, -1), 12),
        ('LINEABOVE', (4, -1), (-1, -1), 2, colors.black),
    ]))
    elements.append(totals_table)
    
    # Observações
    if pedido.observacoes:
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph("<b>Observações:</b>", styles['Normal']))
        elements.append(Paragraph(pedido.observacoes, styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"pedido_{pedido.numero_pedido}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/{pedido_id}/reverter")
def reverter_status(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Reverte status do pedido (para corrigir cliques acidentais)"""
    current_user, tenant_id = current_user_and_tenant
    pedido = db.query(PedidoCompra).filter(
        PedidoCompra.id == pedido_id,
        PedidoCompra.tenant_id == tenant_id
    ).first()
    
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    # Lógica de reversão
    status_reverso = {
        'enviado': 'rascunho',
        'confirmado': 'enviado',
        'recebido_parcial': 'confirmado',
        'recebido_total': 'confirmado'
    }
    
    if pedido.status not in status_reverso:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível reverter pedido com status '{pedido.status}'"
        )
    
    status_anterior = pedido.status
    pedido.status = status_reverso[pedido.status]
    pedido.updated_at = datetime.now()
    
    db.commit()
    logger.info(f"⏪ Pedido {pedido.numero_pedido} revertido: {status_anterior} → {pedido.status}")
    
    return {
        "message": "Status revertido com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status_anterior": status_anterior,
        "status_atual": pedido.status
    }
