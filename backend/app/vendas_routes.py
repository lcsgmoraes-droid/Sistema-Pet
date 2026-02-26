# -*- coding: utf-8 -*-
# ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
# Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
# NÃO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenário real
# 3. Validar impacto financeiro

"""
Rotas da API para o módulo de Vendas (PDV)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
import json

from .db import get_session
from .db.transaction import transactional_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .idempotency import idempotent  # ← IDEMPOTÊNCIA
from .security.permissions_decorator import require_permission
from .vendas_models import (
    Venda, VendaItem, VendaPagamento, VendaBaixa
)
from .models import Cliente, User
from .produtos_models import Produto, ProdutoLote, EstoqueMovimentacao, ProdutoKitComponente
from .financeiro_models import ContaReceber, FormaPagamento, LancamentoManual
from .audit_log import log_action
from .utils.logger import logger as struct_logger, set_user_id
from .estoque.service import EstoqueService
from .caixa.service import CaixaService
from .financeiro import ContasReceberService
from .utils.security_helpers import safe_get_produto, safe_get_cliente, safe_get_conta_bancaria, get_by_id_user
from .services.opportunity_background_processor import get_opportunity_processor

router = APIRouter(prefix="/vendas", tags=["vendas"])

# Configurar logger tradicional (manter compatibilidade)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# FUNÇÕES AUXILIARES - CONSOLIDAÇÃO DE LÓGICA REPETIDA
# ============================================================================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant (padrão repetido 13x)"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_venda_ou_404(db: Session, venda_id: int, tenant_id: str):
    """Busca venda com validação de tenant e retorna 404 se não encontrada"""
    venda = db.query(Venda).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    
    return venda


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    """Busca cliente com validação de tenant e retorna 404 se não encontrado"""
    cliente = db.query(Cliente).filter_by(
        id=cliente_id,
        tenant_id=tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    return cliente


# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class VendaItemSchema(BaseModel):
    tipo: str  # 'produto' ou 'servico'
    produto_id: Optional[int] = None
    servico_descricao: Optional[str] = None
    quantidade: float
    preco_unitario: float
    desconto_item: Optional[float] = 0
    subtotal: float
    lote_id: Optional[int] = None
    pet_id: Optional[int] = None  # Vincular item a um pet específico
    is_kit: Optional[bool] = None  # Identificar se o item é um KIT

class VendaPagamentoSchema(BaseModel):
    forma_pagamento: str
    valor: float
    bandeira: Optional[str] = None
    numero_parcelas: Optional[int] = 1  # Número de parcelas para cartão de crédito
    numero_transacao: Optional[str] = None
    numero_autorizacao: Optional[str] = None
    nsu_cartao: Optional[str] = None  # NSU da operadora (para conciliação bancária)
    operadora_id: Optional[int] = None  # 🆕 ID da operadora de cartão
    valor_recebido: Optional[float] = None
    troco: Optional[float] = None

class CriarVendaRequest(BaseModel):
    cliente_id: Optional[int] = None
    vendedor_id: Optional[int] = None
    funcionario_id: Optional[int] = None  # Funcionário/Veterinário que recebe comissão
    itens: List[VendaItemSchema]
    desconto_valor: Optional[float] = 0
    desconto_percentual: Optional[float] = 0
    observacoes: Optional[str] = None
    tem_entrega: bool = False
    taxa_entrega: Optional[float] = 0
    percentual_taxa_loja: Optional[float] = 100  # Percentual 0-100
    percentual_taxa_entregador: Optional[float] = 0  # Percentual 0-100
    entregador_id: Optional[int] = None
    loja_origem: Optional[str] = None
    endereco_entrega: Optional[str] = None
    distancia_km: Optional[float] = None
    valor_por_km: Optional[float] = None
    observacoes_entrega: Optional[str] = None

class FinalizarVendaRequest(BaseModel):
    pagamentos: List[VendaPagamentoSchema]

class CancelarVendaRequest(BaseModel):
    motivo: str

# [DEPRECATED - Sprint 1 BLOCO 3] Movido para app/api/endpoints/configuracoes_entrega.py
# class ConfiguracaoEntregaSchema(BaseModel):
#     valor_por_km: Optional[float] = None
#     taxa_minima: Optional[float] = None
#     raio_maximo_km: Optional[float] = None
#     lojas: Optional[List[str]] = []
#     google_maps_api_key: Optional[str] = None


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calcular_totais_venda(itens: List, desconto_valor: float, desconto_percentual: float, taxa_entrega: float) -> dict:
    """
    Calcula os totais da venda (subtotal, desconto, total)
    
    Args:
        itens: Lista de itens da venda
        desconto_valor: Valor do desconto em reais
        desconto_percentual: Percentual de desconto
        taxa_entrega: Taxa de entrega
    
    Returns:
        Dict com subtotal, desconto_valor, total
    """
    # Calcular subtotal dos itens
    subtotal = sum(item.subtotal for item in itens)
    
    # Aplicar desconto (se houver)
    if desconto_percentual > 0:
        desconto_valor = subtotal * (desconto_percentual / 100)
    
    # Calcular total
    total = subtotal - desconto_valor + taxa_entrega
    
    return {
        'subtotal': subtotal,
        'desconto_valor': desconto_valor,
        'total': total
    }


# ============================================================================
# ENDPOINTS - CONFIGURAÇÕES DE ENTREGA [DEPRECATED]
# ============================================================================
# [DEPRECATED - Sprint 1 BLOCO 3] Endpoints movidos para app/api/endpoints/configuracoes_entrega.py
# Nova estrutura: tenant_id (UUID), entregador_padrao_id (Integer), ponto_inicial_rota
# Antiga estrutura (user_id, valor_por_km, taxa_minima) não é mais usada


# ============================================================================
# ENDPOINTS - VENDAS CRUD
# ============================================================================

@router.get('')
def listar_vendas(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=5000),  # Aumentado limite para relatórios
    status: Optional[str] = None,
    cliente_id: Optional[int] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    busca: Optional[str] = None,
    tem_entrega: Optional[bool] = None,
    sem_rota: Optional[bool] = None,  # Filtrar vendas sem rota de entrega
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista as vendas com filtros - OTIMIZADO com eager loading"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    try:
        # EAGER LOADING: Carregar todas as relações de uma vez (evita N+1 queries)
        query = db.query(Venda).options(
            joinedload(Venda.cliente),          # Cliente da venda
            joinedload(Venda.pagamentos),       # Pagamentos da venda
            joinedload(Venda.itens).joinedload(VendaItem.produto)  # Itens + Produtos
        ).filter_by(
            tenant_id=tenant_id
        )
    except Exception as e:
        logger.error(f"❌ Erro ao criar query base: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar query: {str(e)}")
    
    # Aplicar filtros
    if status:
        query = query.filter_by(status=status)
    
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    
    if tem_entrega is not None:
        query = query.filter_by(tem_entrega=tem_entrega)
    
    # Filtrar vendas sem rota de entrega
    if sem_rota:
        from app.rotas_entrega_models import RotaEntrega
        # Buscar vendas que não têm rota associada
        subquery = db.query(RotaEntrega.venda_id).filter(
            RotaEntrega.tenant_id == tenant_id
        ).subquery()
        query = query.filter(~Venda.id.in_(subquery))
    
    if data_inicio:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0)
        query = query.filter(Venda.data_venda >= data_inicio_dt)
    
    if data_fim:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(Venda.data_venda <= data_fim_dt)
    
    if busca:
        try:
            # Buscar por número da venda, observações OU nome do cliente
            # SQLite: usar LIKE com lower() para case-insensitive
            busca_lower = f'%{busca.lower()}%'
            query = query.outerjoin(Cliente, Venda.cliente_id == Cliente.id).filter(
                or_(
                    Venda.numero_venda.contains(busca),
                    func.lower(Cliente.nome).like(busca_lower)
                )
            )
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar filtro de busca: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")
    
    # Ordenar por data mais recente
    query = query.order_by(desc(Venda.data_venda))
    
    # Contar total
    total = query.count()
    
    # Paginar
    vendas = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        'vendas': [v.to_dict() for v in vendas],
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'current_page': page
    }


@router.get('/{venda_id}')
def buscar_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Busca uma venda específica"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    venda = db.query(Venda).options(
        joinedload(Venda.itens).joinedload(VendaItem.produto)
    ).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    
    # 🐛 DEBUG: Log dos valores de entrega
    logger.info(
        f"🔍 GET venda/{venda_id}: percentual_loja={venda.percentual_taxa_loja}, "
        f"percentual_entregador={venda.percentual_taxa_entregador}, "
        f"valor_loja={venda.valor_taxa_loja}, valor_entregador={venda.valor_taxa_entregador}"
    )
    
    return venda.to_dict()


@router.post('')
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita criação duplicada de vendas
@require_permission("vendas.criar")
async def criar_venda(
    dados: CriarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria uma nova venda.
    
    🎯 ROTA REFATORADA: Agora usa VendaService como orquestrador central.
    A rota apenas valida o request e chama o service.
    """
    from app.vendas.service import VendaService
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # ========================================
    # 🔒 TRAVA 1 — VALIDAÇÃO: PRODUTO PAI NÃO PODE SER VENDIDO
    # ========================================
    for item in dados.itens:
        if item.produto_id:
            produto = db.query(Produto).filter(
                Produto.id == item.produto_id,
                Produto.tenant_id == tenant_id
            ).first()
            
            if produto and produto.is_parent:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Produto '{produto.nome}' possui variações e não pode ser vendido diretamente. Selecione uma variação específica (cor, tamanho, etc.) para adicionar ao carrinho."
                )
    
    # ========================================
    # 🔒 TRAVA 2 — VALIDAÇÃO: ENDEREÇO OBRIGATÓRIO QUANDO TEM ENTREGA
    # ========================================
    if dados.tem_entrega and not dados.endereco_entrega:
        raise HTTPException(
            status_code=400,
            detail="❌ Endereço de entrega é obrigatório quando a venda tem entrega. Selecione o endereço do cliente ou digite um novo."
        )
    
    # ========================================
    # 🔒 TRAVA 3 — VALIDAÇÃO: ENTREGADOR OBRIGATÓRIO QUANDO TEM ENTREGA
    # ========================================
    if dados.tem_entrega and not dados.entregador_id:
        raise HTTPException(
            status_code=400,
            detail="❌ Entregador é obrigatório quando a venda tem entrega. Selecione um entregador antes de salvar."
        )
    
    # Preparar payload para o service
    payload = {
        'cliente_id': dados.cliente_id,
        'vendedor_id': dados.vendedor_id,
        'funcionario_id': dados.funcionario_id,
        'itens': [item.dict() for item in dados.itens],
        'desconto_valor': dados.desconto_valor,
        'desconto_percentual': dados.desconto_percentual,
        'observacoes': dados.observacoes,
        'tem_entrega': dados.tem_entrega,
        'taxa_entrega': dados.taxa_entrega,
        'percentual_taxa_loja': dados.percentual_taxa_loja,
        'percentual_taxa_entregador': dados.percentual_taxa_entregador,
        'entregador_id': dados.entregador_id,
        'loja_origem': dados.loja_origem,
        'endereco_entrega': dados.endereco_entrega,
        'distancia_km': dados.distancia_km,
        'valor_por_km': dados.valor_por_km,
        'observacoes_entrega': dados.observacoes_entrega,
        'tenant_id': tenant_id
    }
    
    # Chamar service (toda lógica de negócio está lá)
    venda_dict = VendaService.criar_venda(
        payload=payload,
        user_id=current_user.id,
        db=db
    )
    
    # ============================================================================
    # 🤖 PROCESSAMENTO PASSIVO DE OPORTUNIDADES (background, não-bloqueante)
    # ============================================================================
    try:
        from uuid import UUID
        
        # Obter processador para sessão (tenant + session_id único)
        session_id = f"venda_{venda_dict['id']}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)),
            session_id=session_id
        )
        
        # GATILHO 1: Cliente selecionado (se houver cliente)
        if dados.cliente_id:
            processor.on_client_selected(cliente_id=UUID(str(dados.cliente_id)))
        
        # GATILHO 2: Itens adicionados ao carrinho
        if dados.itens:
            itens_contexto = [
                {
                    "tipo": item.tipo,
                    "produto_id": item.produto_id,
                    "quantidade": float(item.quantidade),
                    "preco": float(item.preco_unitario),
                    "categoria": None  # Placeholder - expandir com dados do produto se necessário
                }
                for item in dados.itens
            ]
            processor.on_item_added(
                cliente_id=UUID(str(dados.cliente_id)) if dados.cliente_id else None,
                itens_carrinho=itens_contexto
            )
    except Exception as e:
        # Fail-safe: Nunca deixar background processor afetar fluxo principal
        logger.debug(f"Background processor (criar): {str(e)}")
        pass
    
    return venda_dict


@router.put('/{venda_id}')
def atualizar_venda(
    venda_id: int,
    dados: CriarVendaRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma venda existente (somente vendas abertas)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar venda
    venda = db.query(Venda).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    
    # Só permite atualizar vendas abertas
    if venda.status != 'aberta':
        raise HTTPException(
            status_code=400, 
            detail=f'Não é possível atualizar venda com status "{venda.status}". Apenas vendas abertas podem ser atualizadas.'
        )
    
    # Validações
    if not dados.itens or len(dados.itens) == 0:
        raise HTTPException(status_code=400, detail='A venda deve ter pelo menos um item')
    
    # Validar endereço obrigatório quando tem entrega
    if dados.tem_entrega and not dados.endereco_entrega:
        raise HTTPException(
            status_code=400,
            detail="❌ Endereço de entrega é obrigatório quando a venda tem entrega. Selecione o endereço do cliente ou digite um novo."
        )
    
    # Validar entregador obrigatório quando tem entrega
    if dados.tem_entrega and not dados.entregador_id:
        raise HTTPException(
            status_code=400,
            detail="❌ Entregador é obrigatório quando a venda tem entrega. Selecione um entregador antes de salvar."
        )
    
    # Calcular novos totais
    totais = calcular_totais_venda(
        dados.itens,
        dados.desconto_valor or 0,
        dados.desconto_percentual or 0,
        dados.taxa_entrega or 0
    )
    
    logger.info(f"\n🔄 ATUALIZANDO VENDA {venda_id}:")
    logger.info(f"   funcionario_id recebido: {dados.funcionario_id}")
    logger.info(f"   funcionario_id anterior: {venda.funcionario_id}")
    
    # Atualizar campos da venda
    venda.cliente_id = dados.cliente_id
    venda.vendedor_id = dados.vendedor_id or current_user.id
    venda.funcionario_id = dados.funcionario_id  # ✅ Funcionário/Veterinário que recebe comissão
    
    logger.info(f"   funcionario_id novo: {venda.funcionario_id}")
    
    venda.subtotal = totais['subtotal']
    venda.desconto_valor = totais['desconto_valor']
    venda.desconto_percentual = dados.desconto_percentual or 0
    venda.total = totais['total']
    venda.observacoes = dados.observacoes
    venda.tem_entrega = dados.tem_entrega
    venda.taxa_entrega = dados.taxa_entrega or 0
    venda.entregador_id = dados.entregador_id
    venda.loja_origem = dados.loja_origem
    venda.endereco_entrega = dados.endereco_entrega
    venda.distancia_km = dados.distancia_km
    venda.valor_por_km = dados.valor_por_km
    venda.observacoes_entrega = dados.observacoes_entrega
    venda.status_entrega = 'pendente' if dados.tem_entrega else None
    venda.updated_at = datetime.now()
    
    # 🔄 DEVOLVER ESTOQUE dos produtos REMOVIDOS
    # Compara itens antigos com novos e devolve o que foi removido
    itens_antigos = db.query(VendaItem).filter_by(venda_id=venda.id).all()
    produtos_antigos_ids = {item.produto_id for item in itens_antigos if item.produto_id}
    produtos_novos_ids = {item.produto_id for item in dados.itens if item.produto_id}
    produtos_removidos_ids = produtos_antigos_ids - produtos_novos_ids
    
    # Estornar estoque dos produtos removidos
    for item_antigo in itens_antigos:
        if item_antigo.produto_id in produtos_removidos_ids:
            try:
                logger.info(f"📦 Devolvendo estoque (produto removido): Produto {item_antigo.produto_id} +{item_antigo.quantidade}")
                EstoqueService.estornar_estoque(
                    produto_id=item_antigo.produto_id,
                    quantidade=float(item_antigo.quantidade),
                    motivo='ajuste',
                    referencia_id=venda.id,
                    referencia_tipo='venda_editada',
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                    db=db,
                    documento=None,
                    observacao=f'Produto removido da venda #{venda.id}'
                )
                log_action(
                    db=db,
                    user_id=current_user.id,
                    action='update',
                    entity_type='produtos',
                    entity_id=item_antigo.produto_id,
                    details=f'Estorno (+{item_antigo.quantidade}) - Produto removido da venda #{venda.id}'
                )
            except ValueError as e:
                logger.error(f"❌ Erro ao estornar estoque: {e}")
    
    # Excluir itens antigos
    db.query(VendaItem).filter_by(venda_id=venda.id).delete()
    
    # Criar novos itens
    for item_data in dados.itens:
        # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
        item = VendaItem(
            venda_id=venda.id,
            tenant_id=tenant_id,  # ✅ Garantir isolamento entre empresas
            tipo=item_data.tipo,
            produto_id=item_data.produto_id,
            servico_descricao=item_data.servico_descricao,
            quantidade=item_data.quantidade,
            preco_unitario=item_data.preco_unitario,
            desconto_item=item_data.desconto_item or 0,
            subtotal=item_data.subtotal,
            lote_id=item_data.lote_id,
            pet_id=item_data.pet_id
        )
        db.add(item)
    
    db.commit()
    db.refresh(venda)
    
    log_action(db, current_user.id, 'update', 'vendas', venda.id,
               details=f'Venda {venda.numero_venda} atualizada - Total: R$ {totais["total"]:.2f}')
    
    # ============================================================================
    # 🚚 CRIAR ROTA DE ENTREGA SE NECESSÁRIO (e não existir)
    # ============================================================================
    if venda.tem_entrega and venda.endereco_entrega:
        from app.rotas_entrega_models import RotaEntrega
        from app.models import Cliente, ConfiguracaoEntrega
        
        # Verificar se já existe rota para esta venda
        rota_existente = db.query(RotaEntrega).filter(
            RotaEntrega.venda_id == venda.id,
            RotaEntrega.tenant_id == tenant_id
        ).first()
        
        if not rota_existente:
            try:
                # Buscar entregador padrão
                entregador_padrao = db.query(Cliente).filter(
                    Cliente.tenant_id == tenant_id,
                    Cliente.entregador_padrao == True,
                    Cliente.entregador_ativo == True,
                    Cliente.ativo == True
                ).first()
                
                if entregador_padrao:
                    from app.utils.timezone import now_brasilia
                    
                    # Criar rota de entrega
                    rota = RotaEntrega(
                        tenant_id=tenant_id,
                        venda_id=venda.id,
                        entregador_id=entregador_padrao.id,
                        endereco_destino=venda.endereco_entrega,
                        taxa_entrega_cliente=float(venda.taxa_entrega) if venda.taxa_entrega else 0,
                        status="pendente",
                        created_by=current_user.id,
                        moto_da_loja=not entregador_padrao.moto_propria,
                        created_at=now_brasilia(),
                        updated_at=now_brasilia()
                    )
                    rota.numero = f"ROTA-{now_brasilia().strftime('%Y%m%d%H%M%S')}"
                    
                    # Buscar configuração de entrega para ponto inicial
                    config_entrega = db.query(ConfiguracaoEntrega).filter(
                        ConfiguracaoEntrega.tenant_id == tenant_id
                    ).first()
                    
                    if config_entrega:
                        ponto_inicial = (
                            f"{config_entrega.logradouro or ''}"
                            f"{', ' + config_entrega.numero if config_entrega.numero else ''}"
                            f"{' - ' + config_entrega.bairro if config_entrega.bairro else ''}"
                            f"{' - ' + config_entrega.cidade if config_entrega.cidade else ''}"
                            f"/{config_entrega.estado if config_entrega.estado else ''}"
                        ).strip()
                        rota.ponto_inicial_rota = ponto_inicial
                        rota.ponto_final_rota = ponto_inicial
                        rota.retorna_origem = True
                    
                    db.add(rota)
                    db.commit()
                    logger.info(f"🚚 Rota de entrega criada ao atualizar venda: {rota.numero} (ID={rota.id}, Entregador={entregador_padrao.nome})")
                else:
                    logger.warning(f"⚠️ Venda #{venda.numero_venda} atualizada com entrega mas não há entregador padrão configurado")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao criar rota de entrega ao atualizar venda: {e}")
                # Não falha a atualização da venda por erro na criação da rota
        else:
            logger.info(f"ℹ️ Venda {venda.numero_venda} já possui rota (ID={rota_existente.id}), não criando nova")
    
    # ============================================================================
    # ❌ REMOVIDO: Não regenerar comissões no endpoint de edição
    # ============================================================================
    # MOTIVO: Quando uma venda tem múltiplos pagamentos (baixa parcial + nova baixa),
    # deletar e regenerar cria apenas UMA comissão com o total, perdendo o histórico
    # de comissões por parcela.
    # 
    # SOLUÇÃO: Comissões são geradas APENAS no endpoint /finalizar, incrementalmente,
    # com parcela_numero correto para cada pagamento.
    # ============================================================================
    
    # ============================================================================
    # 🤖 PROCESSAMENTO PASSIVO DE OPORTUNIDADES (background, não-bloqueante)
    # ============================================================================
    try:
        from uuid import UUID
        
        # Obter processador para sessão
        session_id = f"venda_{venda.id}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)),
            session_id=session_id
        )
        
        # 🔴 CASO ESPECIAL: Cliente removido da venda
        if dados.cliente_id is None and venda.cliente_id is not None:
            # Invalidar cache quando cliente é removido
            processor.cleanup()
        else:
            # GATILHO 1: Cliente selecionado/alterado (se houver cliente)
            if dados.cliente_id:
                processor.on_client_selected(cliente_id=UUID(str(dados.cliente_id)))
            
            # GATILHO 2/3: Itens atualizados (pode ser adição ou remoção)
            if dados.itens:
                itens_contexto = [
                    {
                        "tipo": item.tipo,
                        "produto_id": item.produto_id,
                        "quantidade": float(item.quantidade),
                        "preco": float(item.preco_unitario),
                        "categoria": None
                    }
                    for item in dados.itens
                ]
                
                # Atualização: pode ser adição ou remoção, usar on_item_added genericamente
                # (background processor analisa contexto internamente)
                processor.on_item_added(
                    cliente_id=UUID(str(dados.cliente_id)) if dados.cliente_id else None,
                    itens_carrinho=itens_contexto
                )
    except Exception as e:
        # Fail-safe: Nunca deixar background processor afetar fluxo principal
        logger.debug(f"Background processor (atualizar): {str(e)}")
        pass
    
    # ============================================================================
    # 🆕 VERIFICAR SE VENDA JÁ ESTÁ TOTALMENTE PAGA E GERAR COMISSÕES
    # ============================================================================
    # Cenário: Usuário registrou pagamento primeiro, depois adicionou funcionário comissionado
    # Neste caso, precisa verificar se venda está paga e gerar comissões
    if venda.funcionario_id and venda.status != 'finalizada':
        try:
            from sqlalchemy import text
            
            # Buscar total pago
            result = db.execute(text("""
                SELECT COALESCE(SUM(valor), 0) as total_pago
                FROM venda_pagamentos
                WHERE venda_id = :venda_id
            """), {'venda_id': venda.id})
            
            total_pago_row = result.fetchone()
            total_pago = Decimal(str(total_pago_row[0])) if total_pago_row else Decimal('0')
            total_venda = Decimal(str(venda.total))
            
            logger.info(f"📊 Venda {venda.id}: Total={total_venda}, Pago={total_pago}")
            
            # Se está totalmente paga, finalizar e gerar comissões
            if total_pago >= total_venda - Decimal('0.01'):  # Margem de 1 centavo
                logger.info(f"✅ Venda {venda.id} está totalmente paga, finalizando e gerando comissões...")
                
                # Atualizar status
                status_anterior = venda.status
                venda.status = 'finalizada'
                venda.updated_at = datetime.now()
                db.commit()
                db.refresh(venda)
                
                # Gerar comissões para cada pagamento
                from app.comissoes_service import gerar_comissoes_venda
                
                todos_pagamentos = db.execute(text("""
                    SELECT vp.id, vp.forma_pagamento, vp.valor, vp.data_pagamento
                    FROM venda_pagamentos vp
                    WHERE vp.venda_id = :venda_id
                    ORDER BY vp.data_pagamento ASC
                """), {'venda_id': venda.id}).fetchall()
                
                # Verificar quais pagamentos já têm comissão
                comissoes_existentes = db.execute(text("""
                    SELECT DISTINCT parcela_numero
                    FROM comissoes_itens
                    WHERE venda_id = :venda_id AND funcionario_id = :funcionario_id
                """), {'venda_id': venda.id, 'funcionario_id': venda.funcionario_id}).fetchall()
                
                parcelas_com_comissao = {row[0] for row in comissoes_existentes}
                
                comissoes_geradas = 0
                total_comissoes = Decimal('0')
                
                for idx, pagamento_row in enumerate(todos_pagamentos, start=1):
                    parcela_numero = idx
                    
                    if parcela_numero in parcelas_com_comissao:
                        continue
                    
                    valor_pagamento = Decimal(str(pagamento_row[2]))
                    forma_pagamento = pagamento_row[1]
                    
                    resultado = gerar_comissoes_venda(
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=valor_pagamento,
                        forma_pagamento=forma_pagamento,
                        parcela_numero=parcela_numero,
                        db=db
                    )
                    
                    if resultado and resultado.get('success') and not resultado.get('duplicated'):
                        comissoes_geradas += 1
                        total_comissoes += Decimal(str(resultado.get('total_comissao', 0)))
                
                if comissoes_geradas > 0:
                    logger.info(f"✅ {comissoes_geradas} comissões geradas - Total: R$ {total_comissoes:.2f}")
                    struct_logger.info(
                        event="COMMISSION_GENERATED_ON_UPDATE",
                        message=f"Comissões geradas ao atualizar venda com funcionário",
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        total_comissoes=float(total_comissoes),
                        status_anterior=status_anterior
                    )
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar pagamentos e gerar comissões: {str(e)}", exc_info=True)
            # Não falha a atualização por erro nas comissões
    
    return venda.to_dict()


@router.post('/{venda_id}/marcar-entregue')
async def marcar_venda_entregue(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Confirma que o cliente retirou o pedido na loja (ou terceiro apresentou a palavra-chave)."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = db.query(Venda).filter(Venda.id == venda_id, Venda.tenant_id == tenant_id).first()
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    venda.status_entrega = "entregue"
    venda.data_entrega = datetime.now()
    db.commit()
    return {"id": venda_id, "status_entrega": "entregue", "data_entrega": venda.data_entrega.isoformat()}


@router.post('/{venda_id}/finalizar')
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita finalização duplicada
async def finalizar_venda(
    venda_id: int,
    dados: FinalizarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Finaliza uma venda com os pagamentos.
    
    REFATORADO: Utiliza VendaService.finalizar_venda() para orquestração atômica.
    Esta rota agora é um thin wrapper que apenas processa comissões e lembretes pós-commit.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # 🔒 HARDENING 1: Logs estruturados e validação de estado
    set_user_id(current_user.id)
    struct_logger.info(
        event="FINALIZE_START",
        message=f"Iniciando finalização da venda #{venda_id}",
        venda_id=venda_id,
        total_pagamentos=len(dados.pagamentos) if dados and dados.pagamentos else 0
    )
    
    # ========================================
    # 🔒 VALIDAÇÃO: ENTREGADOR OBRIGATÓRIO QUANDO TEM ENTREGA
    # ========================================
    venda_temp = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if venda_temp and venda_temp.tem_entrega and not venda_temp.entregador_id:
        raise HTTPException(
            status_code=400,
            detail="❌ Não é possível finalizar. Entregador é obrigatório quando a venda tem entrega. Atribua um entregador antes de finalizar."
        )
    
    # ============================================================
    # 🔥 ORQUESTRAÇÃO ATÔMICA VIA VendaService
    # ============================================================
    
    from app.vendas import VendaService
    
    # Converter pagamentos do request para formato do service
    pagamentos_list = [
        {
            'forma_pagamento': p.forma_pagamento,
            'valor': p.valor,
            'numero_parcelas': p.numero_parcelas,
            'bandeira': getattr(p, 'bandeira', None),
            'nsu_cartao': getattr(p, 'nsu_cartao', None),
            'operadora_id': getattr(p, 'operadora_id', None)  # 🆕 Capturar operadora
        }
        for p in dados.pagamentos
    ] if dados.pagamentos else []
    
    # Executar finalização com transação atômica única
    resultado = VendaService.finalizar_venda(
        venda_id=venda_id,
        pagamentos=pagamentos_list,
        user_id=current_user.id,
        user_nome=current_user.nome,
        tenant_id=tenant_id,
        db=db
    )
    
    # Log de sucesso
    struct_logger.info(
        event="FINALIZE_SUCCESS",
        message=f"Venda finalizada com sucesso",
        venda_id=venda_id,
        numero_venda=resultado['venda']['numero_venda'],
        status=resultado['venda']['status'],
        total_pago=resultado['venda']['total_pago']
    )
    
    # ============================================================
    # ETAPA PÓS-COMMIT: COMISSÕES E LEMBRETES (operações secundárias)
    # ============================================================
    
    # Recarregar venda para ter dados atualizados após commit
    venda = db.query(Venda).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada após finalização')
    
    # 🆕 GERAR COMISSÕES AUTOMATICAMENTE (apenas se funcionário/veterinário foi selecionado)
    if venda.funcionario_id:
        try:
            from app.comissoes_service import gerar_comissoes_venda
            from sqlalchemy import text
            
            # � BUSCAR TODOS OS PAGAMENTOS DA VENDA (não só os novos!)
            # Precisamos gerar comissões para TODOS os pagamentos que ainda não têm comissão
            todos_pagamentos = db.execute(text("""
                SELECT vp.id, vp.forma_pagamento, vp.valor, vp.data_pagamento
                FROM venda_pagamentos vp
                WHERE vp.venda_id = :venda_id
                ORDER BY vp.data_pagamento ASC
            """), {'venda_id': venda.id}).fetchall()
            
            if not todos_pagamentos:
                logger.info("ℹ️  Nenhum pagamento encontrado na venda")
            else:
                # 🔢 Verificar quais pagamentos já têm comissão
                comissoes_existentes = db.execute(text("""
                    SELECT DISTINCT parcela_numero
                    FROM comissoes_itens
                    WHERE venda_id = :venda_id AND funcionario_id = :funcionario_id
                """), {'venda_id': venda.id, 'funcionario_id': venda.funcionario_id}).fetchall()
                
                parcelas_com_comissao = {row[0] for row in comissoes_existentes}
                logger.info(f"📊 Pagamentos: {len(todos_pagamentos)} total, {len(parcelas_com_comissao)} já com comissão")
                
                # 🔄 GERAR UMA COMISSÃO PARA CADA PAGAMENTO SEM COMISSÃO
                comissoes_geradas = 0
                total_comissoes = Decimal('0')
                
                for idx, pagamento_row in enumerate(todos_pagamentos, start=1):
                    parcela_numero = idx
                    
                    # Pular se já tem comissão
                    if parcela_numero in parcelas_com_comissao:
                        logger.info(f"⏭️  Parcela {parcela_numero} já tem comissão - pulando")
                        continue
                    
                    valor_pagamento = Decimal(str(pagamento_row[2]))
                    forma_pagamento = pagamento_row[1]
                    
                    struct_logger.info(
                        event="COMMISSION_START",
                        message="Gerando comissão para pagamento",
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=float(valor_pagamento),
                        forma_pagamento=forma_pagamento,
                        parcela_numero=parcela_numero
                    )
                    
                    resultado = gerar_comissoes_venda(
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=valor_pagamento,
                        forma_pagamento=forma_pagamento,  # ✅ Passa forma de pagamento correta
                        parcela_numero=parcela_numero,
                        db=db
                    )
                    
                    if resultado and resultado.get('success'):
                        if not resultado.get('duplicated'):
                            comissoes_geradas += 1
                            total_comissoes += Decimal(str(resultado.get('total_comissao', 0)))
                            struct_logger.info(
                                event="COMMISSION_GENERATED",
                                message="Comissão gerada para pagamento",
                                venda_id=venda.id,
                                parcela_numero=parcela_numero,
                                valor_comissao=float(resultado.get('total_comissao', 0))
                            )
                        else:
                            struct_logger.warning(
                                event="COMMISSION_DUPLICATED",
                                message="Comissão já existia (proteção idempotente)",
                                venda_id=venda.id,
                                parcela_numero=parcela_numero
                            )
                
                if comissoes_geradas > 0:
                    logger.info(f"✅ {comissoes_geradas} comissões geradas - Total: R$ {total_comissoes}")
                else:
                    logger.info("ℹ️  Nenhuma comissão nova gerada (todas já existiam)")
                
        except Exception as e:
            logger.error(f"⚠️ Erro ao gerar comissões (venda {venda.id}): {str(e)}", exc_info=True)
            # Não abortar a finalização da venda por erro nas comissões
    else:
        logger.info("ℹ️  Venda sem funcionário - comissões não geradas")
    
    # 🔔 SISTEMA DE RECORRÊNCIA - Criar/Atualizar lembretes automaticamente
    from app.produtos_models import Lembrete
    from app.models import Pet
    
    lembretes_criados = []
    lembretes_atualizados = []
    
    try:
        for item in venda.itens:
            # Apenas produtos com pet_id vinculado e que tenham recorrência
            if item.tipo == 'produto' and item.produto_id and item.pet_id:
                # 🔒 SEGURANÇA: Validar que produto pertence ao usuário
                produto = safe_get_produto(db, item.produto_id, current_user.id)
                
                # 🔒 SEGURANÇA: Validar que pet pertence ao cliente do usuário
                pet = db.query(Pet).filter(
                    Pet.id == item.pet_id,
                    Pet.cliente_id == venda.cliente_id
                ).first()
                
                if not produto or not pet:
                    continue  # Ignorar se não encontrado (segurança)
                
                if produto and pet and produto.tem_recorrencia and produto.intervalo_dias:
                    # Verificar se já existe lembrete PENDENTE para este produto+pet
                    lembrete_existente = db.query(Lembrete).filter(
                        Lembrete.cliente_id == venda.cliente_id,
                        Lembrete.pet_id == item.pet_id,
                        Lembrete.produto_id == item.produto_id,
                        Lembrete.status.in_(['pendente', 'notificado'])
                    ).first()
                    
                    if lembrete_existente:
                        # ✅ CLIENTE JÁ TINHA LEMBRETE - DAR CHECK AUTOMÁTICO
                        historico = json.loads(lembrete_existente.historico_doses) if lembrete_existente.historico_doses else []
                        historico.append({
                            "dose": lembrete_existente.dose_atual,
                            "data": datetime.utcnow().isoformat(),
                            "comprou": True,
                            "status": "completado",
                            "venda_id": venda.id
                        })
                        
                        # Marcar como completado
                        lembrete_existente.status = 'completado'
                        lembrete_existente.data_completado = datetime.utcnow()
                        lembrete_existente.historico_doses = json.dumps(historico)
                        
                        # Verificar se é a última dose
                        if lembrete_existente.dose_total and lembrete_existente.dose_atual >= lembrete_existente.dose_total:
                            # Última dose - NÃO criar novo lembrete
                            lembretes_atualizados.append({
                                "acao": "finalizado",
                                "produto": produto.nome,
                                "pet": pet.nome,
                                "dose": f"{lembrete_existente.dose_atual}/{lembrete_existente.dose_total}"
                            })
                        else:
                            # Criar novo lembrete para próxima dose
                            data_proxima = datetime.utcnow() + timedelta(days=produto.intervalo_dias)
                            data_notificacao = data_proxima - timedelta(days=7)
                            
                            novo_lembrete = Lembrete(
                                user_id=current_user.id,
                                cliente_id=venda.cliente_id,
                                pet_id=item.pet_id,
                                produto_id=item.produto_id,
                                venda_id=venda.id,
                                data_compra=datetime.utcnow(),
                                data_proxima_dose=data_proxima,
                                data_notificacao_7_dias=data_notificacao,
                                status='pendente',
                                quantidade_recomendada=float(item.quantidade),
                                preco_estimado=produto.preco_venda,
                                dose_atual=lembrete_existente.dose_atual + 1,
                                dose_total=lembrete_existente.dose_total,
                                historico_doses=json.dumps(historico)
                            )
                            db.add(novo_lembrete)
                            
                            lembretes_atualizados.append({
                                "acao": "renovado",
                                "produto": produto.nome,
                                "pet": pet.nome,
                                "dose": f"{novo_lembrete.dose_atual}/{novo_lembrete.dose_total or '∞'}"
                            })
                    else:
                        # ✨ PRIMEIRA VENDA COM RECORRÊNCIA - CRIAR LEMBRETE
                        data_proxima = datetime.utcnow() + timedelta(days=produto.intervalo_dias)
                        data_notificacao = data_proxima - timedelta(days=7)
                        
                        historico_inicial = [{
                            "dose": 1,
                            "data": datetime.utcnow().isoformat(),
                            "comprou": True,
                            "status": "criado",
                            "venda_id": venda.id
                        }]
                        
                        novo_lembrete = Lembrete(
                            user_id=current_user.id,
                            cliente_id=venda.cliente_id,
                            pet_id=item.pet_id,
                            produto_id=item.produto_id,
                            venda_id=venda.id,
                            data_compra=datetime.utcnow(),
                            data_proxima_dose=data_proxima,
                            data_notificacao_7_dias=data_notificacao,
                            status='pendente',
                            quantidade_recomendada=float(item.quantidade),
                            preco_estimado=produto.preco_venda,
                            dose_atual=1,
                            dose_total=produto.numero_doses,
                            historico_doses=json.dumps(historico_inicial)
                        )
                        db.add(novo_lembrete)
                        
                        lembretes_criados.append({
                            "produto": produto.nome,
                            "pet": pet.nome,
                            "proxima_dose": data_proxima.strftime("%d/%m/%Y"),
                            "dose_total": produto.numero_doses or "∞"
                        })
        
        if lembretes_criados or lembretes_atualizados:
            logger.info(f"🔔 Lembretes: {len(lembretes_criados)} criados, {len(lembretes_atualizados)} atualizados")
    
    except Exception as e:
        logger.error(f"⚠️ Erro ao processar lembretes: {str(e)}")
        # Não abortar a venda por erro nos lembretes
    
    db.commit()
    
    log_action(db, current_user.id, 'UPDATE', 'vendas', venda.id,
               details=f'Venda {venda.numero_venda} finalizada - Total: R$ {float(venda.total):.2f}')
    
    # ============================================================================
    # 💾 INVALIDAR CACHE DE OPORTUNIDADES (venda finalizada)
    # ============================================================================
    try:
        from uuid import UUID
        session_id = f"venda_{venda.id}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)),
            session_id=session_id
        )
        processor.cleanup()  # Limpa processador e invalida cache
    except Exception as e:
        logger.debug(f"Cache cleanup (finalizar): {str(e)}")
        pass
    
    # ✅ LOG DE SUCESSO ESTRUTURADO
    total_pago = sum(float(p.valor) for p in venda.pagamentos) if venda.pagamentos else 0
    struct_logger.info(
        event="FINALIZE_COMPLETE",
        message=f"Venda finalizada completamente (com comissões e lembretes)",
        venda_id=venda_id,
        numero_venda=venda.numero_venda,
        status_final=venda.status,
        total_venda=float(venda.total),
        total_pagamentos=total_pago,
        forma_pagamento=dados.pagamentos[0].forma_pagamento if dados.pagamentos else None,
        lembretes_criados=len(lembretes_criados),
        lembretes_atualizados=len(lembretes_atualizados)
    )
    
    # Adicionar informações de lembretes no retorno
    venda_dict = venda.to_dict()
    if lembretes_criados or lembretes_atualizados:
        venda_dict['lembretes'] = {
            "criados": lembretes_criados,
            "atualizados": lembretes_atualizados
        }
    
    # Adicionar dados do resultado do VendaService (se disponível)
    if 'operacoes' in resultado:
        venda_dict['resultado_operacoes'] = resultado['operacoes']
    
    return venda_dict


@router.post('/{venda_id}/cancelar')
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita cancelamento duplicado
async def cancelar_venda(
    venda_id: int,
    dados: CancelarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cancela uma venda realizando estorno completo.
    
    🎯 ROTA REFATORADA: Agora usa VendaService como orquestrador central.
    A rota apenas valida o request e chama o service.
    """
    from app.vendas.service import VendaService
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    set_user_id(current_user.id)
    struct_logger.info(
        event="VENDA_CANCELAMENTO_START",
        message="Iniciando cancelamento de venda via service",
        venda_id=venda_id,
        motivo=dados.motivo
    )
    
    # Chamar service (toda lógica de negócio está lá)
    resultado = VendaService.cancelar_venda(
        venda_id=venda_id,
        motivo=dados.motivo,
        user_id=current_user.id,
        tenant_id=tenant_id,
        db=db
    )
    
    struct_logger.info(
        event="VENDA_CANCELADA_SUCESSO",
        message="Cancelamento concluído com sucesso",
        venda_id=venda_id,
        numero_venda=resultado['venda']['numero_venda'],
        itens_estornados=resultado['estornos']['itens_estornados']
    )
    
    # ============================================================================
    # 💾 INVALIDAR CACHE DE OPORTUNIDADES (venda cancelada)
    # ============================================================================
    try:
        from uuid import UUID
        session_id = f"venda_{venda_id}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)),
            session_id=session_id
        )
        processor.cleanup()  # Limpa processador e invalida cache
    except Exception as e:
        logger.debug(f"Cache cleanup (cancelar): {str(e)}")
        pass
    
    return resultado['venda']


@router.post('/{venda_id}/reabrir')
def reabrir_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Reabre uma venda finalizada (muda status para aberta)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    venda = db.query(Venda).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    
    # Impedir reabertura de vendas com NF emitida
    if venda.status == 'pago_nf':
        raise HTTPException(
            status_code=400, 
            detail='Não é possível reabrir uma venda com NF-e emitida. Cancele a nota fiscal primeiro.'
        )
    
    # Permitir reabrir vendas finalizadas ou parcialmente pagas
    if venda.status not in ['finalizada', 'baixa_parcial']:
        raise HTTPException(
            status_code=400, 
            detail='Apenas vendas finalizadas ou com baixa parcial podem ser reabertas'
        )
    
    # Guardar status anterior para log
    status_anterior = venda.status
    
    # ============================================================================
    # 🧹 CANCELAR/REMOVER COMISSÕES EXISTENTES
    # ============================================================================
    comissoes_removidas = 0
    if venda.funcionario_id:
        try:
            from sqlalchemy import text
            
            # Contar comissões antes de remover
            result = db.execute(text("""
                SELECT COUNT(*) FROM comissoes_itens 
                WHERE venda_id = :venda_id
            """), {'venda_id': venda.id})
            comissoes_removidas = result.scalar() or 0
            
            if comissoes_removidas > 0:
                struct_logger.info(
                    event="COMMISSION_CANCEL_START",
                    message=f"Cancelando {comissoes_removidas} comissões por reabertura de venda",
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    count=comissoes_removidas
                )
                
                # Remover comissões
                db.execute(text("""
                    DELETE FROM comissoes_itens WHERE venda_id = :venda_id
                """), {'venda_id': venda.id})
                
                # Também remover provisões de comissão em contas_pagar
                db.execute(text("""
                    DELETE FROM contas_pagar 
                    WHERE descricao LIKE :descricao 
                    AND status = 'pendente'
                """), {'descricao': f'%Comissão - Venda #{venda.id}%'})
                
                struct_logger.info(
                    event="COMMISSION_CANCELLED",
                    message=f"Comissões canceladas com sucesso",
                    venda_id=venda.id,
                    count=comissoes_removidas
                )
            else:
                logger.info(f"ℹ️  Venda #{venda.id} não tinha comissões para cancelar")
                
        except Exception as e:
            logger.error(f"❌ Erro ao cancelar comissões da venda {venda.id}: {e}", exc_info=True)
            struct_logger.error(
                event="COMMISSION_CANCEL_ERROR",
                message=f"Erro ao cancelar comissões: {str(e)}",
                venda_id=venda.id,
                error=str(e)
            )
            # Prosseguir com reabertura mesmo se falhar cancelamento de comissões
    
    # ℹ️  NOTA: NÃO devolvemos estoque ao reabrir!
    # O estoque só é devolvido ao:
    # 1. EDITAR venda e remover produtos
    # 2. EXCLUIR/CANCELAR venda completamente
    # Reabrir serve apenas para alterar forma de pagamento, não mexe em produtos
    
    # Mudar status para aberta
    venda.status = 'aberta'
    venda.data_finalizacao = None
    venda.updated_at = datetime.now()
    
    db.commit()
    db.refresh(venda)
    
    log_action(
        db=db,
        user_id=current_user.id,
        action='update',
        entity_type='vendas',
        entity_id=venda.id,
        details=f'Venda #{venda.id} reaberta (status: {status_anterior} → aberta, comissões canceladas: {comissoes_removidas})'
    )
    
    return venda.to_dict()


@router.patch('/{venda_id}/status')
def atualizar_status_venda(
    venda_id: int,
    status_data: dict,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza apenas o status da venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar a venda
    venda = db.query(Venda).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    
    # Extrair status do body
    novo_status = status_data.get('status')
    if not novo_status:
        raise HTTPException(status_code=400, detail='Status não informado')
    
    status_anterior = venda.status
    venda.status = novo_status
    venda.updated_at = datetime.now()
    
    # 🆕 GERAR COMISSÕES se estiver finalizando a venda (apenas se funcionário/veterinário foi selecionado)
    if novo_status == 'finalizada' and status_anterior != 'finalizada' and venda.funcionario_id:
        try:
            from app.comissoes_service import gerar_comissoes_venda
            from sqlalchemy import text
            
            struct_logger.info(
                event="COMMISSION_START",
                message=f"Gerando comissões via PATCH /status (status: {status_anterior} → {novo_status})",
                venda_id=venda.id,
                funcionario_id=venda.funcionario_id,
                trigger="status_change"
            )
            
            # 🔍 BUSCAR TODOS OS PAGAMENTOS DA VENDA 
            # Precisamos gerar comissões para TODOS os pagamentos que ainda não têm comissão
            todos_pagamentos = db.execute(text("""
                SELECT vp.id, vp.forma_pagamento, vp.valor, vp.data_pagamento
                FROM venda_pagamentos vp
                WHERE vp.venda_id = :venda_id
                ORDER BY vp.data_pagamento ASC
            """), {'venda_id': venda.id}).fetchall()
            
            if not todos_pagamentos:
                logger.info("ℹ️  Nenhum pagamento encontrado na venda")
            else:
                # 🔢 Verificar quais pagamentos já têm comissão
                comissoes_existentes = db.execute(text("""
                    SELECT DISTINCT parcela_numero
                    FROM comissoes_itens
                    WHERE venda_id = :venda_id AND funcionario_id = :funcionario_id
                """), {'venda_id': venda.id, 'funcionario_id': venda.funcionario_id}).fetchall()
                
                parcelas_com_comissao = {row[0] for row in comissoes_existentes}
                logger.info(f"📊 Pagamentos: {len(todos_pagamentos)} total, {len(parcelas_com_comissao)} já com comissão")
                
                # 🔄 GERAR UMA COMISSÃO PARA CADA PAGAMENTO SEM COMISSÃO
                comissoes_geradas = 0
                total_comissoes = Decimal('0')
                
                for idx, pagamento_row in enumerate(todos_pagamentos, start=1):
                    parcela_numero = idx
                    
                    # Pular se já tem comissão
                    if parcela_numero in parcelas_com_comissao:
                        logger.info(f"⏭️  Parcela {parcela_numero} já tem comissão - pulando")
                        continue
                    
                    valor_pagamento = Decimal(str(pagamento_row[2]))
                    forma_pagamento = pagamento_row[1]
                    
                    struct_logger.info(
                        event="COMMISSION_START",
                        message="Gerando comissão para pagamento",
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=float(valor_pagamento),
                        forma_pagamento=forma_pagamento,
                        parcela_numero=parcela_numero
                    )
                    
                    resultado = gerar_comissoes_venda(
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=valor_pagamento,
                        forma_pagamento=forma_pagamento,
                        parcela_numero=parcela_numero,
                        db=db
                    )
                    
                    if resultado and resultado.get('success'):
                        if not resultado.get('duplicated'):
                            comissoes_geradas += 1
                            total_comissoes += Decimal(str(resultado.get('total_comissao', 0)))
                            struct_logger.info(
                                event="COMMISSION_GENERATED",
                                message="Comissão gerada com sucesso",
                                venda_id=venda.id,
                                parcela_numero=parcela_numero,
                                total_comissao=float(resultado.get('total_comissao', 0))
                            )
                
                if comissoes_geradas > 0:
                    logger.info(f"✅ {comissoes_geradas} comissões geradas - Total: R$ {total_comissoes:.2f}")
                else:
                    logger.info("ℹ️  Nenhuma comissão nova gerada (todas já existiam ou sem configuração)")
                
        except Exception as e:
            logger.error(f"❌ Erro ao gerar comissões para venda {venda.id}: {str(e)}", exc_info=True)
            struct_logger.error(
                event="COMMISSION_ERROR",
                message=f"Erro ao gerar comissões: {str(e)}",
                venda_id=venda.id,
                error=str(e),
                trigger="status_change"
            )
            # Não abortar a atualização por erro nas comissões
    
    db.commit()
    db.refresh(venda)
    
    log_action(
        db=db,
        user_id=current_user.id,
        action='update',
        entity_type='vendas',
        entity_id=venda.id,
        details=f'Status da venda #{venda.id} alterado: {status_anterior} → {novo_status}'
    )
    
    return {'success': True, 'status': novo_status}
    
    return {'message': 'Status atualizado com sucesso', 'status': venda.status}


@router.patch('/{venda_id}/pagamento/{pagamento_id}/nsu')
def atualizar_nsu_pagamento(
    venda_id: int,
    pagamento_id: int,
    nsu_data: dict,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza apenas o NSU de um pagamento em cartão.
    Usado pela tela de conciliação para preencher NSU manualmente.
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar a venda
    venda = db.query(Venda).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    
    # Buscar o pagamento
    pagamento = db.query(VendaPagamento).filter_by(
        id=pagamento_id,
        venda_id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not pagamento:
        raise HTTPException(status_code=404, detail='Pagamento não encontrado')
    
    # Extrair NSU do body
    novo_nsu = nsu_data.get('nsu_cartao', '').strip()
    if not novo_nsu:
        raise HTTPException(status_code=400, detail='NSU não informado')
    
    # VALIDAR NSU DUPLICADO (mesma lógica do VendaService)
    if pagamento.operadora_id:
        nsu_duplicado = db.query(VendaPagamento).filter(
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.nsu_cartao == novo_nsu,
            VendaPagamento.operadora_id == pagamento.operadora_id,
            VendaPagamento.id != pagamento_id  # Excluir o próprio pagamento
        ).first()
        
        if nsu_duplicado:
            venda_duplicada = db.query(Venda).filter_by(id=nsu_duplicado.venda_id).first()
            raise HTTPException(
                status_code=400,
                detail=f"❌ NSU DUPLICADO: O NSU '{novo_nsu}' já está vinculado à "
                       f"Venda {venda_duplicada.numero_venda if venda_duplicada else nsu_duplicado.venda_id}. "
                       f"Cada NSU deve ser usado apenas uma vez por operadora."
            )
    
    # Atualizar NSU
    nsu_anterior = pagamento.nsu_cartao
    pagamento.nsu_cartao = novo_nsu
    pagamento.updated_at = datetime.now()
    
    db.commit()
    db.refresh(pagamento)
    
    log_action(
        db=db,
        user_id=current_user.id,
        action='update',
        entity_type='venda_pagamento',
        entity_id=pagamento.id,
        details=f'NSU do pagamento atualizado: {nsu_anterior} → {novo_nsu} (Venda {venda.numero_venda})'
    )
    
    return {
        'success': True,
        'nsu_cartao': novo_nsu,
        'mensagem': f'NSU atualizado para {novo_nsu}'
    }


@router.get('/{venda_id}/pagamentos')
def listar_pagamentos_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todos os pagamentos de uma venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    venda = db.query(Venda).filter_by(
        id=venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    
    pagamentos = db.query(VendaPagamento).filter_by(venda_id=venda.id).order_by(VendaPagamento.data_pagamento).all()
    
    total_pago = sum(float(p.valor) for p in pagamentos)
    valor_restante = float(venda.total) - total_pago
    
    return {
        'venda_id': venda.id,
        'numero_venda': venda.numero_venda,
        'total_venda': float(venda.total),
        'total_pago': total_pago,
        'valor_restante': max(0, valor_restante),
        'status': venda.status,
        'pagamentos': [p.to_dict() for p in pagamentos]
    }


@router.delete('/pagamentos/{pagamento_id}')
def excluir_pagamento(
    pagamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Excluir um pagamento de uma venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # 🔒 SEGURANÇA: Buscar o pagamento validando que a venda pertence ao usuário
    # Primeiro buscamos o pagamento, depois validamos a venda
    pagamento = db.query(VendaPagamento).filter_by(id=pagamento_id).first()
    
    if not pagamento:
        raise HTTPException(status_code=404, detail='Pagamento não encontrado')
    
    # 🔒 SEGURANÇA: Validar que a venda do pagamento pertence ao tenant
    venda = db.query(Venda).filter_by(
        id=pagamento.venda_id,
        tenant_id=tenant_id
    ).first()
    
    if not venda:
        raise HTTPException(status_code=404, detail='Venda não encontrada')
    
    # Impedir exclusão de pagamento em vendas com NF emitida
    if venda.status == 'pago_nf':
        raise HTTPException(
            status_code=400,
            detail='Não é possível excluir pagamentos de uma venda com NF-e emitida. Cancele a nota fiscal primeiro.'
        )
    
    # ⚠️ IMPORTANTE: Se venda está finalizada/baixa_parcial, não pode excluir pagamento
    # Usuário deve REABRIR a venda primeiro!
    if venda.status in ['finalizada', 'baixa_parcial']:
        raise HTTPException(
            status_code=400,
            detail='Não é possível excluir pagamentos de uma venda finalizada. Reabra a venda primeiro através do botão "Reabrir Venda".'
        )
    
    # Registrar auditoria
    try:
        log_action(
            db=db,
            user_id=current_user.id,
            action='delete',
            entity_type='venda_pagamentos',
            entity_id=pagamento.id,
            details=f'Excluído pagamento de R$ {pagamento.valor} ({pagamento.forma_pagamento}) da venda #{venda.id}'
        )
    except Exception as e:
        logger.info(f"⚠️ Erro ao registrar auditoria: {e}")
    
    # Sincronizar exclusão com contas a receber e lançamentos manuais
    try:
        contas = db.query(ContaReceber).filter(ContaReceber.venda_id == venda.id).all()
        
        for conta in contas:
            # Deletar conta a receber
            try:
                db.delete(conta)
                logger.info(f"🗑️ Conta a receber {conta.id} excluída")
            except Exception as e:
                logger.info(f"⚠️ Erro ao deletar conta: {e}")
    except Exception as e:
        logger.info(f"⚠️ Erro ao buscar contas a receber: {e}")
    
    # Excluir o pagamento
    db.delete(pagamento)
    db.flush()  # Garantir que o delete seja processado antes da query
    
    # Recalcular total pago
    pagamentos_restantes = db.query(VendaPagamento).filter_by(venda_id=venda.id).all()
    total_pago = sum(float(p.valor) for p in pagamentos_restantes)
    total_venda = float(venda.total)
    
    logger.info(f"DEBUG excluir_pagamento: total_pago={total_pago}, total_venda={total_venda}")
    
    # Atualizar status da venda
    if total_pago == 0:
        venda.status = 'aberta'
        logger.info(f"DEBUG: Mudou status para ABERTA (total_pago = 0)")
    elif total_pago >= total_venda:
        venda.status = 'finalizada'
        logger.info(f"DEBUG: Mudou status para FINALIZADA (total_pago >= total_venda)")
    else:
        venda.status = 'baixa_parcial'
        logger.info(f"DEBUG: Mudou status para BAIXA_PARCIAL")
    
    db.commit()
    
    return {
        'message': 'Pagamento excluído com sucesso',
        'venda_id': venda.id,
        'novo_status': venda.status,
        'total_pago': total_pago,
        'valor_restante': max(0, total_venda - total_pago)
    }


@router.delete('/{venda_id}')
def excluir_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Excluir uma venda e devolver estoque"""
    from sqlalchemy.exc import IntegrityError
    from app.rotas_entrega_models import RotaEntrega
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    logger.info(f"🗑️  INICIANDO EXCLUSÃO - Venda ID: {venda_id}, User: {current_user.id}, Tenant: {tenant_id}")
    
    try:
        # Buscar a venda
        venda = db.query(Venda).filter_by(
            id=venda_id,
            tenant_id=tenant_id
        ).first()
        
        if not venda:
            logger.warning(f"⚠️  Venda {venda_id} não encontrada para exclusão")
            raise HTTPException(status_code=404, detail='Venda não encontrada')
        
        logger.info(f"✅ Venda encontrada: #{venda.numero_venda}, Status: {venda.status}")
        
        # Verificar se a venda tem NF emitida
        if venda.status == 'pago_nf':
            logger.warning(f"🚫 Venda {venda_id} tem NF-e emitida, bloqueando exclusão")
            raise HTTPException(
                status_code=400,
                detail='Não é possível excluir uma venda com NF-e emitida. Cancele a nota fiscal primeiro.'
            )
        
        # Verificar se a venda está finalizada
        if venda.status == 'finalizada':
            logger.warning(f"🚫 Venda {venda_id} está finalizada, bloqueando exclusão")
            raise HTTPException(
                status_code=400, 
                detail='Não é possível excluir uma venda finalizada. Estorne os pagamentos primeiro.'
            )
        
        # ✅ NOVO: Verificar se a venda está vinculada a uma rota de entrega
        rota_vinculada = db.query(RotaEntrega).filter_by(venda_id=venda_id).first()
        if rota_vinculada:
            passos_resolucao = [
                f"1. Acesse a rota de entrega #{rota_vinculada.id}",
                "2. Remova esta venda da rota",
                "3. Tente excluir a venda novamente"
            ]
            raise HTTPException(
                status_code=400,
                detail={
                    'erro': 'Venda vinculada a uma rota de entrega',
                    'mensagem': f'Esta venda está associada à Rota #{rota_vinculada.id} (Status: {rota_vinculada.status})',
                    'solucao': 'Para excluir esta venda, primeiro remova-a da rota de entrega.',
                    'passos': passos_resolucao,
                    'rota_id': rota_vinculada.id,
                    'rota_status': rota_vinculada.status
                }
            )
        
        # 💾 GUARDAR itens para estorno DEPOIS de deletar (evita conflito)
        itens = db.query(VendaItem).filter_by(venda_id=venda_id).all()
        itens_para_estorno = [(item.produto_id, float(item.quantidade), item.tipo) for item in itens if item.produto_id]
        numero_venda = venda.numero_venda  # Guardar número antes de deletar
        logger.info(f"🔍 EXCLUIR VENDA: Armazenando {len(itens_para_estorno)} itens para estorno posterior")
        logger.info(f"📝 Auditoria: Venda #{venda.id} ({numero_venda}) será excluída - Total: R$ {venda.total} - {len(itens)} itens")
        
        # 💰 IMPORTANTE: Excluir movimentações de caixa relacionadas
        from app.caixa_models import MovimentacaoCaixa
        movimentacoes = db.query(MovimentacaoCaixa).filter_by(venda_id=venda_id).all()
        for mov in movimentacoes:
            logger.info(f"🗑️ Removendo movimentação de caixa: R$ {mov.valor} ({mov.tipo})")
            db.delete(mov)
        
        # 🚚 IMPORTANTE: Excluir paradas de entrega relacionadas e reverter status da venda
        from app.rotas_entrega_models import RotaEntregaParada
        paradas = db.query(RotaEntregaParada).filter_by(venda_id=venda_id).all()
        for parada in paradas:
            logger.info(f"🚚 Removendo parada de entrega da rota #{parada.rota_id}")
            db.delete(parada)
        
        # Reverter status de entrega para None (venda excluída não precisa de entrega)
        venda.status_entrega = None
        
        # 🏦 ESTORNAR MOVIMENTAÇÕES BANCÁRIAS
        from app.financeiro_models import MovimentacaoFinanceira, ContaBancaria, LancamentoManual
        
        movimentacoes_bancarias = db.query(MovimentacaoFinanceira).filter(
            MovimentacaoFinanceira.origem_tipo == 'venda',
            MovimentacaoFinanceira.origem_id == venda_id
        ).all()
        for mov_banc in movimentacoes_bancarias:
            # 🔒 SEGURANÇA: Validar que a conta bancária pertence ao usuário
            conta_bancaria = get_by_id_user(
                db=db,
                model=ContaBancaria,
                entity_id=mov_banc.conta_bancaria_id,
                user_id=current_user.id,
                error_message="Conta bancária não encontrada"
            )
            if conta_bancaria:
                if mov_banc.tipo == 'receita':
                    conta_bancaria.saldo_atual -= mov_banc.valor
                    logger.info(f"🏦 Estornando saldo bancário: {conta_bancaria.nome} -R$ {mov_banc.valor}")
                elif mov_banc.tipo == 'despesa':
                    conta_bancaria.saldo_atual += mov_banc.valor
                    logger.info(f"🏦 Estornando saldo bancário: {conta_bancaria.nome} +R$ {mov_banc.valor}")
            
            db.delete(mov_banc)
        
        # 📊 CANCELAR LANÇAMENTOS MANUAIS (Fluxo de Caixa)
        # Buscar por documento VENDA-{id} ou por venda vinculada
        lancamentos = db.query(LancamentoManual).filter(
            or_(
                LancamentoManual.documento == f"VENDA-{venda_id}",
                LancamentoManual.documento.like(f"VENDA-{venda_id}-%")
            )
        ).all()
        
        for lanc in lancamentos:
            if lanc.status == 'previsto':
                # Apenas remover se ainda não foi realizado
                logger.info(f"📊 Removendo lançamento previsto: {lanc.descricao} - R$ {lanc.valor}")
                db.delete(lanc)
            elif lanc.status == 'realizado':
                # Marcar como cancelado (manter histórico)
                lanc.status = 'cancelado'
                logger.info(f"📊 Cancelando lançamento realizado: {lanc.descricao} - R$ {lanc.valor}")
        
        # Excluir pagamentos (se houver)
        db.query(VendaPagamento).filter_by(venda_id=venda_id).delete()
        
        # Excluir/Cancelar contas a receber vinculadas
        contas_receber = db.query(ContaReceber).filter_by(venda_id=venda_id).all()
        for conta in contas_receber:
            if conta.status == 'pendente' or conta.status == 'parcial':
                # Pode excluir contas pendentes
                logger.info(f"💳 Removendo conta a receber: {conta.descricao} - R$ {conta.valor_original}")
                db.delete(conta)
            elif conta.status == 'recebido':
                # Marcar como cancelada (manter histórico)
                conta.status = 'cancelado'
                logger.info(f"💳 Cancelando conta já recebida: {conta.descricao} - R$ {conta.valor_recebido}")
        
        # Excluir itens
        db.query(VendaItem).filter_by(venda_id=venda_id).delete()
        
        # Excluir venda
        logger.info(f"🗑️  DELETANDO venda do banco: ID={venda_id}, Numero={venda.numero_venda}")
        db.delete(venda)
        
        # ✅ AGORA SIM: Estornar estoque DEPOIS de deletar dados da venda (evita conflito de ordem)
        logger.info(f"📦 INICIANDO ESTORNO DE ESTOQUE: {len(itens_para_estorno)} itens")
        for produto_id, quantidade, tipo in itens_para_estorno:
            logger.info(f"  → Produto: {produto_id}, Qtd: {quantidade}, Tipo: {tipo}")
            try:
                logger.info(f"📦 Estornando estoque: Produto {produto_id} +{quantidade}")
                resultado_estorno = EstoqueService.estornar_estoque(
                    produto_id=produto_id,
                    quantidade=quantidade,
                    motivo='cancelamento',
                    referencia_id=venda_id,
                    referencia_tipo='venda_excluida',
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                    db=db,
                    documento=numero_venda,
                    observacao=f'Venda {numero_venda} excluída'
                )
                logger.info(f"✅ Estoque estornado com sucesso: {resultado_estorno}")
                logger.info(f"🔍 DEBUG: Movimentação ID={resultado_estorno.get('movimentacao_id')}, Estoque: {resultado_estorno.get('estoque_anterior')} → {resultado_estorno.get('estoque_novo')}")
                logger.info(f"📝 Auditoria: Estorno de estoque (+{quantidade}) - Venda {numero_venda} excluída")
                
            except ValueError as e:
                logger.error(f"Erro ao estornar estoque: {e}")
        
        # 🔍 DEBUG: Verificar movimentações pendentes antes do commit
        pending_movs = [obj for obj in db.new if obj.__class__.__name__ == 'EstoqueMovimentacao']
        logger.info(f"🔍 DEBUG: Movimentações pendentes ANTES do commit: {len(pending_movs)}")
        for mov in pending_movs:
            logger.info(f"  → Mov ID={mov.id}, tipo={mov.tipo}, produto_id={mov.produto_id}, qtd={mov.quantidade}")
        
        # Commit da transação
        logger.info(f"💾 EXECUTANDO COMMIT...")
        db.commit()
        logger.info(f"✅ COMMIT CONCLUÍDO!")
        logger.info(f"✅ ✅ VENDA EXCLUÍDA COM SUCESSO: ID={venda_id}")
        
        return {
            'message': 'Venda excluída com sucesso',
            'itens_devolvidos': len(itens)
        }
    
    except IntegrityError as e:
        # ✅ Tratamento amigável para erros de integridade referencial
        db.rollback()
        logger.error(f"❌ IntegrityError ao excluir venda: {e}")
        
        erro_msg = str(e.orig)
        
        # Identificar tipo de violação
        if 'rotas_entrega' in erro_msg:
            raise HTTPException(
                status_code=400,
                detail={
                    'erro': 'Venda vinculada a uma rota de entrega',
                    'mensagem': 'Esta venda ainda está associada a uma ou mais rotas de entrega.',
                    'solucao': 'Remova a venda da rota de entrega antes de excluí-la.',
                    'passos': [
                        '1. Acesse o menu de Rotas de Entrega',
                        '2. Encontre a rota que contém esta venda',
                        '3. Remova a venda da rota',
                        '4. Tente excluir a venda novamente'
                    ],
                    'detalhes_tecnicos': erro_msg if current_user.is_admin else None
                }
            )
        elif 'contas_receber' in erro_msg:
            raise HTTPException(
                status_code=400,
                detail={
                    'erro': 'Venda possui contas a receber vinculadas',
                    'mensagem': 'Esta venda possui contas a receber que precisam ser tratadas.',
                    'solucao': 'Cancele ou exclua as contas a receber vinculadas antes de excluir a venda.',
                    'passos': [
                        '1. Acesse Financeiro > Contas a Receber',
                        '2. Filtre pela venda',
                        '3. Cancele ou exclua as contas pendentes',
                        '4. Tente excluir a venda novamente'
                    ],
                    'detalhes_tecnicos': erro_msg if current_user.is_admin else None
                }
            )
        else:
            # Erro genérico de integridade
            raise HTTPException(
                status_code=400,
                detail={
                    'erro': 'Não é possível excluir esta venda',
                    'mensagem': 'Esta venda está vinculada a outros registros no sistema.',
                    'solucao': 'Remova ou cancele os vínculos antes de excluir a venda.',
                    'passos': [
                        '1. Verifique se existem rotas de entrega vinculadas',
                        '2. Verifique contas a receber pendentes',
                        '3. Entre em contato com o suporte se o problema persistir'
                    ],
                    'detalhes_tecnicos': erro_msg if current_user.is_admin else None
                }
            )
    
    except Exception as e:
        # ❌ Capturar QUALQUER outra exceção que possa estar causando rollback
        db.rollback()
        logger.error(f"❌ ERRO INESPERADO ao excluir venda {venda_id}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f'Erro inesperado ao excluir venda: {str(e)}'
        )


@router.post('/{venda_id}/devolucao')
def registrar_devolucao(
    venda_id: int,
    dados: dict,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Registrar devolução de itens de uma venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 INICIANDO DEVOLUÇÃO - Venda #{venda_id}")
        logger.info(f"{'='*80}")
        logger.info(f"📦 Dados recebidos: {dados}")
        logger.info(f"👤 Usuário: {current_user.nome} (ID: {current_user.id})")
        logger.info(f"🏪 Tenant ID: {tenant_id}")
        
        # Buscar a venda
        venda = db.query(Venda).filter_by(
            id=venda_id,
            tenant_id=tenant_id
        ).first()
        
        if not venda:
            logger.info(f"❌ Venda #{venda_id} não encontrada")
            raise HTTPException(status_code=404, detail='Venda não encontrada')
        
        logger.info(f"✅ Venda encontrada: #{venda.numero_venda} - Total: R$ {venda.total}")
        
        caixa_id = dados.get('caixa_id')
        itens_devolucao = dados.get('itens', [])
        motivo = dados.get('motivo', '')
        gerar_credito = dados.get('gerar_credito', False)  # 🆕 Nova opção
        
        logger.info(f"💰 Modo: {'CRÉDITO ao cliente' if gerar_credito else 'DINHEIRO'}")
        logger.info(f"📝 Motivo: {motivo}")
        logger.info(f"📦 Itens para devolução: {len(itens_devolucao)}")
        
        if not caixa_id and not gerar_credito:
            logger.info(f"❌ Caixa ID não fornecido para devolução em dinheiro")
            raise HTTPException(status_code=400, detail='ID do caixa é obrigatório para devolução em dinheiro')
        
        if not itens_devolucao:
            logger.info(f"❌ Nenhum item selecionado")
            raise HTTPException(status_code=400, detail='Nenhum item selecionado para devolução')
        
        if not motivo:
            logger.info(f"❌ Motivo não fornecido")
            raise HTTPException(status_code=400, detail='Motivo da devolução é obrigatório')
        
        # Verificar se o caixa existe e está aberto (apenas se for devolução em dinheiro)
        from app.caixa_models import Caixa, MovimentacaoCaixa
        caixa = None
        if not gerar_credito:
            caixa = db.query(Caixa).filter_by(id=caixa_id, status='aberto').first()
            
            if not caixa:
                raise HTTPException(status_code=400, detail='Caixa não encontrado ou não está aberto')
        
        valor_total_devolucao = 0
        itens_devolvidos = []
        
        # Processar cada item devolvido
        for item_dev in itens_devolucao:
            # 🆕 Verificar se é componente de KIT
            is_componente_kit = item_dev.get('is_componente_kit', False)
            
            if is_componente_kit:
                # 🔥 DEVOLUÇÃO DE COMPONENTE DE KIT
                produto_id = item_dev.get('produto_id')
                quantidade_devolvida = float(item_dev.get('quantidade', 0))
                preco_unitario_componente = float(item_dev.get('preco_unitario', 0))
                kit_item_id = item_dev.get('kit_item_id')
                
                if quantidade_devolvida <= 0:
                    continue
                
                logger.info(f"📦 Devolvendo componente do KIT - Produto ID: {produto_id}, Quantidade: {quantidade_devolvida}")
                
                # Devolver componente ao estoque
                try:
                    resultado_estorno = EstoqueService.estornar_estoque(
                        produto_id=produto_id,
                        quantidade=quantidade_devolvida,
                        motivo='devolucao',
                        referencia_id=venda_id,
                        referencia_tipo='venda',
                        user_id=current_user.id,
                        tenant_id=tenant_id,
                        db=db,
                        documento=None,
                        observacao=f"{motivo} - Componente de KIT (Item #{kit_item_id})"
                    )
                    
                    # Buscar nome do produto
                    from app.produtos_models import Produto
                    produto = db.query(Produto).filter_by(id=produto_id).first()
                    produto_nome = produto.nome if produto else f"Produto #{produto_id}"
                    
                    logger.info(f"  ✅ Componente estornado: {produto_nome} +{quantidade_devolvida}")
                    
                    # Registrar auditoria
                    log_action(
                        db=db,
                        user_id=current_user.id,
                        action='update',
                        entity_type='produtos',
                        entity_id=produto_id,
                        details=f'Devolução de componente de KIT (+{quantidade_devolvida}) - Venda #{venda_id} - Motivo: {motivo}'
                    )
                except ValueError as e:
                    logger.error(f"Erro ao devolver componente de KIT: {e}")
                
                # Calcular valor devolvido do componente
                valor_componente = Decimal(str(preco_unitario_componente)) * Decimal(str(quantidade_devolvida))
                valor_total_devolucao += valor_componente
                
                itens_devolvidos.append({
                    'produto_id': produto_id,
                    'produto_nome': produto_nome,
                    'quantidade': quantidade_devolvida,
                    'valor_unitario': preco_unitario_componente,
                    'valor_total': valor_componente,
                    'tipo': 'componente_kit'
                })
                
            else:
                # 🔹 DEVOLUÇÃO NORMAL (Item inteiro - pode ser KIT inteiro ou produto simples)
                item_id = item_dev.get('item_id')
                quantidade_devolvida = float(item_dev.get('quantidade', 0))
                
                if quantidade_devolvida <= 0:
                    continue
                
                # Buscar o item da venda
                item_venda = db.query(VendaItem).filter_by(id=item_id, venda_id=venda_id).first()
                
                if not item_venda:
                    raise HTTPException(status_code=404, detail=f'Item {item_id} não encontrado na venda')
                
                if quantidade_devolvida > item_venda.quantidade:
                    raise HTTPException(
                        status_code=400,
                        detail=f'Quantidade devolvida ({quantidade_devolvida}) maior que quantidade vendida ({item_venda.quantidade})'
                    )
                
                # Devolver ao estoque
                if item_venda.produto_id:
                    try:
                        resultado_estorno = EstoqueService.estornar_estoque(
                            produto_id=item_venda.produto_id,
                            quantidade=quantidade_devolvida,
                            motivo='devolucao',
                            referencia_id=venda_id,
                            referencia_tipo='venda',
                            user_id=current_user.id,
                            tenant_id=tenant_id,
                            db=db,
                            documento=None,
                            observacao=motivo
                        )
                        # Registrar auditoria
                        log_action(
                            db=db,
                            user_id=current_user.id,
                            action='update',
                            entity_type='produtos',
                            entity_id=item_venda.produto_id,
                            details=f'Devolução de estoque (+{quantidade_devolvida}) - Venda #{venda_id} - Motivo: {motivo}'
                        )
                    except ValueError as e:
                        logger.error(f"Erro ao devolver estoque: {e}")
                
                # Calcular valor devolvido
                valor_item = item_venda.preco_unitario * Decimal(str(quantidade_devolvida))
                valor_total_devolucao += valor_item
                
                itens_devolvidos.append({
                    'produto_id': item_venda.produto_id,
                    'produto_nome': item_venda.produto.nome if item_venda.produto else item_venda.servico_descricao,
                    'quantidade': quantidade_devolvida,
                    'valor_unitario': item_venda.preco_unitario,
                    'valor_total': valor_item,
                    'tipo': 'item_normal'
                })
        
        # 💰 OPÇÃO 1: GERAR CRÉDITO PARA O CLIENTE
        if gerar_credito:
            if not venda.cliente_id:
                raise HTTPException(
                    status_code=400,
                    detail='Não é possível gerar crédito para venda sem cliente cadastrado'
                )
            
            # 🔒 SEGURANÇA: Validar que o cliente pertence ao usuário
            from app.models import Cliente
            cliente = safe_get_cliente(db, venda.cliente_id, current_user.id)
            
            # Adicionar crédito ao cliente
            cliente.credito = (cliente.credito or Decimal('0')) + Decimal(str(valor_total_devolucao))
            logger.info(f"💰 Crédito adicionado ao cliente {cliente.nome}: +R$ {valor_total_devolucao:.2f} (Total: R$ {cliente.credito:.2f})")
            
            # Não cria MovimentacaoCaixa nem LancamentoManual (apenas crédito)
            
        # 💵 OPÇÃO 2: DEVOLUÇÃO EM DINHEIRO
        else:
            # Verificar se o caixa existe e está aberto
            from app.caixa_models import Caixa
            caixa = db.query(Caixa).filter_by(id=caixa_id, status='aberto').first()
            
            if not caixa:
                raise HTTPException(status_code=400, detail='Caixa não encontrado ou não está aberto')
            
            # Registrar devolução no caixa usando o service
            movimentacao = CaixaService.registrar_devolucao(
                caixa_id=caixa_id,
                venda_id=venda_id,
                venda_numero=venda.numero_venda,
                valor=valor_total_devolucao,
                motivo=motivo,
                user_id=current_user.id,
                user_nome=current_user.nome,
                tenant_id=tenant_id,  # 🔒 Isolamento multi-tenant
                db=db
            )
            
            # Criar lançamento manual de saída (estorno no fluxo de caixa)
            from app.financeiro_models import LancamentoManual, CategoriaFinanceira
            
            categoria_devolucoes = db.query(CategoriaFinanceira).filter(
                CategoriaFinanceira.nome.ilike('%devolução%'),
                CategoriaFinanceira.tipo == 'despesa',
                CategoriaFinanceira.tenant_id == tenant_id
            ).first()
            
            if not categoria_devolucoes:
                categoria_devolucoes = CategoriaFinanceira(
                    nome="Devoluções de Vendas",
                    tipo="despesa",
                    user_id=current_user.id,
                    tenant_id=tenant_id
                )
                db.add(categoria_devolucoes)
                db.flush()
            
            lancamento_devolucao = LancamentoManual(
                tipo='saida',
                valor=Decimal(str(valor_total_devolucao)),
                descricao=f"Devolução venda {venda.numero_venda} - {motivo}",
                data_lancamento=date.today(),
                status='realizado',
                categoria_id=categoria_devolucoes.id,
                documento=f"DEVOLUCAO-{venda_id}",
                fornecedor_cliente=venda.cliente.nome if venda.cliente else "Cliente Avulso",
                user_id=current_user.id,
                tenant_id=tenant_id
            )
            db.add(lancamento_devolucao)
            logger.info(f"📊 Lançamento de devolução criado: R$ {valor_total_devolucao:.2f}")
        
        # 🆕 AJUSTAR CONTAS A RECEBER (sempre, independente de crédito ou dinheiro)
        from app.financeiro_models import ContaReceber, LancamentoManual, CategoriaFinanceira
        
        contas_receber = db.query(ContaReceber).filter_by(venda_id=venda_id).all()
        if contas_receber:
            # Reduzir proporcionalmente o valor das contas pendentes ou estornar pagas
            for conta in contas_receber:
                if conta.status in ['pendente', 'parcial']:
                    proporcao = float(valor_total_devolucao) / float(venda.total)
                    reducao = float(conta.valor_original) * proporcao
                    
                    conta.valor_original -= Decimal(str(reducao))
                    conta.valor_final -= Decimal(str(reducao))
                    
                    # Se ficou zerada, marcar como cancelada
                    if conta.valor_final <= 0:
                        conta.status = 'cancelada'
                    
                    logger.info(f"💳 Ajustando ContaReceber #{conta.id}: -R$ {reducao:.2f}")
                elif conta.status == 'pago':
                    # Cancelar a conta paga (estorno)
                    conta.status = 'estornada'
                    logger.info(f"💳 Estornando ContaReceber #{conta.id} (paga)")
        
        # 🆕 ESTORNAR LANÇAMENTOS MANUAIS REALIZADOS (Fluxo de Caixa)
        lancamentos = db.query(LancamentoManual).filter(
            LancamentoManual.documento == f"VENDA-{venda_id}",
            LancamentoManual.status == 'realizado'
        ).all()
        
        if lancamentos:
            # Buscar ou criar categoria de devoluções
            categoria_devolucoes = db.query(CategoriaFinanceira).filter(
                CategoriaFinanceira.nome.ilike('%devolução%'),
                CategoriaFinanceira.tipo == 'despesa',
                CategoriaFinanceira.user_id == current_user.id,
                CategoriaFinanceira.tenant_id == tenant_id
            ).first()
            
            if not categoria_devolucoes:
                categoria_devolucoes = CategoriaFinanceira(
                    nome="Devoluções de Vendas",
                    tipo="despesa",
                    user_id=current_user.id,
                    tenant_id=tenant_id
                )
                db.add(categoria_devolucoes)
                db.flush()
            
            for lanc in lancamentos:
                proporcao = float(valor_total_devolucao) / float(venda.total)
                estorno = float(lanc.valor) * proporcao
                
                # Criar lançamento de estorno (saída)
                estorno_lanc = LancamentoManual(
                    tipo='saida',
                    valor=Decimal(str(estorno)),
                    descricao=f"Estorno devolução venda {venda.numero_venda} - {motivo}",
                    data_lancamento=date.today(),
                    status='realizado',
                    categoria_id=categoria_devolucoes.id,
                    documento=f"ESTORNO-VENDA-{venda_id}",
                    fornecedor_cliente=venda.cliente.nome if venda.cliente else "Cliente Avulso",
                    user_id=current_user.id,
                    tenant_id=tenant_id
                )
                db.add(estorno_lanc)
                logger.info(f"💸 Estorno criado no LancamentoManual: -R$ {estorno:.2f}")
        
        # 🆕 ATUALIZAR STATUS DA VENDA
        if float(valor_total_devolucao) >= float(venda.total) * 0.99:  # 99% devolvido = total
            venda.status = 'finalizada_devolucao_total'
        else:
            venda.status = 'finalizada_devolucao_parcial'
        
        # 📝 GERAR HISTÓRICO DE DEVOLUÇÃO NA OBSERVAÇÃO
        from datetime import datetime
        
        # Determinar tipo de devolução
        if float(valor_total_devolucao) >= float(venda.total) * 0.99:
            tipo_desc = "Devolução total"
        else:
            # Verificar se tem componentes de KIT
            tem_componentes = any(item.get('tipo') == 'componente_kit' for item in itens_devolvidos)
            if tem_componentes:
                tipo_desc = "Devolução parcial por componentes de KIT"
            else:
                tipo_desc = "Devolução parcial"
        
        # Montar histórico
        historico = f"\n\n{'='*60}\n"
        historico += f"[DEVOLUÇÃO | {datetime.now().strftime('%d/%m/%Y %H:%M')}]\n"
        historico += f"Usuário: {current_user.nome}\n"
        historico += f"Tipo: {tipo_desc}\n"
        
        # Agrupar itens por tipo
        itens_kit = [i for i in itens_devolvidos if i.get('tipo') == 'componente_kit']
        itens_normais = [i for i in itens_devolvidos if i.get('tipo') != 'componente_kit']
        
        # Listar itens normais
        if itens_normais:
            historico += "Itens devolvidos:\n"
            for item in itens_normais:
                historico += f"  • {item['produto_nome']} → {item['quantidade']} un (R$ {float(item['valor_total']):.2f})\n"
        
        # Listar componentes de KIT
        if itens_kit:
            historico += "Componentes de KIT devolvidos:\n"
            for item in itens_kit:
                historico += f"  • {item['produto_nome']} → {item['quantidade']} un (R$ {float(item['valor_total']):.2f})\n"
        
        historico += f"Motivo: {motivo}\n"
        historico += "Forma de estorno:\n"
        
        if gerar_credito:
            historico += f"  • Crédito em cliente → R$ {float(valor_total_devolucao):.2f}\n"
        else:
            historico += f"  • Dinheiro (Caixa) → R$ {float(valor_total_devolucao):.2f}\n"
        
        historico += f"Valor total estornado: R$ {float(valor_total_devolucao):.2f}\n"
        historico += f"{'='*60}"
        
        # Anexar histórico à observação (APPEND, nunca sobrescrever)
        if venda.observacoes:
            venda.observacoes = venda.observacoes + historico
        else:
            venda.observacoes = historico.lstrip()
        
        logger.info(f"📝 Histórico de devolução adicionado às observações da venda")
        
        # Registrar auditoria da devolução
        tipo_devolucao = "Crédito ao cliente" if gerar_credito else "Dinheiro"
        log_action(
            db=db,
            user_id=current_user.id,
            action='devolucao',
            entity_type='vendas',
            entity_id=venda_id,
            details=f'Devolução registrada ({tipo_devolucao}) - Venda #{venda_id} - R$ {valor_total_devolucao:.2f} - Motivo: {motivo}'
        )
        
        db.commit()
        
        resultado = {
            'message': 'Devolução registrada com sucesso',
            'venda_id': venda_id,
            'valor_total_devolucao': float(valor_total_devolucao),
            'tipo_devolucao': tipo_devolucao,
            'status_venda': venda.status,
            'itens_devolvidos': itens_devolvidos
        }
        
        if gerar_credito:
            from app.models import Cliente
            # 🔒 SEGURANÇA: Validar que o cliente pertence ao usuário
            cliente = safe_get_cliente(db, venda.cliente_id, current_user.id)
            resultado['credito_cliente'] = float(cliente.credito)
            resultado['cliente_nome'] = cliente.nome
        else:
            resultado['movimentacao_caixa_id'] = movimentacao.id
        
        logger.info(f"✅ Devolução concluída com sucesso!")
        logger.info(f"{'='*80}\n")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"\n{'='*80}")
        logger.info(f"🚨 ERRO CRÍTICO NA DEVOLUÇÃO:")
        logger.info(f"{'='*80}")
        logger.info(f"Tipo: {type(e).__name__}")
        logger.info(f"Mensagem: {str(e)}")
        import traceback
        logger.info(f"Traceback completo:")
        traceback.print_exc()
        logger.info(f"{'='*80}\n")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar devolução: {str(e)}")


# ============================================================================
# ENDPOINTS - RELATÓRIOS
# ============================================================================

@router.get('/relatorios/resumo')
def relatorio_resumo(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Relatório resumo de vendas"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(Venda).filter_by(tenant_id=tenant_id)
    
    if data_inicio:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0)
        query = query.filter(Venda.data_venda >= data_inicio_dt)
    
    if data_fim:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(Venda.data_venda <= data_fim_dt)
    
    vendas = query.all()
    
    # Calcular resumo
    total_vendas = len(vendas)
    total_valor = sum(float(v.total) for v in vendas if v.status != 'cancelada')
    total_canceladas = sum(1 for v in vendas if v.status == 'cancelada')
    
    # Por forma de pagamento
    pagamentos_resumo = {}
    for venda in vendas:
        if venda.status != 'cancelada':
            for pag in venda.pagamentos:
                forma = pag.forma_pagamento
                if forma not in pagamentos_resumo:
                    pagamentos_resumo[forma] = 0
                pagamentos_resumo[forma] += float(pag.valor)
    
    return {
        'total_vendas': total_vendas,
        'total_valor': total_valor,
        'total_canceladas': total_canceladas,
        'pagamentos_resumo': pagamentos_resumo,
        'periodo': {
            'inicio': data_inicio if data_inicio else None,
            'fim': data_fim if data_fim else None
        }
    }
