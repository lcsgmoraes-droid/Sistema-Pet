"""Rotas de consulta de clientes e extratos de campanhas."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sqlfunc, or_ as sql_or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.cashback_limit import cashback_use_limit_percent
from app.campaigns.loyalty_service import summarize_loyalty_balances_for_customer
from app.campaigns.cashback_wallet import (
    get_cashback_wallet,
    get_tenant_cashback_liability,
)
from app.campaigns.models import (
    Campaign,
    CashbackSourceTypeEnum,
    CashbackTransaction,
    Coupon,
    CouponStatusEnum,
    CustomerRankHistory,
    LoyaltyStamp,
)
from app.campaigns.routes_common import get_db
from app.campaigns.statement_service import build_campaign_customer_statement
from app.models import Cliente


router = APIRouter()


@router.get("/clientes/buscar")
def buscar_clientes_campanhas(
    search: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Busca clientes por nome, CPF ou telefone. Usado pelo Gestor de Benefícios."""
    _, tenant_id = user_and_tenant
    termo = f"%{search}%"
    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_(True),
            (
                Cliente.nome.ilike(termo)
                | Cliente.codigo.ilike(termo)
                | Cliente.cpf.ilike(termo)
                | Cliente.telefone.ilike(termo)
                | Cliente.celular.ilike(termo)
            ),
        )
        .order_by(Cliente.nome)
        .limit(limit)
        .all()
    )
    return {
        "clientes": [
            {
                "id": c.id,
                "codigo": c.codigo,
                "nome": c.nome,
                "cpf": c.cpf,
                "telefone": c.telefone or c.celular,
            }
            for c in clientes
        ]
    }


@router.get("/gestor/clientes-por-tipo")
def gestor_clientes_por_tipo(
    tipo: str = Query(..., regex="^(carimbos|cashback|cupons|ranking)$"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista clientes ativos em determinado tipo de benefício.
    tipo: carimbos | cashback | cupons | ranking
    """
    _, tenant_id = user_and_tenant

    if tipo == "carimbos":
        customer_ids = [
            row[0]
            for row in (
                db.query(LoyaltyStamp.customer_id)
                .filter(
                    LoyaltyStamp.tenant_id == tenant_id,
                    LoyaltyStamp.voided_at.is_(None),
                )
                .distinct()
                .all()
            )
        ]
        if not customer_ids:
            return {"clientes": []}

        clientes = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.ativo.is_(True),
                Cliente.id.in_(customer_ids),
            )
            .all()
        )
        rows = []
        for cliente in clientes:
            saldo = summarize_loyalty_balances_for_customer(
                db,
                tenant_id=tenant_id,
                customer_id=cliente.id,
            )
            total_disponivel = int(saldo.get("total_carimbos") or 0)
            if total_disponivel <= 0:
                continue
            rows.append((cliente, total_disponivel))

        rows.sort(key=lambda item: (-item[1], (item[0].nome or "").lower()))
        rows = rows[:limit]
        return {
            "clientes": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "cpf": c.cpf,
                    "telefone": c.telefone or c.celular,
                    "detalhe": f"{total} carimbo(s)",
                }
                for c, total in rows
            ]
        }

    elif tipo == "cashback":
        customer_ids = [
            row[0]
            for row in db.query(CashbackTransaction.customer_id)
            .filter(CashbackTransaction.tenant_id == tenant_id)
            .distinct()
            .all()
        ]
        if not customer_ids:
            return {"clientes": []}
        clientes = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.ativo.is_(True),
                Cliente.id.in_(customer_ids),
            )
            .all()
        )
        rows = [
            (
                cliente,
                get_cashback_wallet(
                    db, tenant_id=tenant_id, customer_id=cliente.id
                ).available,
            )
            for cliente in clientes
        ]
        rows = [(cliente, saldo) for cliente, saldo in rows if saldo > 0]
        rows.sort(key=lambda item: (-item[1], (item[0].nome or "").lower()))
        rows = rows[:limit]
        return {
            "clientes": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "cpf": c.cpf,
                    "telefone": c.telefone or c.celular,
                    "detalhe": f"R$ {float(saldo):.2f}".replace(".", ","),
                }
                for c, saldo in rows
            ]
        }

    elif tipo == "cupons":
        subq = (
            db.query(
                Coupon.customer_id,
                sqlfunc.count(Coupon.id).label("total"),
            )
            .filter(
                Coupon.tenant_id == tenant_id,
                Coupon.status == CouponStatusEnum.active,
            )
            .group_by(Coupon.customer_id)
            .subquery()
        )
        rows = (
            db.query(Cliente, subq.c.total)
            .join(subq, Cliente.id == subq.c.customer_id)
            .filter(Cliente.tenant_id == tenant_id, Cliente.ativo.is_(True))
            .order_by(subq.c.total.desc())
            .limit(limit)
            .all()
        )
        return {
            "clientes": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "cpf": c.cpf,
                    "telefone": c.telefone or c.celular,
                    "detalhe": f"{total} cupom(ns) ativo(s)",
                }
                for c, total in rows
            ]
        }

    else:  # ranking
        from datetime import date

        periodo_atual = date.today().strftime("%Y-%m")
        rows = (
            db.query(
                Cliente, CustomerRankHistory.rank_level, CustomerRankHistory.total_spent
            )
            .join(CustomerRankHistory, Cliente.id == CustomerRankHistory.customer_id)
            .filter(
                CustomerRankHistory.tenant_id == tenant_id,
                CustomerRankHistory.period == periodo_atual,
                Cliente.ativo.is_(True),
            )
            .order_by(CustomerRankHistory.total_spent.desc())
            .limit(limit)
            .all()
        )
        rank_map = {
            "platinum": "🏆 Platinum",
            "gold": "🥇 Ouro",
            "silver": "🥈 Prata",
            "bronze": "🥉 Bronze",
        }
        return {
            "clientes": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "cpf": c.cpf,
                    "telefone": c.telefone or c.celular,
                    "detalhe": rank_map.get(str(rank), str(rank)),
                }
                for c, rank, _ in rows
            ]
        }


@router.get("/clientes/{customer_id}/saldo")
def saldo_cliente(
    customer_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna o saldo de cashback, carimbos, cupons ativos e nível de ranking do cliente.
    Usado na tela do PDV quando um cliente é selecionado.
    """
    _, tenant_id = user_and_tenant

    saldo_cashback = float(
        get_cashback_wallet(db, tenant_id=tenant_id, customer_id=customer_id).available
    )
    cashback_limit_percent = cashback_use_limit_percent(db, tenant_id)
    now_utc = datetime.now(timezone.utc)

    loyalty_summary = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    # Cupons ativos do cliente
    cupons_ativos = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == customer_id,
            Coupon.status == CouponStatusEnum.active,
            sql_or_(Coupon.valid_until.is_(None), Coupon.valid_until >= now_utc),
        )
        .order_by(Coupon.id.desc())
        .limit(10)
        .all()
    )
    campanhas_cupons_map = {}
    campanha_ids = [c.campaign_id for c in cupons_ativos if c.campaign_id]
    if campanha_ids:
        campanhas = (
            db.query(Campaign)
            .filter(
                Campaign.tenant_id == tenant_id,
                Campaign.id.in_(campanha_ids),
            )
            .all()
        )
        campanhas_cupons_map = {campanha.id: campanha for campanha in campanhas}

    # Nível de ranking atual (último período calculado)
    rank_atual = (
        db.query(CustomerRankHistory)
        .filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.customer_id == customer_id,
        )
        .order_by(CustomerRankHistory.period.desc())
        .first()
    )

    return {
        "customer_id": customer_id,
        "saldo_cashback": saldo_cashback,
        "cashback_use_limit_percent": (
            float(cashback_limit_percent) if cashback_limit_percent is not None else None
        ),
        "total_carimbos": loyalty_summary["total_carimbos"],
        "total_carimbos_brutos": loyalty_summary["total_carimbos_brutos"],
        "carimbos_comprometidos_total": loyalty_summary["carimbos_comprometidos_total"],
        "carimbos_em_debito": loyalty_summary["carimbos_em_debito"],
        "carimbos_convertidos": loyalty_summary["carimbos_convertidos"],
        "ciclos_concluidos": loyalty_summary["ciclos_concluidos"],
        "rank_level": rank_atual.rank_level.value if rank_atual else "bronze",
        "rank_period": rank_atual.period if rank_atual else None,
        "rank_total_spent": float(rank_atual.total_spent) if rank_atual else 0.0,
        "rank_total_purchases": rank_atual.total_purchases if rank_atual else 0,
        "cupons_ativos": [
            {
                "code": c.code,
                "coupon_type": c.coupon_type.value,
                "discount_value": float(c.discount_value) if c.discount_value else None,
                "discount_percent": float(c.discount_percent)
                if c.discount_percent
                else None,
                "channel": c.channel.value,
                "status": c.status.value,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                "min_purchase_value": float(c.min_purchase_value)
                if c.min_purchase_value
                else None,
                "customer_id": c.customer_id,
                "campaign_id": c.campaign_id,
                "nome_campanha": (
                    campanhas_cupons_map[c.campaign_id].name
                    if c.campaign_id in campanhas_cupons_map
                    else None
                ),
                "campaign_type": (
                    campanhas_cupons_map[c.campaign_id].campaign_type.value
                    if c.campaign_id in campanhas_cupons_map
                    else None
                ),
                "campaign_params": (
                    campanhas_cupons_map[c.campaign_id].params
                    if c.campaign_id in campanhas_cupons_map
                    else None
                ),
                "meta": c.meta,
            }
            for c in cupons_ativos
        ],
    }


# ---------------------------------------------------------------------------
# Extrato unificado de campanhas por cliente
# ---------------------------------------------------------------------------


@router.get("/clientes/{customer_id}/extrato")
def extrato_campanhas_cliente(
    customer_id: int,
    tipo: Optional[str] = Query(
        "todos",
        description="todos | carimbos | cashback | cupons | ranking",
    ),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna um extrato auditavel de campanhas do cliente.

    O extrato junta as fontes historicas ja existentes:
    carimbos, cupons, resgates, cashback, estornos e ranking.
    """
    _, tenant_id = user_and_tenant

    cliente = (
        db.query(Cliente.id)
        .filter(Cliente.tenant_id == tenant_id, Cliente.id == customer_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    return build_campaign_customer_statement(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo=tipo,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Cashback — extrato do cliente
# ---------------------------------------------------------------------------


@router.get("/clientes/{customer_id}/cashback/extrato")
def extrato_cashback(
    customer_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna o extrato completo de cashback do cliente:
    créditos (entrada), débitos por resgate/expiração (saída), expirados.
    Usado no app mobile na tela de Benefícios.
    """
    _, tenant_id = user_and_tenant
    now_utc = datetime.now(timezone.utc)

    txs = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.tx_type != "closed",
        )
        .order_by(CashbackTransaction.id.desc())
        .limit(limit)
        .all()
    )

    wallet = get_cashback_wallet(
        db, tenant_id=tenant_id, customer_id=customer_id, as_of=now_utc
    )
    saldo_atual = float(wallet.available)

    items = []
    for t in txs:
        # Determina se este crédito específico está expirado
        is_expired_credit = wallet.expected_expiration_by_credit.get(t.id, 0) > 0
        items.append(
            {
                "id": t.id,
                "amount": float(t.amount),
                "tx_type": t.tx_type,  # 'credit' | 'debit' | 'expired'
                "source_type": t.source_type.value,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "expired": is_expired_credit,
            }
        )

    return {
        "customer_id": customer_id,
        "saldo_atual": saldo_atual,
        "transacoes": items,
    }


# ---------------------------------------------------------------------------
# Cashback — sugestão de pedido inteligente
# ---------------------------------------------------------------------------


@router.get("/clientes/{customer_id}/cashback/sugestao")
def sugestao_cashback(
    customer_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Baseado no padrão de compra do cliente, sugere um valor de pedido mostrando
    quanto ficaria após aplicar o saldo de cashback disponível.
    """
    _, tenant_id = user_and_tenant
    now_utc = datetime.now(timezone.utc)

    wallet = get_cashback_wallet(
        db, tenant_id=tenant_id, customer_id=customer_id, as_of=now_utc
    )
    saldo = float(wallet.available)

    # Ticket médio das últimas 10 compras (via cashback transactions de crédito)
    ultimas_compras = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.tx_type == "credit",
            CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign,
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(10)
        .all()
    )

    # Usa a descrição para extrair o valor original (cashback é % do valor)
    # Alternativa: usar média dos valores de cashback como proxy
    if ultimas_compras:
        ticket_medio_cashback = sum(float(t.amount) for t in ultimas_compras) / len(
            ultimas_compras
        )
        # Estimativa groossa: se o cashback médio é ~2%, ticket médio é ~50x
        # Mas sem acesso direto às vendas, usamos o valor de cashback como referência
        ticket_sugerido = round(ticket_medio_cashback * 50, 2)  # fallback heurístico
    else:
        ticket_sugerido = 100.0

    valor_com_cashback = max(0.0, round(ticket_sugerido - saldo, 2))

    # Próximo cashback que vai expirar
    creditos_com_saldo = [
        credit_id
        for credit_id, restante in wallet.remaining_by_credit.items()
        if restante > 0
    ]
    proximo_expirando = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.id.in_(creditos_com_saldo),
            CashbackTransaction.expires_at.isnot(None),
            CashbackTransaction.expires_at > now_utc,
        )
        .order_by(CashbackTransaction.expires_at.asc())
        .first()
    )

    return {
        "saldo_disponivel": saldo,
        "ticket_sugerido": ticket_sugerido,
        "valor_com_cashback": valor_com_cashback,
        "economia": min(saldo, ticket_sugerido),
        "proximo_expirando": {
            "amount": float(wallet.remaining_by_credit[proximo_expirando.id]),
            "expires_at": proximo_expirando.expires_at.isoformat(),
            "dias_restantes": max(0, (proximo_expirando.expires_at - now_utc).days),
        }
        if proximo_expirando
        else None,
    }


# ---------------------------------------------------------------------------
# Carimbos — listagem por cliente
# ---------------------------------------------------------------------------


@router.get("/relatorio")
def relatorio_campanhas(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    tipo: Optional[str] = Query(None, description="credito | resgate"),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Histórico de movimentações de cashback do tenant.
    Retorna créditos (purchase_completed) e resgates (resgate em venda).
    Usado na aba Relatórios em Campanhas.
    """
    from app.models import Cliente
    from app.vendas_models import Venda
    from app.vendas.cashback_financeiro import cashback_resgatado_liquido_por_transacao

    _, tenant_id = user_and_tenant

    q = db.query(CashbackTransaction).filter(CashbackTransaction.tenant_id == tenant_id)

    if data_inicio:
        q = q.filter(
            CashbackTransaction.created_at
            >= datetime.combine(data_inicio, datetime.min.time())
        )
    if data_fim:
        q = q.filter(
            CashbackTransaction.created_at
            <= datetime.combine(data_fim, datetime.max.time())
        )
    if tipo == "credito":
        q = q.filter(CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign)
    elif tipo == "resgate":
        q = q.filter(
            CashbackTransaction.source_type == CashbackSourceTypeEnum.redemption
        )

    transacoes = []
    total_creditado = Decimal("0.00")
    resgate_ids = []
    for t in q.order_by(CashbackTransaction.id.desc()).yield_per(500):
        if t.source_type == CashbackSourceTypeEnum.campaign:
            total_creditado += Decimal(str(t.amount))
        elif t.source_type == CashbackSourceTypeEnum.redemption:
            resgate_ids.append(t.id)
        if len(transacoes) < 500:
            transacoes.append(t)
    resgate_liquido = cashback_resgatado_liquido_por_transacao(
        db,
        tenant_id=tenant_id,
        redemption_ids=resgate_ids,
    )

    # Buscar nomes de clientes em lote
    customer_ids = list({t.customer_id for t in transacoes})
    clientes_map = {}
    if customer_ids:
        clientes = (
            db.query(Cliente)
            .filter(
                Cliente.id.in_(customer_ids),
                Cliente.tenant_id == tenant_id,
            )
            .all()
        )
        clientes_map = {c.id: c.nome for c in clientes}

    # Buscar números de venda em lote (source_id é venda_id para resgates)
    venda_ids = list(
        {
            t.source_id
            for t in transacoes
            if t.source_id and t.source_type == CashbackSourceTypeEnum.redemption
        }
    )
    vendas_map = {}
    if venda_ids:
        vendas = (
            db.query(Venda)
            .filter(
                Venda.id.in_(venda_ids),
                Venda.tenant_id == tenant_id,
            )
            .all()
        )
        vendas_map = {v.id: v.numero_venda for v in vendas}

    resultado = []
    for t in transacoes:
        eh_resgate = t.source_type == CashbackSourceTypeEnum.redemption
        valor = resgate_liquido.get(t.id, 0) if eh_resgate else abs(t.amount)
        if eh_resgate and valor <= 0:
            continue
        tipo_movimento = (
            "resgate"
            if eh_resgate
            else "estorno"
            if t.source_type == CashbackSourceTypeEnum.reversal
            else "expiracao"
            if t.source_type == CashbackSourceTypeEnum.expiration
            else "credito"
            if t.source_type == CashbackSourceTypeEnum.campaign
            else "ajuste"
        )
        resultado.append(
            {
                "id": t.id,
                "data": t.created_at.isoformat(),
                "cliente_id": t.customer_id,
                "cliente_nome": clientes_map.get(
                    t.customer_id, f"Cliente #{t.customer_id}"
                ),
                "tipo": tipo_movimento,
                "valor": float(valor),
                "source_type": t.source_type.value if t.source_type else None,
                "venda_id": t.source_id if eh_resgate else None,
                "numero_venda": vendas_map.get(t.source_id)
                if eh_resgate and t.source_id
                else None,
                "descricao": t.description,
            }
        )

    # Totais
    total_resgatado = sum(resgate_liquido.values())

    return {
        "transacoes": resultado,
        "total_creditado": round(float(total_creditado), 2),
        "total_resgatado": round(total_resgatado, 2),
        "saldo_total": float(get_tenant_cashback_liability(db, tenant_id=tenant_id)),
    }


# ---------------------------------------------------------------------------
# Carimbos — lançamento manual
# ---------------------------------------------------------------------------
