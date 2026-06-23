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

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from io import BytesIO

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .models import Cliente
from .produtos_models import (
    Produto,
    ProdutoLote,
    EstoqueMovimentacao,
    PedidoCompra,
    PedidoCompraItem,
    ProdutoFornecedor,
    Marca,
)
from .services.email_service import is_email_configured, send_email
from .pedidos_compra.confronto_routes import (
    _realizar_confronto as _realizar_confronto,
    router as confronto_router,
)
from .pedidos_compra.exportacao import (
    PEDIDO_EXPORT_COLUNAS_DEFAULT,
    _buscar_fornecedor_pedido,
    _gerar_excel_pedido_bytes,
    _gerar_pdf_pedido_bytes,
    _montar_content_disposition_attachment,
    _montar_email_pedido,
    _montar_nome_arquivo_pedido,
    _montar_resposta_pedido_detalhada,
    _normalizar_colunas_exportacao_pedido,
)
from .pedidos_compra.sugestao import (
    JANELAS_GIRO_SUGESTAO,
    _calcular_dias_com_estoque,
    _calcular_planejamento_compra_sugestao,
    _calcular_tendencia_vendas_sugestao,
    _float_seguro_sugestao,
    _montar_item_sugestao_compra,
    _montar_resposta_sugestao_compra,
    _selecionar_produtos_fornecedor_sugestao,
)
from .pedidos_compra.sugestao_queries import (
    _agrupar_movimentacoes_estoque_periodo,
    _carregar_vendas_sugestao,
    _obter_estoque_atual_sugestao,
    _resolver_fornecedores_compra,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pedidos-compra", tags=["Pedidos de Compra"])
router.include_router(confronto_router)

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


class PedidoCompraEnvioFormatos(BaseModel):
    pdf: bool = True
    excel: bool = False


class PedidoCompraEnviarRequest(BaseModel):
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    formatos: PedidoCompraEnvioFormatos = Field(
        default_factory=PedidoCompraEnvioFormatos
    )
    colunas_exportacao: List[str] = Field(
        default_factory=lambda: PEDIDO_EXPORT_COLUNAS_DEFAULT.copy()
    )
    envio_manual: bool = False


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


# ============================================================================
# STATUS DE ENVIO
# ============================================================================


@router.get("/envio/status")
def status_envio_pedidos(current_user_and_tenant=Depends(get_current_user_and_tenant)):
    """Informa se o servidor está apto a enviar pedidos por e-mail."""
    current_user, tenant_id = current_user_and_tenant
    return {"email_configurado": is_email_configured()}


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
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    db.add(pedido)
    db.flush()  # Para obter o ID

    # Criar itens
    for item_req in request.itens:
        valor_item = (
            item_req.preco_unitario - item_req.desconto_item
        ) * item_req.quantidade_pedida

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
        valor_item = (
            item_req.preco_unitario - item_req.desconto_item
        ) * item_req.quantidade_pedida

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


# ============================================================================
# ENVIAR PEDIDO
# ============================================================================


@router.post("/{pedido_id}/enviar")
def enviar_pedido(
    pedido_id: int,
    request: PedidoCompraEnviarRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Marca pedido como enviado"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📤 Enviando pedido {pedido_id}")

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
            detail=f"Pedido não pode ser enviado no status '{pedido.status}'",
        )

    fornecedor = _buscar_fornecedor_pedido(db, tenant_id, pedido)
    fornecedor_nome = (
        fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"
    )

    if request.envio_manual:
        pedido.status = "enviado"
        pedido.data_envio = datetime.utcnow()
        pedido.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Pedido {pedido.numero_pedido} marcado como enviado manualmente")
        return {
            "message": "Pedido marcado como enviado manualmente",
            "pedido_id": pedido.id,
            "numero_pedido": pedido.numero_pedido,
            "status": pedido.status,
            "tipo_envio": "manual",
        }

    email_destino = (request.email or "").strip()
    if not email_destino:
        raise HTTPException(status_code=400, detail="Informe o e-mail do fornecedor")

    formatos = request.formatos or PedidoCompraEnvioFormatos()
    if not formatos.pdf and not formatos.excel:
        raise HTTPException(
            status_code=400, detail="Selecione pelo menos um formato para envio"
        )

    colunas_exportacao = _normalizar_colunas_exportacao_pedido(
        request.colunas_exportacao
    )

    if not is_email_configured():
        raise HTTPException(
            status_code=503, detail="O envio de e-mail nao esta configurado no servidor"
        )

    anexos = []
    if formatos.pdf:
        nome_pdf = _montar_nome_arquivo_pedido(
            pedido, fornecedor_nome, db, tenant_id, "pdf"
        )
        anexos.append(
            {
                "filename": nome_pdf,
                "content": _gerar_pdf_pedido_bytes(
                    pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
                ),
                "mime_subtype": "pdf",
            }
        )
    if formatos.excel:
        nome_excel = _montar_nome_arquivo_pedido(
            pedido, fornecedor_nome, db, tenant_id, "xlsx"
        )
        anexos.append(
            {
                "filename": nome_excel,
                "content": _gerar_excel_pedido_bytes(
                    pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
                ),
                "mime_subtype": "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

    assunto, html_body, text_body = _montar_email_pedido(
        pedido, fornecedor_nome, colunas_exportacao
    )
    enviado = send_email(
        to=email_destino,
        subject=assunto,
        html_body=html_body,
        text_body=text_body,
        attachments=anexos,
        simulate_if_unconfigured=False,
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel enviar o e-mail do pedido. Revise a configuracao SMTP.",
        )

    pedido.status = "enviado"
    pedido.data_envio = datetime.utcnow()
    pedido.updated_at = datetime.utcnow()

    db.commit()
    logger.info(
        f"Pedido {pedido.numero_pedido} enviado por e-mail para {email_destino}"
    )
    return {
        "message": "Pedido enviado por e-mail com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status,
        "tipo_envio": "email",
        "email": email_destino,
    }


# ============================================================================
# CONFIRMAR PEDIDO
# ============================================================================


@router.post("/{pedido_id}/confirmar")
def confirmar_pedido(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Confirma pedido (fornecedor confirmou recebimento)"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"✅ Confirmando pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ["rascunho", "enviado"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser confirmado no status '{pedido.status}'",
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
        "status": pedido.status,
    }


# ============================================================================
# CANCELAR PEDIDO
# ============================================================================


@router.post("/{pedido_id}/cancelar")
def cancelar_pedido(
    pedido_id: int,
    motivo: str = Query(..., min_length=10, description="Motivo do cancelamento"),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cancela pedido"""
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"❌ Cancelando pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status in ["recebido_total", "cancelado"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser cancelado no status '{pedido.status}'",
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
        "status": pedido.status,
    }


# ============================================================================
# RECEBER PEDIDO (com entrada automática no estoque)
# ============================================================================


@router.post("/{pedido_id}/receber")
def receber_pedido(
    pedido_id: int,
    request: RecebimentoPedidoRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Recebe pedido (total ou parcial) e dá entrada automática no estoque
    """
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📦 Recebendo pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens))
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ["confirmado", "recebido_parcial"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser recebido no status '{pedido.status}'",
        )

    data_recebimento = request.data_recebimento or datetime.utcnow()
    itens_recebidos = []
    para_sync_bling = []  # (produto_id, estoque_atual)

    # Processar cada item
    for receb_item in request.itens:
        # Buscar item
        item = (
            db.query(PedidoCompraItem)
            .filter(
                PedidoCompraItem.id == receb_item.item_id,
                PedidoCompraItem.pedido_compra_id == pedido_id,
            )
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Item {receb_item.item_id} não encontrado no pedido",
            )

        # Validar quantidade
        quantidade_pendente = item.quantidade_pedida - item.quantidade_recebida
        if receb_item.quantidade_recebida > quantidade_pendente:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item.id}: quantidade recebida ({receb_item.quantidade_recebida}) "
                f"maior que pendente ({quantidade_pendente})",
            )

        # Atualizar quantidade recebida
        item.quantidade_recebida += receb_item.quantidade_recebida

        # Atualizar status do item
        if item.quantidade_recebida >= item.quantidade_pedida:
            item.status = "recebido_total"
        else:
            item.status = "recebido_parcial"

        # DAR ENTRADA NO ESTOQUE
        produto = (
            db.query(Produto)
            .filter(Produto.id == item.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto {item.produto_id} nao encontrado para o item {item.id}",
            )

        # Criar lote
        numero_lote = f"PC{pedido.id}-{item.id}"
        custo_unitario_lote = float(item.preco_unitario or 0) - float(
            item.desconto_item or 0
        )

        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=numero_lote,
            quantidade_inicial=receb_item.quantidade_recebida,
            quantidade_disponivel=receb_item.quantidade_recebida,
            quantidade_reservada=0,
            custo_unitario=custo_unitario_lote,
            data_fabricacao=None,
            data_validade=None,
            ordem_entrada=int(datetime.utcnow().timestamp()),
            status="ativo",
            tenant_id=tenant_id,
        )
        db.add(lote)
        db.flush()

        # Atualizar estoque do produto
        produto.estoque_atual = (
            produto.estoque_atual or 0
        ) + receb_item.quantidade_recebida

        # Recalcular custo médio ponderado
        if produto.custo_medio:
            estoque_anterior = (
                produto.estoque_atual or 0
            ) - receb_item.quantidade_recebida
            valor_anterior = estoque_anterior * produto.custo_medio
            valor_entrada = receb_item.quantidade_recebida * lote.custo_unitario
            produto.custo_medio = (
                valor_anterior + valor_entrada
            ) / produto.estoque_atual
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
            estoque_anterior=(produto.estoque_atual or 0)
            - receb_item.quantidade_recebida,
            estoque_atual=produto.estoque_atual,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(movimentacao)

        itens_recebidos.append(
            {
                "item_id": item.id,
                "produto_id": produto.id,
                "produto_nome": produto.nome,
                "quantidade_recebida": receb_item.quantidade_recebida,
                "lote": numero_lote,
                "status": item.status,
            }
        )
        para_sync_bling.append((produto.id, produto.estoque_atual))

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

    # SINCRONIZAR ESTOQUE COM BLING para todos os itens recebidos
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        for produto_id, estoque_novo in para_sync_bling:
            sincronizar_bling_background(
                produto_id, estoque_novo, "recebimento_pedido_compra"
            )
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (pedido_compra): {e_sync}")

    logger.info(f"✅ Pedido {pedido.numero_pedido} recebido - Status: {pedido.status}")

    return {
        "message": "Recebimento processado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status,
        "itens_recebidos": len(itens_recebidos),
        "detalhes": itens_recebidos,
    }


# ============================================================================
# EXPORTAÇÃO PDF/EXCEL
# ============================================================================


@router.get("/{pedido_id}/export/excel")
def exportar_excel(
    pedido_id: int,
    colunas: Optional[str] = Query(
        None, description="Colunas do documento separadas por virgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta pedido para Excel"""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .options(joinedload(PedidoCompra.itens))
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    fornecedor = _buscar_fornecedor_pedido(db, tenant_id, pedido)
    fornecedor_nome = (
        fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"
    )
    colunas_exportacao = _normalizar_colunas_exportacao_pedido(colunas)
    output = BytesIO(
        _gerar_excel_pedido_bytes(
            pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
        )
    )
    filename = _montar_nome_arquivo_pedido(
        pedido, fornecedor_nome, db, tenant_id, "xlsx"
    )

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": _montar_content_disposition_attachment(filename)
        },
    )


@router.get("/{pedido_id}/export/pdf")
def exportar_pdf(
    pedido_id: int,
    colunas: Optional[str] = Query(
        None, description="Colunas do documento separadas por virgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta pedido para PDF"""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .options(joinedload(PedidoCompra.itens))
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    fornecedor = _buscar_fornecedor_pedido(db, tenant_id, pedido)
    fornecedor_nome = (
        fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"
    )
    colunas_exportacao = _normalizar_colunas_exportacao_pedido(colunas)
    buffer = BytesIO(
        _gerar_pdf_pedido_bytes(
            pedido, fornecedor_nome, db, tenant_id, colunas_exportacao
        )
    )
    filename = _montar_nome_arquivo_pedido(
        pedido, fornecedor_nome, db, tenant_id, "pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _montar_content_disposition_attachment(filename)
        },
    )


@router.post("/{pedido_id}/reverter")
def reverter_status(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Reverte status do pedido (para corrigir cliques acidentais)"""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Lógica de reversão
    status_reverso = {
        "enviado": "rascunho",
        "confirmado": "enviado",
        "recebido_parcial": "confirmado",
        "recebido_total": "confirmado",
    }

    if pedido.status not in status_reverso:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível reverter pedido com status '{pedido.status}'",
        )

    status_anterior = pedido.status
    pedido.status = status_reverso[pedido.status]
    pedido.updated_at = datetime.now()

    db.commit()
    logger.info(
        f"⏪ Pedido {pedido.numero_pedido} revertido: {status_anterior} → {pedido.status}"
    )

    return {
        "message": "Status revertido com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status_anterior": status_anterior,
        "status_atual": pedido.status,
    }


# ============================================================================
# 💡 SUGESTÃO INTELIGENTE DE PEDIDO
# ============================================================================


@router.get("/sugestao/{fornecedor_id}")
def sugerir_pedido_inteligente(
    fornecedor_id: int,
    periodo_dias: int = Query(
        default=90, ge=7, le=365, description="Período de análise (7-365 dias)"
    ),
    dias_cobertura: int = Query(
        default=30,
        ge=7,
        le=180,
        description="Dias de estoque que o pedido deve cobrir (7-180)",
    ),
    apenas_criticos: bool = Query(
        default=False, description="Apenas produtos críticos (estoque < 7 dias)"
    ),
    incluir_alerta: bool = Query(
        default=True, description="Incluir produtos em alerta"
    ),
    incluir_grupo_fornecedor: bool = Query(
        default=False,
        description="Incluir todos os CNPJs do grupo comercial do fornecedor",
    ),
    apenas_fornecedor_principal: bool = Query(
        default=False,
        description="Considerar apenas produtos cujo fornecedor principal esta no fornecedor/grupo selecionado",
    ),
    fornecedor_grupo_id: Optional[int] = Query(
        default=None,
        description="Grupo comercial de fornecedores para consolidar a sugestao",
    ),
    marca_ids: Optional[List[int]] = Query(
        default=None, description="Filtrar por marcas específicas"
    ),
    marca_ids_brackets: Optional[List[int]] = Query(default=None, alias="marca_ids[]"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    📊 Sugestão Inteligente de Pedido de Compra

    Analisa histórico de vendas, estoque atual e lead time do fornecedor
    para sugerir quantidade ideal a pedir de cada produto.

    Algoritmo:
    1. Calcula consumo médio diário baseado em vendas do período
    2. Verifica estoque atual e dias de cobertura restantes
    3. Considera lead time do fornecedor (prazo de entrega)
    4. Sugere quantidade para cobrir a cobertura escolhida, somando reposicao
       apenas quando o estoque atual nao cobre lead time + margem de seguranca.
    5. Prioriza produtos críticos (estoque baixo) e em alerta

    Parâmetros:
    - periodo_dias: Base de cálculo (30/60/90/180 dias)
    - dias_cobertura: Quantos dias de estoque o pedido deve garantir (15/30/45/60/90)
    - apenas_criticos: Filtrar apenas produtos com < 7 dias de estoque
    - incluir_alerta: Incluir produtos que atingiram estoque mínimo
    """
    user, tenant_id = user_and_tenant

    logger.info(
        f"💡 Gerando sugestão de pedido - Fornecedor: {fornecedor_id} | Período: {periodo_dias} dias"
    )

    # Validar fornecedor
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

    # Data inicial para análise
    fornecedor_ids, fornecedor_grupo = _resolver_fornecedores_compra(
        db,
        tenant_id,
        fornecedor,
        incluir_grupo_fornecedor=incluir_grupo_fornecedor,
        fornecedor_grupo_id=fornecedor_grupo_id,
    )

    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=periodo_dias)

    marcas_filtro = marca_ids or marca_ids_brackets or []

    # Buscar produtos do fornecedor com relacionamento e marca
    produtos_fornecedor_query = (
        db.query(Produto, ProdutoFornecedor, Marca)
        .join(ProdutoFornecedor, Produto.id == ProdutoFornecedor.produto_id)
        .outerjoin(Marca, Produto.marca_id == Marca.id)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo,
            or_(
                Produto.participa_sugestao_compra,
                Produto.participa_sugestao_compra.is_(None),
            ),
            or_(Produto.e_granel.is_(False), Produto.e_granel.is_(None)),
            ~Produto.nome.ilike("%granel%"),
            ProdutoFornecedor.fornecedor_id.in_(fornecedor_ids),
            ProdutoFornecedor.ativo,
        )
    )

    if apenas_fornecedor_principal:
        produtos_fornecedor_query = produtos_fornecedor_query.filter(
            or_(
                ProdutoFornecedor.e_principal,
                ProdutoFornecedor.fornecedor_id == Produto.fornecedor_id,
                Produto.fornecedor_id.is_(None),
            ),
        )

    if marcas_filtro:
        produtos_fornecedor_query = produtos_fornecedor_query.filter(
            Produto.marca_id.in_(marcas_filtro)
        )

    produtos_fornecedor_raw = produtos_fornecedor_query.all()
    fornecedores_por_id = {
        item.id: item.nome
        for item in db.query(Cliente.id, Cliente.nome)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.id.in_(fornecedor_ids),
        )
        .all()
    }

    produtos_fornecedor = _selecionar_produtos_fornecedor_sugestao(
        produtos_fornecedor_raw,
        fornecedor_id,
    )

    if not produtos_fornecedor:
        return {
            "fornecedor": {
                "id": fornecedor.id,
                "nome": fornecedor.nome,
                "ids_considerados": fornecedor_ids,
                "grupo": {
                    "id": fornecedor_grupo.id,
                    "nome": fornecedor_grupo.nome,
                }
                if fornecedor_grupo
                else None,
            },
            "periodo_dias": periodo_dias,
            "apenas_fornecedor_principal": apenas_fornecedor_principal,
            "sugestoes": [],
            "resumo": {
                "total_produtos": 0,
                "produtos_criticos": 0,
                "produtos_alerta": 0,
                "valor_total_estimado": 0,
            },
            "mensagem": "Nenhum produto vinculado a este fornecedor",
        }

    sugestoes = []
    total_criticos = 0
    total_alerta = 0
    valor_total = 0

    # Bulk queries de vendas — 2 queries no total em vez de N queries individuais
    ids_produtos = [p.id for p, _pf, _marca in produtos_fornecedor]
    vendas_por_produto = _carregar_vendas_sugestao(
        db,
        tenant_id,
        ids_produtos,
        periodo_dias,
        data_fim,
    )
    movimentacoes_por_produto = _agrupar_movimentacoes_estoque_periodo(
        db,
        tenant_id,
        ids_produtos,
        data_inicio,
        data_fim,
    )

    for produto, produto_fornecedor, marca in produtos_fornecedor:
        # Consumo no período — lookup em vez de query individual
        vendas_stats = vendas_por_produto.get(produto.id) or {
            "vendas_periodo": 0.0,
            "janelas": {str(dias): 0.0 for dias in JANELAS_GIRO_SUGESTAO},
            "origens": [],
            "fontes": [],
            "granel_consumo": {},
        }
        vendas_periodo = _float_seguro_sugestao(vendas_stats.get("vendas_periodo"))
        vendas_janelas = vendas_stats.get("janelas") or {}
        vendas_30 = _float_seguro_sugestao(vendas_janelas.get("30"))

        # Consumo médio diário
        estoque_atual, estoque_info = _obter_estoque_atual_sugestao(
            db, produto, tenant_id
        )
        estoque_minimo = _float_seguro_sugestao(produto.estoque_minimo)
        cobertura_estoque = _calcular_dias_com_estoque(
            movimentacoes_por_produto.get(produto.id, []),
            estoque_atual,
            data_inicio,
            data_fim,
        )

        dias_com_estoque = _float_seguro_sugestao(cobertura_estoque["dias_com_estoque"])
        dias_sem_estoque = _float_seguro_sugestao(cobertura_estoque["dias_sem_estoque"])
        ruptura_ativa = bool(cobertura_estoque["ruptura_ativa"])
        teve_ruptura = bool(cobertura_estoque["teve_ruptura"])

        lead_time = produto_fornecedor.prazo_entrega or 7
        planejamento_compra = _calcular_planejamento_compra_sugestao(
            vendas_periodo=vendas_periodo,
            vendas_30=vendas_30,
            periodo_dias=periodo_dias,
            estoque_atual=estoque_atual,
            estoque_minimo=estoque_minimo,
            dias_com_estoque=dias_com_estoque,
            dias_cobertura=dias_cobertura,
            lead_time=lead_time,
            ruptura_ativa=ruptura_ativa,
            teve_ruptura=teve_ruptura,
        )

        consumo_observado = planejamento_compra["consumo_observado"]
        consumo_recente = planejamento_compra["consumo_recente"]
        quantidade_sugerida = planejamento_compra["quantidade_sugerida"]
        prioridade = planejamento_compra["prioridade"]

        if prioridade == "CR\u00cdTICO":
            total_criticos += 1
        elif prioridade == "ALERTA":
            total_alerta += 1

        tendencia = _calcular_tendencia_vendas_sugestao(
            periodo_dias,
            consumo_observado,
            consumo_recente,
        )

        # Preço unitário
        preco_unitario = _float_seguro_sugestao(
            produto_fornecedor.preco_custo
            if produto_fornecedor.preco_custo is not None
            else produto.preco_custo
        )
        valor_sugestao = quantidade_sugerida * preco_unitario

        # Aplicar filtros
        incluir_produto = True

        if apenas_criticos and prioridade != "CRÍTICO":
            incluir_produto = False

        if not incluir_alerta and prioridade == "ALERTA":
            incluir_produto = False

        # Adicionar à lista (mesmo com qtd 0 para visibilidade se estoque alto)
        if incluir_produto or quantidade_sugerida > 0:
            sugestao = _montar_item_sugestao_compra(
                produto=produto,
                produto_fornecedor=produto_fornecedor,
                marca=marca,
                fornecedor_grupo=fornecedor_grupo,
                fornecedores_por_id=fornecedores_por_id,
                estoque_info=estoque_info,
                vendas_stats=vendas_stats,
                vendas_janelas=vendas_janelas,
                vendas_periodo=vendas_periodo,
                estoque_atual=estoque_atual,
                estoque_minimo=estoque_minimo,
                dias_com_estoque=dias_com_estoque,
                dias_sem_estoque=dias_sem_estoque,
                teve_ruptura=teve_ruptura,
                ruptura_ativa=ruptura_ativa,
                lead_time=lead_time,
                dias_cobertura=dias_cobertura,
                planejamento=planejamento_compra,
                tendencia=tendencia,
                preco_unitario=preco_unitario,
                valor_sugestao=valor_sugestao,
            )
            sugestoes.append(sugestao)
            valor_total += valor_sugestao

    logger.info(
        f"✅ Sugestão gerada: {len(sugestoes)} produtos | {total_criticos} críticos | {total_alerta} em alerta"
    )

    return _montar_resposta_sugestao_compra(
        fornecedor=fornecedor,
        fornecedor_ids=fornecedor_ids,
        fornecedor_grupo=fornecedor_grupo,
        periodo_dias=periodo_dias,
        dias_cobertura=dias_cobertura,
        apenas_fornecedor_principal=apenas_fornecedor_principal,
        data_inicio=data_inicio,
        data_fim=data_fim,
        sugestoes=sugestoes,
        total_criticos=total_criticos,
        total_alerta=total_alerta,
        valor_total=valor_total,
    )
