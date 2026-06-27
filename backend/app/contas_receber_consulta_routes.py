"""Rotas de consulta e resumo de contas a receber."""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .contas_receber_schemas import ContaReceberResponse
from .db import get_session
from .financeiro_models import ContaReceber
from .models import Cliente

router = APIRouter()


@router.get("/", response_model=List[ContaReceberResponse])
def listar_contas_receber(
    status: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    categoria_id: Optional[int] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    apenas_vencidas: bool = Query(False),
    apenas_vencer: bool = Query(False),
    numero_venda: Optional[str] = Query(None),  # Filtro por nÃºmero da venda
    limit: int = Query(500, le=1000),  # Aumentado para 500 registros por padrÃ£o
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista contas a receber com filtros
    """
    current_user, _tenant_id = user_and_tenant

    query = (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.categoria))
        .filter(ContaReceber.user_id == current_user.id)
    )

    # Filtros
    if status:
        query = query.filter(ContaReceber.status == status)
    if cliente_id:
        query = query.filter(ContaReceber.cliente_id == cliente_id)
    if categoria_id:
        query = query.filter(ContaReceber.categoria_id == categoria_id)
    if data_inicio:
        query = query.filter(ContaReceber.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_vencimento <= data_fim)

    # Filtro por nÃºmero de venda
    if numero_venda:
        from app.vendas_models import Venda

        vendas_ids = (
            db.query(Venda.id)
            .filter(
                Venda.user_id == current_user.id,
                Venda.numero_venda.like(f"%{numero_venda}%"),
            )
            .subquery()
        )
        query = query.filter(ContaReceber.venda_id.in_(vendas_ids))

    if apenas_vencidas:
        query = query.filter(
            and_(
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento < date.today(),
            )
        )
    if apenas_vencer:
        query = query.filter(
            and_(
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento >= date.today(),
            )
        )

    # Ordenar por ID DESC (mais recentes primeiro) e depois por data de vencimento
    query = query.order_by(desc(ContaReceber.id))
    contas = query.limit(limit).offset(offset).all()

    # Montar response
    resultado = []
    for conta in contas:
        # Calcular dias para vencimento
        dias_venc = None
        if conta.status == "pendente":
            dias_venc = (conta.data_vencimento - date.today()).days

        # Buscar nome do cliente
        cliente_nome = None
        if conta.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == conta.cliente_id).first()
            if cliente:
                cliente_nome = cliente.nome

        # Buscar nÃºmero da venda se existir venda_id
        numero_venda = None
        if conta.venda_id:
            from app.vendas_models import Venda

            venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
            if venda:
                numero_venda = venda.numero_venda

        resultado.append(
            {
                "id": conta.id,
                "descricao": conta.descricao,
                "cliente_nome": cliente_nome,
                "categoria_nome": conta.categoria.nome if conta.categoria else None,
                "valor_original": float(conta.valor_original),
                "valor_recebido": float(conta.valor_recebido),
                "valor_final": float(conta.valor_final),
                "data_emissao": conta.data_emissao,
                "data_vencimento": conta.data_vencimento,
                "data_recebimento": conta.data_recebimento,
                "status": conta.status,
                "dias_vencimento": dias_venc,
                "eh_parcelado": conta.eh_parcelado,
                "numero_parcela": conta.numero_parcela,
                "total_parcelas": conta.total_parcelas,
                "documento": conta.documento,
                "venda_id": conta.venda_id,
                "numero_venda": numero_venda,
                "observacoes": conta.observacoes,
                # ConciliaÃ§Ã£o de cartÃ£o
                "nsu": conta.nsu,
                "adquirente": conta.adquirente,
                "conciliado": conta.conciliado,
                "data_conciliacao": conta.data_conciliacao,
            }
        )

    return resultado


# ============================================================================
# BUSCAR CONTA ESPECÃFICA
# ============================================================================


@router.get("/{conta_id}")
def buscar_conta_receber(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Busca uma conta a receber especÃ­fica com todos os detalhes
    """
    from .vendas_models import Venda
    from .financeiro_models import ContaBancaria

    conta = (
        db.query(ContaReceber)
        .options(
            joinedload(ContaReceber.categoria), joinedload(ContaReceber.recebimentos)
        )
        .filter(ContaReceber.id == conta_id)
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta nÃ£o encontrada")

    # Buscar cliente
    cliente = None
    if conta.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == conta.cliente_id).first()

    # Buscar venda (se houver)
    venda = None
    if conta.venda_id:
        venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()

    # Buscar recebimentos com conta bancÃ¡ria
    recebimentos_detalhados = []
    for r in conta.recebimentos:
        conta_bancaria = None
        if r.conta_bancaria_id:
            conta_bancaria = (
                db.query(ContaBancaria)
                .filter(ContaBancaria.id == r.conta_bancaria_id)
                .first()
            )

        recebimentos_detalhados.append(
            {
                "id": r.id,
                "valor": float(r.valor_recebido),
                "data": r.data_recebimento,
                "forma_pagamento_id": r.forma_pagamento_id,
                "conta_bancaria_id": r.conta_bancaria_id,
                "conta_bancaria_nome": conta_bancaria.nome if conta_bancaria else None,
                "observacoes": r.observacoes,
            }
        )

    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "cliente": {
            "id": cliente.id if cliente else None,
            "nome": cliente.nome if cliente else None,
            "cpf": cliente.cpf if cliente else None,
        }
        if cliente
        else None,
        "venda": {
            "id": venda.id if venda else None,
            "numero_venda": venda.numero_venda if venda else None,
        }
        if venda
        else None,
        "categoria": {
            "id": conta.categoria.id if conta.categoria else None,
            "nome": conta.categoria.nome if conta.categoria else None,
            "cor": conta.categoria.cor if conta.categoria else None,
        }
        if conta.categoria
        else None,
        "valores": {
            "original": float(conta.valor_original),
            "recebido": float(conta.valor_recebido),
            "desconto": float(conta.valor_desconto),
            "juros": float(conta.valor_juros),
            "multa": float(conta.valor_multa),
            "final": float(conta.valor_final),
            "saldo": float(conta.valor_final - conta.valor_recebido),
        },
        "datas": {
            "emissao": conta.data_emissao,
            "vencimento": conta.data_vencimento,
            "recebimento": conta.data_recebimento,
        },
        "status": conta.status,
        "parcelamento": {
            "eh_parcelado": conta.eh_parcelado,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas,
        }
        if conta.eh_parcelado
        else None,
        "documento": conta.documento,
        "observacoes": conta.observacoes,
        "recebimentos": recebimentos_detalhados,
    }


# ============================================================================
# REGISTRAR RECEBIMENTO
# ============================================================================


@router.get("/dashboard/resumo")
def dashboard_contas_receber(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Resumo financeiro de contas a receber
    """
    hoje = date.today()

    # Total pendente
    total_pendente = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(ContaReceber.status.in_(["pendente", "parcial", "vencido"]))
        .scalar()
        or 0
    )

    # Vencidas
    total_vencido = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(ContaReceber.status == "pendente", ContaReceber.data_vencimento < hoje)
        )
        .scalar()
        or 0
    )

    count_vencidas = (
        db.query(func.count(ContaReceber.id))
        .filter(
            and_(ContaReceber.status == "pendente", ContaReceber.data_vencimento < hoje)
        )
        .scalar()
    )

    # Vence hoje
    total_vence_hoje = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.status == "pendente", ContaReceber.data_vencimento == hoje
            )
        )
        .scalar()
        or 0
    )

    # PrÃ³ximos 7 dias
    data_7dias = hoje + timedelta(days=7)
    total_7dias = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento.between(hoje, data_7dias),
            )
        )
        .scalar()
        or 0
    )

    # PrÃ³ximos 30 dias
    data_30dias = hoje + timedelta(days=30)
    total_30dias = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento.between(hoje, data_30dias),
            )
        )
        .scalar()
        or 0
    )

    # Recebido no mÃªs
    primeiro_dia_mes = hoje.replace(day=1)
    total_recebido_mes = (
        db.query(func.sum(ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.data_recebimento >= primeiro_dia_mes,
                ContaReceber.data_recebimento <= hoje,
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_pendente": float(total_pendente),
        "vencidas": {"total": float(total_vencido), "quantidade": count_vencidas},
        "vence_hoje": float(total_vence_hoje),
        "proximos_7_dias": float(total_7dias),
        "proximos_30_dias": float(total_30dias),
        "recebido_mes_atual": float(total_recebido_mes),
    }


# ============================================================================
# PROCESSAR RECORRÃŠNCIAS
# ============================================================================
