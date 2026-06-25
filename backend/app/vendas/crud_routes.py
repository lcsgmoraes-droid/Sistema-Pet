"""Rotas CRUD de vendas."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque.service import EstoqueService
from app.idempotency import idempotent
from app.models import Cliente
from app.produtos_models import Produto
from app.security.permissions_decorator import require_permission
from app.services.opportunity_background_processor import get_opportunity_processor
from app.services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)
from app.utils.logger import logger as struct_logger
from app.vendas.comissoes import _gerar_comissoes_pendentes_venda, _total_pago_venda
from app.vendas.regras import (
    _resolver_status_entrega_atualizacao,
    calcular_totais_venda,
)
from app.vendas.routes_common import _validar_tenant_e_obter_usuario
from app.vendas.schemas import CriarVendaRequest
from app.vendas_models import Venda, VendaItem

router = APIRouter()
logger = logging.getLogger(__name__)


def normalizar_status_filtro_vendas(status: Optional[str]) -> list[str]:
    if not status:
        return []

    return [item.strip() for item in status.split(",") if item.strip()]


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
    status_filtrados = normalizar_status_filtro_vendas(status)
    if len(status_filtrados) == 1:
        query = query.filter_by(status=status_filtrados[0])
    elif len(status_filtrados) > 1:
        query = query.filter(Venda.status.in_(status_filtrados))

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
