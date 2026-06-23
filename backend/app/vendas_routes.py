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

# ruff: noqa: F401

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, desc
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import json

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .idempotency import idempotent  # ← IDEMPOTÊNCIA
from .security.permissions_decorator import require_permission
from .vendas_models import Venda, VendaItem
from .models import Cliente
from .produtos_models import Produto
from .audit_log import log_action
from .utils.logger import logger as struct_logger, set_user_id
from .estoque.service import EstoqueService
from .utils.security_helpers import safe_get_produto
from .services.opportunity_background_processor import get_opportunity_processor
from .services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
    invalidate_venda_rentabilidade_snapshot,
)
from .services.order_push_notifications import notify_sale_order_event
from .vendas.comissoes import (
    _contar_comissoes_venda,
    _gerar_comissoes_pendentes_venda,
    _listar_pagamentos_venda_para_comissao,
    _parcelas_com_comissao_funcionario,
    _remover_comissoes_venda,
    _total_pago_venda,
)
from .vendas.regras import _resolver_status_entrega_atualizacao, calcular_totais_venda
from .vendas.schemas import (
    CancelarVendaRequest,
    CriarVendaRequest,
    ExcluirVendaRequest,
    FinalizarVendaRequest,
    MarcarEntregueRequest,
    VendaItemSchema,
    VendaPagamentoSchema,
)

from .vendas.routes_common import (
    _normalizar_motivo_exclusao_venda,
    _obter_cliente_ou_404,
    _obter_venda_ou_404,
    _remover_provisoes_comissao_venda,
    _validar_tenant_e_obter_usuario,
)
from .vendas.pagamentos_routes import (
    atualizar_nsu_pagamento,
    excluir_pagamento,
    listar_pagamentos_venda,
    router as pagamentos_router,
)
from .vendas.devolucoes_routes import (
    registrar_devolucao,
    router as devolucoes_router,
)

router = APIRouter(prefix="/vendas", tags=["vendas"])
router.include_router(pagamentos_router)
router.include_router(devolucoes_router)

# Configurar logger tradicional (manter compatibilidade)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# HELPERS DE ROTA REEXPORTADOS PARA COMPATIBILIDADE
# ============================================================================
# Implementacoes movidas para app.vendas.routes_common.


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

# ============================================================================
# ENDPOINTS - CONFIGURAÇÕES DE ENTREGA [DEPRECATED]
# ============================================================================
# [DEPRECATED - Sprint 1 BLOCO 3] Endpoints movidos para app/api/endpoints/configuracoes_entrega.py
# Nova estrutura: tenant_id (UUID), entregador_padrao_id (Integer), ponto_inicial_rota
# Antiga estrutura (user_id, valor_por_km, taxa_minima) não é mais usada


# ============================================================================
# ENDPOINTS - VENDAS CRUD
# ============================================================================


@router.get("")
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
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista as vendas com filtros - OTIMIZADO com eager loading"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    try:
        # EAGER LOADING: Carregar todas as relações de uma vez (evita N+1 queries)
        query = (
            db.query(Venda)
            .options(
                joinedload(Venda.cliente),  # Cliente da venda
                joinedload(Venda.pagamentos),  # Pagamentos da venda
                joinedload(Venda.itens).joinedload(
                    VendaItem.produto
                ),  # Itens + Produtos
            )
            .filter_by(tenant_id=tenant_id)
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
        subquery = (
            db.query(RotaEntrega.venda_id)
            .filter(RotaEntrega.tenant_id == tenant_id)
            .subquery()
        )
        query = query.filter(~Venda.id.in_(subquery))

    if data_inicio:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
        data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0)
        query = query.filter(Venda.data_venda >= data_inicio_dt)

    if data_fim:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(Venda.data_venda <= data_fim_dt)

    if busca:
        try:
            # Buscar por número da venda, observações OU nome do cliente
            # SQLite: usar LIKE com lower() para case-insensitive
            busca_lower = f"%{busca.lower()}%"
            query = query.outerjoin(Cliente, Venda.cliente_id == Cliente.id).filter(
                or_(
                    Venda.numero_venda.contains(busca),
                    func.lower(Cliente.nome).like(busca_lower),
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
        "vendas": [v.to_dict() for v in vendas],
        "total": total,
        "pages": (total + per_page - 1) // per_page,
        "current_page": page,
    }


@router.get("/{venda_id}")
def buscar_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Busca uma venda específica"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    venda = (
        db.query(Venda)
        .options(joinedload(Venda.itens).joinedload(VendaItem.produto))
        .filter_by(id=venda_id, tenant_id=tenant_id)
        .first()
    )

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # 🐛 DEBUG: Log dos valores de entrega
    logger.info(
        f"🔍 GET venda/{venda_id}: percentual_loja={venda.percentual_taxa_loja}, "
        f"percentual_entregador={venda.percentual_taxa_entregador}, "
        f"valor_loja={venda.valor_taxa_loja}, valor_entregador={venda.valor_taxa_entregador}"
    )

    return venda.to_dict()


@router.post("")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita criação duplicada de vendas
@require_permission("vendas.criar")
async def criar_venda(
    dados: CriarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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
            produto = (
                db.query(Produto)
                .filter(Produto.id == item.produto_id, Produto.tenant_id == tenant_id)
                .first()
            )

            if produto and produto.is_parent:
                raise HTTPException(
                    status_code=400,
                    detail=f"❌ Produto '{produto.nome}' possui variações e não pode ser vendido diretamente. Selecione uma variação específica (cor, tamanho, etc.) para adicionar ao carrinho.",
                )

    # ========================================
    # 🔒 TRAVA 2 — VALIDAÇÃO: ENDEREÇO OBRIGATÓRIO QUANDO TEM ENTREGA
    # ========================================
    if dados.tem_entrega and not dados.endereco_entrega:
        raise HTTPException(
            status_code=400,
            detail="❌ Endereço de entrega é obrigatório quando a venda tem entrega. Selecione o endereço do cliente ou digite um novo.",
        )

    # ========================================
    # 🔒 TRAVA 3 — VALIDAÇÃO: ENTREGADOR OBRIGATÓRIO QUANDO TEM ENTREGA
    # ========================================
    if dados.tem_entrega and not dados.entregador_id:
        raise HTTPException(
            status_code=400,
            detail="❌ Entregador é obrigatório quando a venda tem entrega. Selecione um entregador antes de salvar.",
        )

    # Preparar payload para o service
    payload = {
        "cliente_id": dados.cliente_id,
        "vendedor_id": dados.vendedor_id,
        "funcionario_id": dados.funcionario_id,
        "itens": [item.dict() for item in dados.itens],
        "desconto_valor": dados.desconto_valor,
        "desconto_percentual": dados.desconto_percentual,
        "cupom_code": dados.cupom_code.strip().upper() if dados.cupom_code else None,
        "cupom_discount_applied": dados.cupom_discount_applied,
        "observacoes": dados.observacoes,
        "tem_entrega": dados.tem_entrega,
        "taxa_entrega": dados.taxa_entrega,
        "percentual_taxa_loja": dados.percentual_taxa_loja,
        "percentual_taxa_entregador": dados.percentual_taxa_entregador,
        "entregador_id": dados.entregador_id,
        "loja_origem": dados.loja_origem,
        "endereco_entrega": dados.endereco_entrega,
        "distancia_km": dados.distancia_km,
        "valor_por_km": dados.valor_por_km,
        "observacoes_entrega": dados.observacoes_entrega,
        "tenant_id": tenant_id,
    }

    # Chamar service (toda lógica de negócio está lá)
    venda_dict = VendaService.criar_venda(
        payload=payload, user_id=current_user.id, db=db
    )

    # ============================================================================
    # 🤖 PROCESSAMENTO PASSIVO DE OPORTUNIDADES (background, não-bloqueante)
    # ============================================================================
    try:
        from uuid import UUID

        # Obter processador para sessão (tenant + session_id único)
        session_id = f"venda_{venda_dict['id']}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)), session_id=session_id
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
                    "categoria": None,  # Placeholder - expandir com dados do produto se necessário
                }
                for item in dados.itens
            ]
            processor.on_item_added(
                cliente_id=UUID(str(dados.cliente_id)) if dados.cliente_id else None,
                itens_carrinho=itens_contexto,
            )
    except Exception as e:
        # Fail-safe: Nunca deixar background processor afetar fluxo principal
        logger.debug(f"Background processor (criar): {str(e)}")
        pass

    return venda_dict


@router.put("/{venda_id}")
def atualizar_venda(
    venda_id: int,
    dados: CriarVendaRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza uma venda existente (somente vendas abertas)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar venda
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Só permite atualizar vendas abertas
    if venda.status != "aberta":
        raise HTTPException(
            status_code=400,
            detail=f'Não é possível atualizar venda com status "{venda.status}". Apenas vendas abertas podem ser atualizadas.',
        )

    # Validações
    if not dados.itens or len(dados.itens) == 0:
        raise HTTPException(
            status_code=400, detail="A venda deve ter pelo menos um item"
        )

    # Validar endereço obrigatório quando tem entrega
    if dados.tem_entrega and not dados.endereco_entrega:
        raise HTTPException(
            status_code=400,
            detail="❌ Endereço de entrega é obrigatório quando a venda tem entrega. Selecione o endereço do cliente ou digite um novo.",
        )

    # Validar entregador obrigatório quando tem entrega
    tem_entrega = bool(dados.tem_entrega)
    taxa_entrega = float(dados.taxa_entrega or 0) if tem_entrega else 0.0
    percentual_taxa_entregador = (
        float(dados.percentual_taxa_entregador or 0) if tem_entrega else 0.0
    )
    percentual_taxa_loja = (
        float(
            dados.percentual_taxa_loja
            if dados.percentual_taxa_loja is not None
            else (100 if taxa_entrega > 0 else 0)
        )
        if tem_entrega
        else 0.0
    )
    if (
        tem_entrega
        and taxa_entrega > 0
        and percentual_taxa_entregador == 0
        and percentual_taxa_loja == 0
    ):
        percentual_taxa_loja = 100.0
    valor_taxa_entregador = (
        taxa_entrega * percentual_taxa_entregador / 100 if taxa_entrega > 0 else 0.0
    )
    valor_taxa_loja = (
        taxa_entrega * percentual_taxa_loja / 100 if taxa_entrega > 0 else 0.0
    )
    entregador_id_resolvido = (
        (dados.entregador_id or venda.entregador_id) if tem_entrega else None
    )

    if tem_entrega and not entregador_id_resolvido:
        raise HTTPException(
            status_code=400,
            detail="❌ Entregador é obrigatório quando a venda tem entrega. Selecione um entregador antes de salvar.",
        )

    # Calcular novos totais
    totais = calcular_totais_venda(
        dados.itens,
        dados.desconto_valor or 0,
        dados.desconto_percentual or 0,
        taxa_entrega,
    )

    logger.info(f"\n🔄 ATUALIZANDO VENDA {venda_id}:")
    logger.info(f"   funcionario_id recebido: {dados.funcionario_id}")
    logger.info(f"   funcionario_id anterior: {venda.funcionario_id}")

    # Atualizar campos da venda
    venda.cliente_id = dados.cliente_id
    venda.vendedor_id = dados.vendedor_id or current_user.id
    venda.funcionario_id = (
        dados.funcionario_id
    )  # ✅ Funcionário/Veterinário que recebe comissão

    logger.info(f"   funcionario_id novo: {venda.funcionario_id}")

    venda.subtotal = totais["subtotal"]
    venda.desconto_valor = totais["desconto_valor"]
    venda.desconto_percentual = dados.desconto_percentual or 0
    venda.cupom_code = dados.cupom_code.strip().upper() if dados.cupom_code else None
    venda.cupom_discount_applied = dados.cupom_discount_applied
    venda.total = totais["total"]
    venda.observacoes = dados.observacoes
    venda.tem_entrega = tem_entrega
    venda.taxa_entrega = taxa_entrega
    venda.percentual_taxa_entregador = percentual_taxa_entregador
    venda.percentual_taxa_loja = percentual_taxa_loja
    venda.valor_taxa_entregador = valor_taxa_entregador
    venda.valor_taxa_loja = valor_taxa_loja
    venda.entregador_id = entregador_id_resolvido
    venda.loja_origem = dados.loja_origem if tem_entrega else None
    venda.endereco_entrega = dados.endereco_entrega if tem_entrega else None
    venda.distancia_km = dados.distancia_km if tem_entrega else None
    venda.valor_por_km = dados.valor_por_km if tem_entrega else None
    venda.observacoes_entrega = dados.observacoes_entrega if tem_entrega else None
    venda.status_entrega = _resolver_status_entrega_atualizacao(
        tem_entrega, venda.status_entrega
    )
    if not tem_entrega:
        venda.data_entrega = None
    venda.updated_at = datetime.now()

    # 🔄 DEVOLVER ESTOQUE dos produtos REMOVIDOS
    # Compara itens antigos com novos e devolve o que foi removido
    itens_antigos = db.query(VendaItem).filter_by(venda_id=venda.id).all()
    produtos_antigos_ids = {
        item.produto_id for item in itens_antigos if item.produto_id
    }
    produtos_novos_ids = {item.produto_id for item in dados.itens if item.produto_id}
    produtos_removidos_ids = produtos_antigos_ids - produtos_novos_ids

    # Estornar estoque dos produtos removidos
    for item_antigo in itens_antigos:
        if item_antigo.produto_id in produtos_removidos_ids:
            try:
                logger.info(
                    f"📦 Devolvendo estoque (produto removido): Produto {item_antigo.produto_id} +{item_antigo.quantidade}"
                )
                EstoqueService.estornar_estoque(
                    produto_id=item_antigo.produto_id,
                    quantidade=float(item_antigo.quantidade),
                    motivo="ajuste",
                    referencia_id=venda.id,
                    referencia_tipo="venda_editada",
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                    db=db,
                    documento=None,
                    observacao=f"Produto removido da venda #{venda.id}",
                )
                log_action(
                    db=db,
                    user_id=current_user.id,
                    action="update",
                    entity_type="produtos",
                    entity_id=item_antigo.produto_id,
                    details=f"Estorno (+{item_antigo.quantidade}) - Produto removido da venda #{venda.id}",
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
            pet_id=item_data.pet_id,
        )
        db.add(item)

    db.commit()
    db.refresh(venda)

    log_action(
        db,
        current_user.id,
        "update",
        "vendas",
        venda.id,
        details=f"Venda {venda.numero_venda} atualizada - Total: R$ {totais['total']:.2f}",
    )

    # ============================================================================
    # ❌ IMPORTANTE: rota NÃO é criada automaticamente na edição da venda
    # ============================================================================
    # A criação da rota deve ocorrer apenas nos fluxos explícitos:
    # - ERP (Entregas em Aberto -> Criar Rota)
    # - App do entregador

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
            tenant_id=UUID(str(tenant_id)), session_id=session_id
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
                        "categoria": None,
                    }
                    for item in dados.itens
                ]

                # Atualização: pode ser adição ou remoção, usar on_item_added genericamente
                # (background processor analisa contexto internamente)
                processor.on_item_added(
                    cliente_id=UUID(str(dados.cliente_id))
                    if dados.cliente_id
                    else None,
                    itens_carrinho=itens_contexto,
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
    if venda.funcionario_id:
        try:
            # Buscar total pago com filtro tenant-safe em SQL bruto
            total_pago = _total_pago_venda(db, venda.id, tenant_id)
            total_venda = Decimal(str(venda.total))
            status_anterior = venda.status

            logger.info(f"📊 Venda {venda.id}: Total={total_venda}, Pago={total_pago}")

            # Se está totalmente paga, finalizar e gerar comissões
            if total_pago >= total_venda - Decimal("0.01"):  # Margem de 1 centavo
                logger.info(
                    f"✅ Venda {venda.id} está totalmente paga, finalizando e gerando comissões..."
                )

                # Atualizar status
                venda.status = "finalizada"
                venda.updated_at = datetime.now()
                get_or_build_venda_rentabilidade_snapshot(
                    venda,
                    db,
                    tenant_id,
                    persist_if_missing=True,
                    force_refresh=True,
                )
                db.commit()
                db.refresh(venda)

            if venda.status in ["baixa_parcial", "finalizada"]:
                resultado_comissoes = _gerar_comissoes_pendentes_venda(
                    db=db,
                    venda=venda,
                    tenant_id=tenant_id,
                    trigger="update_sale",
                )

                if resultado_comissoes["comissoes_geradas"] > 0:
                    logger.info(
                        "Comissoes geradas ao atualizar venda %s: %s - Total: R$ %.2f",
                        venda.id,
                        resultado_comissoes["comissoes_geradas"],
                        resultado_comissoes["total_comissoes"],
                    )
                    struct_logger.info(
                        event="COMMISSION_GENERATED_ON_UPDATE",
                        message="Comissoes geradas ao atualizar venda com funcionario",
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        total_comissoes=resultado_comissoes["total_comissoes"],
                        status_anterior=status_anterior,
                    )

        except Exception as e:
            logger.error(
                f"❌ Erro ao verificar pagamentos e gerar comissões: {str(e)}",
                exc_info=True,
            )
            # Não falha a atualização por erro nas comissões

    return venda.to_dict()


def _resolver_retirado_por_conclusao(venda, retirado_por: str | None) -> str | None:
    nome = str(retirado_por or "").strip()
    if not getattr(venda, "tem_entrega", False) and not nome:
        raise HTTPException(status_code=400, detail="Informe quem retirou o pedido.")
    return nome or None


@router.post("/{venda_id}/marcar-entregue")
async def marcar_venda_entregue(
    venda_id: int,
    dados: MarcarEntregueRequest = MarcarEntregueRequest(),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Confirma que o cliente retirou o pedido na loja (ou terceiro apresentou a palavra-chave)."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = (
        db.query(Venda)
        .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    retirado_por = _resolver_retirado_por_conclusao(venda, dados.retirado_por)
    venda.status_entrega = "entregue"
    venda.data_entrega = datetime.now()
    if retirado_por:
        venda.retirado_por = retirado_por
    db.commit()
    notify_sale_order_event(db, venda=venda, event="delivered")
    return {
        "id": venda_id,
        "status_entrega": "entregue",
        "data_entrega": venda.data_entrega.isoformat(),
        "retirado_por": venda.retirado_por,
    }


@router.post("/{venda_id}/marcar-pronto-retirada")
async def marcar_venda_pronta_retirada(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Marca pedido de retirada/app/e-commerce como separado e pronto para o cliente."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = (
        db.query(Venda)
        .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")
    if venda.status_entrega == "entregue":
        raise HTTPException(status_code=400, detail="Venda ja foi entregue/retirada")
    venda.status_entrega = "pronto"
    db.commit()
    notify_sale_order_event(db, venda=venda, event="ready_for_pickup")
    return {"id": venda_id, "status_entrega": "pronto"}


@router.post("/{venda_id}/finalizar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita finalização duplicada
async def finalizar_venda(
    venda_id: int,
    dados: FinalizarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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
        total_pagamentos=len(dados.pagamentos) if dados and dados.pagamentos else 0,
    )

    # ========================================
    # 🔒 VALIDAÇÃO: ENTREGADOR OBRIGATÓRIO QUANDO TEM ENTREGA
    # ========================================
    venda_temp = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if venda_temp and venda_temp.tem_entrega and not venda_temp.entregador_id:
        raise HTTPException(
            status_code=400,
            detail="❌ Não é possível finalizar. Entregador é obrigatório quando a venda tem entrega. Atribua um entregador antes de finalizar.",
        )

    # ============================================================
    # 🔥 ORQUESTRAÇÃO ATÔMICA VIA VendaService
    # ============================================================

    from app.vendas import VendaService

    # Converter pagamentos do request para formato do service
    pagamentos_list = (
        [
            {
                "forma_pagamento": p.forma_pagamento,
                "valor": p.valor,
                "numero_parcelas": p.numero_parcelas,
                "bandeira": getattr(p, "bandeira", None),
                "nsu_cartao": getattr(p, "nsu_cartao", None),
                "operadora_id": getattr(
                    p, "operadora_id", None
                ),  # 🆕 Capturar operadora
            }
            for p in dados.pagamentos
        ]
        if dados.pagamentos
        else []
    )

    # Executar finalização com transação atômica única
    resultado = VendaService.finalizar_venda(
        venda_id=venda_id,
        pagamentos=pagamentos_list,
        user_id=current_user.id,
        user_nome=current_user.nome or current_user.email or "Usuário",
        tenant_id=tenant_id,
        cupom_code=dados.cupom_code,
        cupom_discount_applied=dados.cupom_discount_applied,
        db=db,
    )

    # Log de sucesso
    struct_logger.info(
        event="FINALIZE_SUCCESS",
        message="Venda finalizada com sucesso",
        venda_id=venda_id,
        numero_venda=resultado["venda"]["numero_venda"],
        status=resultado["venda"]["status"],
        total_pago=resultado["venda"]["total_pago"],
    )

    # ============================================================
    # ETAPA PÓS-COMMIT: COMISSÕES E LEMBRETES (operações secundárias)
    # ============================================================

    # Recarregar venda para ter dados atualizados após commit
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if not venda:
        raise HTTPException(
            status_code=404, detail="Venda não encontrada após finalização"
        )

    if venda.funcionario_id:
        try:
            resultado_comissoes = _gerar_comissoes_pendentes_venda(
                db=db,
                venda=venda,
                tenant_id=tenant_id,
                trigger="finalize_sale",
            )
            if resultado_comissoes["comissoes_geradas"] > 0:
                logger.info(
                    "Comissoes geradas ao finalizar venda %s: %s - Total: R$ %.2f",
                    venda.id,
                    resultado_comissoes["comissoes_geradas"],
                    resultado_comissoes["total_comissoes"],
                )
                struct_logger.info(
                    event="COMMISSION_GENERATED_ON_FINALIZE",
                    message="Comissoes geradas ao finalizar venda",
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    total_comissoes=resultado_comissoes["total_comissoes"],
                )
            else:
                logger.info("Nenhuma comissao nova gerada ao finalizar venda")
        except Exception as e:
            logger.error(
                "Erro ao gerar comissoes ao finalizar venda %s: %s",
                venda.id,
                str(e),
                exc_info=True,
            )
            # Nao abortar a finalizacao da venda por erro nas comissoes.
    else:
        logger.info("Venda sem funcionario - comissoes nao geradas")

    # 🔔 SISTEMA DE RECORRÊNCIA - Criar/Atualizar lembretes automaticamente
    from app.produtos_models import Lembrete
    from app.models import Pet

    lembretes_criados = []
    lembretes_atualizados = []

    try:
        for item in venda.itens:
            # Apenas produtos com pet_id vinculado e que tenham recorrência
            if item.tipo == "produto" and item.produto_id and item.pet_id:
                # 🔒 SEGURANÇA: Validar que produto pertence ao usuário
                produto = safe_get_produto(db, item.produto_id, current_user.id)

                # 🔒 SEGURANÇA: Validar que pet pertence ao cliente do usuário
                pet = (
                    db.query(Pet)
                    .filter(Pet.id == item.pet_id, Pet.cliente_id == venda.cliente_id)
                    .first()
                )

                if not produto or not pet:
                    continue  # Ignorar se não encontrado (segurança)

                if (
                    produto
                    and pet
                    and produto.tem_recorrencia
                    and produto.intervalo_dias
                ):
                    # Verificar se já existe lembrete PENDENTE para este produto+pet
                    lembrete_existente = (
                        db.query(Lembrete)
                        .filter(
                            Lembrete.tenant_id == tenant_id,
                            Lembrete.cliente_id == venda.cliente_id,
                            Lembrete.pet_id == item.pet_id,
                            Lembrete.produto_id == item.produto_id,
                            Lembrete.status.in_(["pendente", "notificado"]),
                        )
                        .first()
                    )

                    if lembrete_existente:
                        # ✅ CLIENTE JÁ TINHA LEMBRETE - DAR CHECK AUTOMÁTICO
                        historico = (
                            json.loads(lembrete_existente.historico_doses)
                            if lembrete_existente.historico_doses
                            else []
                        )
                        historico.append(
                            {
                                "dose": lembrete_existente.dose_atual,
                                "data": datetime.utcnow().isoformat(),
                                "comprou": True,
                                "status": "completado",
                                "venda_id": venda.id,
                            }
                        )

                        # Marcar como completado
                        lembrete_existente.status = "completado"
                        lembrete_existente.data_completado = datetime.utcnow()
                        lembrete_existente.historico_doses = json.dumps(historico)

                        # Verificar se é a última dose
                        if (
                            lembrete_existente.dose_total
                            and lembrete_existente.dose_atual
                            >= lembrete_existente.dose_total
                        ):
                            # Última dose - NÃO criar novo lembrete
                            lembretes_atualizados.append(
                                {
                                    "acao": "finalizado",
                                    "produto": produto.nome,
                                    "pet": pet.nome,
                                    "dose": f"{lembrete_existente.dose_atual}/{lembrete_existente.dose_total}",
                                }
                            )
                        else:
                            # Criar novo lembrete para próxima dose
                            data_proxima = datetime.utcnow() + timedelta(
                                days=produto.intervalo_dias
                            )
                            data_notificacao = data_proxima - timedelta(days=7)

                            novo_lembrete = Lembrete(
                                tenant_id=tenant_id,
                                user_id=current_user.id,
                                cliente_id=venda.cliente_id,
                                pet_id=item.pet_id,
                                produto_id=item.produto_id,
                                venda_id=venda.id,
                                data_compra=datetime.utcnow(),
                                data_proxima_dose=data_proxima,
                                data_notificacao_7_dias=data_notificacao,
                                status="pendente",
                                quantidade_recomendada=float(item.quantidade),
                                preco_estimado=produto.preco_venda,
                                dose_atual=lembrete_existente.dose_atual + 1,
                                dose_total=lembrete_existente.dose_total,
                                historico_doses=json.dumps(historico),
                            )
                            db.add(novo_lembrete)

                            lembretes_atualizados.append(
                                {
                                    "acao": "renovado",
                                    "produto": produto.nome,
                                    "pet": pet.nome,
                                    "dose": f"{novo_lembrete.dose_atual}/{novo_lembrete.dose_total or '∞'}",
                                }
                            )
                    else:
                        # ✨ PRIMEIRA VENDA COM RECORRÊNCIA - CRIAR LEMBRETE
                        data_proxima = datetime.utcnow() + timedelta(
                            days=produto.intervalo_dias
                        )
                        data_notificacao = data_proxima - timedelta(days=7)

                        historico_inicial = [
                            {
                                "dose": 1,
                                "data": datetime.utcnow().isoformat(),
                                "comprou": True,
                                "status": "criado",
                                "venda_id": venda.id,
                            }
                        ]

                        novo_lembrete = Lembrete(
                            tenant_id=tenant_id,
                            user_id=current_user.id,
                            cliente_id=venda.cliente_id,
                            pet_id=item.pet_id,
                            produto_id=item.produto_id,
                            venda_id=venda.id,
                            data_compra=datetime.utcnow(),
                            data_proxima_dose=data_proxima,
                            data_notificacao_7_dias=data_notificacao,
                            status="pendente",
                            quantidade_recomendada=float(item.quantidade),
                            preco_estimado=produto.preco_venda,
                            dose_atual=1,
                            dose_total=produto.numero_doses,
                            historico_doses=json.dumps(historico_inicial),
                        )
                        db.add(novo_lembrete)

                        lembretes_criados.append(
                            {
                                "produto": produto.nome,
                                "pet": pet.nome,
                                "proxima_dose": data_proxima.strftime("%d/%m/%Y"),
                                "dose_total": produto.numero_doses or "∞",
                            }
                        )

        if lembretes_criados or lembretes_atualizados:
            logger.info(
                f"🔔 Lembretes: {len(lembretes_criados)} criados, {len(lembretes_atualizados)} atualizados"
            )

    except Exception as e:
        logger.error(f"⚠️ Erro ao processar lembretes: {str(e)}")
        # Não abortar a venda por erro nos lembretes

    db.commit()

    log_action(
        db,
        current_user.id,
        "UPDATE",
        "vendas",
        venda.id,
        details=f"Venda {venda.numero_venda} finalizada - Total: R$ {float(venda.total):.2f}",
    )

    # ============================================================================
    # 💾 INVALIDAR CACHE DE OPORTUNIDADES (venda finalizada)
    # ============================================================================
    try:
        from uuid import UUID

        session_id = f"venda_{venda.id}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)), session_id=session_id
        )
        processor.cleanup()  # Limpa processador e invalida cache
    except Exception as e:
        logger.debug(f"Cache cleanup (finalizar): {str(e)}")
        pass

    # ✅ LOG DE SUCESSO ESTRUTURADO
    total_pago = (
        sum(float(p.valor) for p in venda.pagamentos) if venda.pagamentos else 0
    )
    struct_logger.info(
        event="FINALIZE_COMPLETE",
        message="Venda finalizada completamente (com comissões e lembretes)",
        venda_id=venda_id,
        numero_venda=venda.numero_venda,
        status_final=venda.status,
        total_venda=float(venda.total),
        total_pagamentos=total_pago,
        forma_pagamento=dados.pagamentos[0].forma_pagamento
        if dados.pagamentos
        else None,
        lembretes_criados=len(lembretes_criados),
        lembretes_atualizados=len(lembretes_atualizados),
    )

    # Adicionar informações de lembretes no retorno
    venda_dict = venda.to_dict()
    if lembretes_criados or lembretes_atualizados:
        venda_dict["lembretes"] = {
            "criados": lembretes_criados,
            "atualizados": lembretes_atualizados,
        }

    # Adicionar dados do resultado do VendaService (se disponível)
    if "operacoes" in resultado:
        venda_dict["resultado_operacoes"] = resultado["operacoes"]

    # ============================================================
    # 🎯 CAMPANHAS — Publicar evento purchase_completed na fila
    # Nunca bloqueia a venda em caso de falha
    # ============================================================
    if venda.cliente_id:
        try:
            from app.campaigns.models import CampaignEventQueue, EventOriginEnum

            canal_venda = venda.canal or "loja_fisica"
            evento_campanha = CampaignEventQueue(
                tenant_id=tenant_id,
                event_type="purchase_completed",
                event_origin=EventOriginEnum.user_action,
                event_depth=0,
                payload={
                    "customer_id": venda.cliente_id,
                    "venda_id": venda.id,
                    "venda_total": float(venda.total or 0),
                    "canal": canal_venda,
                },
            )
            db.add(evento_campanha)
            db.commit()
            logger.info(
                "[Campanhas] purchase_completed publicado venda_id=%d cliente_id=%d",
                venda.id,
                venda.cliente_id,
            )
        except Exception as e_camp:
            logger.error("[Campanhas] Erro ao publicar purchase_completed: %s", e_camp)

    return venda_dict


@router.post("/{venda_id}/cancelar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita cancelamento duplicado
async def cancelar_venda(
    venda_id: int,
    dados: CancelarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cancela uma venda realizando estorno completo.

    🎯 ROTA REFATORADA: Agora usa VendaService como orquestrador central.
    A rota apenas valida o request e chama o service.
    """
    from app.vendas.service import VendaService

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    motivo_final = _normalizar_motivo_exclusao_venda(dados.motivo)

    set_user_id(current_user.id)
    struct_logger.info(
        event="VENDA_CANCELAMENTO_START",
        message="Iniciando cancelamento de venda via service",
        venda_id=venda_id,
        motivo=motivo_final,
    )

    # Chamar service (toda lógica de negócio está lá)
    resultado = VendaService.cancelar_venda(
        venda_id=venda_id,
        motivo=motivo_final,
        user_id=current_user.id,
        tenant_id=tenant_id,
        db=db,
    )

    struct_logger.info(
        event="VENDA_CANCELADA_SUCESSO",
        message="Cancelamento concluído com sucesso",
        venda_id=venda_id,
        numero_venda=resultado["venda"]["numero_venda"],
        itens_estornados=resultado["estornos"]["itens_estornados"],
    )

    # ============================================================================
    # 💾 INVALIDAR CACHE DE OPORTUNIDADES (venda cancelada)
    # ============================================================================
    try:
        from uuid import UUID

        session_id = f"venda_{venda_id}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)), session_id=session_id
        )
        processor.cleanup()  # Limpa processador e invalida cache
    except Exception as e:
        logger.debug(f"Cache cleanup (cancelar): {str(e)}")
        pass

    return resultado["venda"]


@router.post("/{venda_id}/reabrir")
def reabrir_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Reabre uma venda finalizada (muda status para aberta)"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Impedir reabertura de vendas com NF emitida
    if venda.status == "pago_nf":
        raise HTTPException(
            status_code=400,
            detail="Não é possível reabrir uma venda com NF-e emitida. Cancele a nota fiscal primeiro.",
        )

    # Permitir reabrir vendas finalizadas ou parcialmente pagas
    if venda.status not in ["finalizada", "baixa_parcial"]:
        raise HTTPException(
            status_code=400,
            detail="Apenas vendas finalizadas ou com baixa parcial podem ser reabertas",
        )

    # Guardar status anterior para log
    status_anterior = venda.status

    # ============================================================================
    # 🧹 CANCELAR/REMOVER COMISSÕES EXISTENTES
    # ============================================================================
    comissoes_removidas = 0
    if venda.funcionario_id:
        try:
            # Contar comissões antes de remover
            comissoes_removidas = _contar_comissoes_venda(db, venda.id, tenant_id)

            if comissoes_removidas > 0:
                struct_logger.info(
                    event="COMMISSION_CANCEL_START",
                    message=f"Cancelando {comissoes_removidas} comissões por reabertura de venda",
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    count=comissoes_removidas,
                )

                # Remover comissões
                _remover_comissoes_venda(db, venda.id, tenant_id)

                # Também remover provisões de comissão em contas_pagar
                _remover_provisoes_comissao_venda(db, venda.id, tenant_id)

                struct_logger.info(
                    event="COMMISSION_CANCELLED",
                    message="Comissões canceladas com sucesso",
                    venda_id=venda.id,
                    count=comissoes_removidas,
                )
            else:
                logger.info(f"ℹ️  Venda #{venda.id} não tinha comissões para cancelar")

        except Exception as e:
            logger.error(
                f"❌ Erro ao cancelar comissões da venda {venda.id}: {e}", exc_info=True
            )
            struct_logger.error(
                event="COMMISSION_CANCEL_ERROR",
                message=f"Erro ao cancelar comissões: {str(e)}",
                venda_id=venda.id,
                error=str(e),
            )
            # Prosseguir com reabertura mesmo se falhar cancelamento de comissões

    # ℹ️  NOTA: NÃO devolvemos estoque ao reabrir!
    # O estoque só é devolvido ao:
    # 1. EDITAR venda e remover produtos
    # 2. EXCLUIR/CANCELAR venda completamente
    # Reabrir serve apenas para alterar forma de pagamento, não mexe em produtos

    # Mudar status para aberta
    venda.status = "aberta"
    venda.data_finalizacao = None
    venda.updated_at = datetime.now()
    invalidate_venda_rentabilidade_snapshot(venda)

    from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
    from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale
    from app.services.business_audit_service import (
        build_sale_reopened_metadata,
        log_business_event,
    )

    coupon_reversal_result = reverse_coupon_redemptions_for_sale(
        db,
        tenant_id=tenant_id,
        venda_id=venda.id,
        reason="Venda reaberta para edicao",
    )

    loyalty_void_result = void_loyalty_stamps_for_sale(
        db,
        tenant_id=tenant_id,
        venda_id=venda.id,
        reason="Venda reaberta para edicao",
    )

    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        event="sale.reopened",
        entity_type="vendas",
        entity_id=venda.id,
        old_value={"status": status_anterior},
        metadata=build_sale_reopened_metadata(
            venda=venda,
            previous_status=status_anterior,
            commissions_removed=comissoes_removidas,
            coupon_reversal=coupon_reversal_result,
            loyalty_void=loyalty_void_result,
        ),
        details=f"Venda #{venda.id} reaberta para edicao",
        commit=False,
    )

    db.commit()
    db.refresh(venda)

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="vendas",
        entity_id=venda.id,
        details=f"Venda #{venda.id} reaberta (status: {status_anterior} → aberta, comissões canceladas: {comissoes_removidas})",
    )

    return venda.to_dict()


@router.patch("/{venda_id}/status")
def atualizar_status_venda(
    venda_id: int,
    status_data: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza apenas o status da venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar a venda
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    # Extrair status do body
    novo_status = status_data.get("status")
    if not novo_status:
        raise HTTPException(status_code=400, detail="Status não informado")

    status_anterior = venda.status
    venda.status = novo_status
    venda.updated_at = datetime.now()

    if novo_status in ["finalizada", "baixa_parcial"]:
        get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=True,
            force_refresh=True,
        )
    elif novo_status == "aberta":
        invalidate_venda_rentabilidade_snapshot(venda)

    if status_anterior in ["finalizada", "baixa_parcial"] and novo_status not in [
        "finalizada",
        "baixa_parcial",
    ]:
        from app.campaigns.coupon_service import reverse_coupon_redemptions_for_sale
        from app.campaigns.loyalty_service import void_loyalty_stamps_for_sale

        reverse_coupon_redemptions_for_sale(
            db,
            tenant_id=tenant_id,
            venda_id=venda.id,
            reason=f"Status alterado para {novo_status}",
        )
        void_loyalty_stamps_for_sale(
            db,
            tenant_id=tenant_id,
            venda_id=venda.id,
            reason=f"Status alterado para {novo_status}",
        )
    # 🆕 GERAR COMISSÕES se estiver finalizando a venda (apenas se funcionário/veterinário foi selecionado)
    if (
        novo_status == "finalizada"
        and status_anterior != "finalizada"
        and venda.funcionario_id
    ):
        try:
            from app.comissoes_service import gerar_comissoes_venda

            struct_logger.info(
                event="COMMISSION_START",
                message=f"Gerando comissões via PATCH /status (status: {status_anterior} → {novo_status})",
                venda_id=venda.id,
                funcionario_id=venda.funcionario_id,
                trigger="status_change",
            )

            # 🔍 BUSCAR TODOS OS PAGAMENTOS DA VENDA
            # Precisamos gerar comissões para TODOS os pagamentos que ainda não têm comissão
            todos_pagamentos = _listar_pagamentos_venda_para_comissao(
                db, venda.id, tenant_id
            )

            if not todos_pagamentos:
                logger.info("ℹ️  Nenhum pagamento encontrado na venda")
            else:
                # 🔢 Verificar quais pagamentos já têm comissão
                parcelas_com_comissao = _parcelas_com_comissao_funcionario(
                    db,
                    venda.id,
                    venda.funcionario_id,
                    tenant_id,
                )
                logger.info(
                    f"📊 Pagamentos: {len(todos_pagamentos)} total, {len(parcelas_com_comissao)} já com comissão"
                )

                # 🔄 GERAR UMA COMISSÃO PARA CADA PAGAMENTO SEM COMISSÃO
                comissoes_geradas = 0
                total_comissoes = Decimal("0")

                for idx, pagamento_row in enumerate(todos_pagamentos, start=1):
                    parcela_numero = idx

                    # Pular se já tem comissão
                    if parcela_numero in parcelas_com_comissao:
                        logger.info(
                            f"⏭️  Parcela {parcela_numero} já tem comissão - pulando"
                        )
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
                        parcela_numero=parcela_numero,
                    )

                    resultado = gerar_comissoes_venda(
                        venda_id=venda.id,
                        funcionario_id=venda.funcionario_id,
                        valor_pago=valor_pagamento,
                        forma_pagamento=forma_pagamento,
                        parcela_numero=parcela_numero,
                        db=db,
                    )

                    if resultado and resultado.get("success"):
                        if not resultado.get("duplicated"):
                            comissoes_geradas += 1
                            total_comissoes += Decimal(
                                str(resultado.get("total_comissao", 0))
                            )
                            struct_logger.info(
                                event="COMMISSION_GENERATED",
                                message="Comissão gerada com sucesso",
                                venda_id=venda.id,
                                parcela_numero=parcela_numero,
                                total_comissao=float(
                                    resultado.get("total_comissao", 0)
                                ),
                            )

                if comissoes_geradas > 0:
                    logger.info(
                        f"✅ {comissoes_geradas} comissões geradas - Total: R$ {total_comissoes:.2f}"
                    )
                else:
                    logger.info(
                        "ℹ️  Nenhuma comissão nova gerada (todas já existiam ou sem configuração)"
                    )

        except Exception as e:
            logger.error(
                f"❌ Erro ao gerar comissões para venda {venda.id}: {str(e)}",
                exc_info=True,
            )
            struct_logger.error(
                event="COMMISSION_ERROR",
                message=f"Erro ao gerar comissões: {str(e)}",
                venda_id=venda.id,
                error=str(e),
                trigger="status_change",
            )
            # Não abortar a atualização por erro nas comissões

    db.commit()
    db.refresh(venda)

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="vendas",
        entity_id=venda.id,
        details=f"Status da venda #{venda.id} alterado: {status_anterior} → {novo_status}",
    )

    return {"success": True, "status": novo_status}

    return {"message": "Status atualizado com sucesso", "status": venda.status}


@router.delete("/{venda_id}")
def excluir_venda(
    venda_id: int,
    dados: Optional[ExcluirVendaRequest] = None,
    motivo: Optional[str] = Query(
        None, description="Justificativa para cancelar/excluir a venda"
    ),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cancelar uma venda mantendo rastreabilidade para auditoria."""
    from app.rotas_entrega_models import RotaEntrega
    from app.vendas.service import VendaService

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    motivo_payload = motivo
    if dados:
        motivo_payload = motivo_payload or dados.motivo or dados.justificativa
    motivo_final = _normalizar_motivo_exclusao_venda(motivo_payload)

    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")

    if venda.status == "pago_nf":
        raise HTTPException(
            status_code=400,
            detail="Nao e possivel cancelar/excluir uma venda com NF-e emitida. Cancele a nota fiscal primeiro.",
        )

    rota_vinculada = db.query(RotaEntrega).filter_by(venda_id=venda_id).first()
    if rota_vinculada:
        passos_resolucao = [
            f"1. Acesse a rota de entrega #{rota_vinculada.id}",
            "2. Remova esta venda da rota",
            "3. Tente cancelar/excluir a venda novamente",
        ]
        raise HTTPException(
            status_code=400,
            detail={
                "erro": "Venda vinculada a uma rota de entrega",
                "mensagem": f"Esta venda esta associada a Rota #{rota_vinculada.id} (Status: {rota_vinculada.status})",
                "solucao": "Para cancelar/excluir esta venda, primeiro remova-a da rota de entrega.",
                "passos": passos_resolucao,
                "rota_id": rota_vinculada.id,
                "rota_status": rota_vinculada.status,
            },
        )

    logger.info("Cancelando venda por rota DELETE preservando auditoria")
    resultado = VendaService.cancelar_venda(
        venda_id=venda_id,
        motivo=motivo_final,
        user_id=current_user.id,
        tenant_id=tenant_id,
        db=db,
    )

    return {
        "message": "Venda cancelada com sucesso e mantida no historico",
        "venda": resultado["venda"],
        "itens_devolvidos": resultado["estornos"].get("itens_estornados", 0),
    }


# ============================================================================


@router.get("/relatorios/resumo")
def relatorio_resumo(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Relatório resumo de vendas"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    query = db.query(Venda).filter_by(tenant_id=tenant_id)

    if data_inicio:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
        data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0)
        query = query.filter(Venda.data_venda >= data_inicio_dt)

    if data_fim:
        # Datas no banco são naive (sem timezone) em horário de Brasília
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(Venda.data_venda <= data_fim_dt)

    vendas = query.all()

    # Calcular resumo
    total_vendas = len(vendas)
    total_valor = sum(float(v.total) for v in vendas if v.status != "cancelada")
    total_canceladas = sum(1 for v in vendas if v.status == "cancelada")

    # Por forma de pagamento
    pagamentos_resumo = {}
    for venda in vendas:
        if venda.status != "cancelada":
            for pag in venda.pagamentos:
                forma = pag.forma_pagamento
                if forma not in pagamentos_resumo:
                    pagamentos_resumo[forma] = 0
                pagamentos_resumo[forma] += float(pag.valor)

    return {
        "total_vendas": total_vendas,
        "total_valor": total_valor,
        "total_canceladas": total_canceladas,
        "pagamentos_resumo": pagamentos_resumo,
        "periodo": {
            "inicio": data_inicio if data_inicio else None,
            "fim": data_fim if data_fim else None,
        },
    }
