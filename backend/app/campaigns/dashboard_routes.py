"""Dashboard operacional de campanhas."""

import calendar
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    CashbackTransaction,
    Coupon,
    CouponRedemption,
    CouponStatusEnum,
    CouponTypeEnum,
    Drawing,
    DrawingStatusEnum,
)
from app.db import SessionLocal
from app.models import Cliente, Pet
from app.vendas_models import Venda as VendaModel


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _mes_dia(value) -> str | None:
    if not hasattr(value, "month") or not hasattr(value, "day"):
        return None
    return f"{value.month:02d}-{value.day:02d}"


@router.get("/dashboard")
def dashboard_campanhas(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Resumo do dia de campanhas, alertas e proximos eventos."""
    _, tenant_id = user_and_tenant
    hoje = date.today()
    hoje_mm_dd = f"{hoje.month:02d}-{hoje.day:02d}"

    cupons_hoje = (
        db.query(sqlfunc.count(Coupon.id))
        .filter(
            Coupon.tenant_id == tenant_id,
            sqlfunc.date(Coupon.created_at) == hoje,
        )
        .scalar()
    ) or 0

    cupons_usados_hoje = (
        db.query(sqlfunc.count(CouponRedemption.id))
        .filter(
            CouponRedemption.tenant_id == tenant_id,
            sqlfunc.date(CouponRedemption.redeemed_at) == hoje,
        )
        .scalar()
    ) or 0

    cupons_expirados_hoje = (
        db.query(sqlfunc.count(Coupon.id))
        .filter(
            Coupon.tenant_id == tenant_id,
            sqlfunc.date(Coupon.valid_until) == hoje,
        )
        .scalar()
    ) or 0

    cupons_ativos_total = (
        db.query(sqlfunc.count(Coupon.id))
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.status == CouponStatusEnum.active,
        )
        .scalar()
    ) or 0

    saldo_passivo = float(
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(CashbackTransaction.tenant_id == tenant_id)
        .scalar()
        or 0
    )

    todos_clientes = []
    aniversarios_clientes = []
    try:
        todos_clientes = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.data_nascimento.isnot(None),
            )
            .all()
        )
        aniversarios_clientes = [
            {
                "id": cliente.id,
                "nome": cliente.nome,
                "tipo": "cliente",
                "idade": hoje.year - cliente.data_nascimento.year,
            }
            for cliente in todos_clientes
            if cliente.data_nascimento
            and _mes_dia(cliente.data_nascimento) == hoje_mm_dd
        ]
    except Exception:
        pass

    todos_pets = []
    aniversarios_pets = []
    try:
        todos_pets = (
            db.query(Pet)
            .filter(
                Pet.tenant_id == tenant_id,
                Pet.data_nascimento.isnot(None),
            )
            .all()
        )
        aniversarios_pets = [
            {
                "id": pet.id,
                "nome": pet.nome,
                "tipo": "pet",
                "dono_id": pet.cliente_id,
            }
            for pet in todos_pets
            if pet.data_nascimento and _mes_dia(pet.data_nascimento) == hoje_mm_dd
        ]
    except Exception:
        pass

    campanhas_list = (
        db.query(Campaign.id, Campaign.name)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.status == CampaignStatusEnum.active,
        )
        .all()
    )
    campanhas_ativas = {
        "total": len(campanhas_list),
        "nomes": [campanha.name for campanha in campanhas_list],
    }

    amanha = hoje + timedelta(days=1)
    amanha_mm_dd = f"{amanha.month:02d}-{amanha.day:02d}"
    aniversarios_amanha = []
    try:
        aniversarios_amanha.extend(
            {"nome": cliente.nome, "tipo": "cliente"}
            for cliente in todos_clientes
            if cliente.data_nascimento
            and _mes_dia(cliente.data_nascimento) == amanha_mm_dd
        )
        aniversarios_amanha.extend(
            {"nome": pet.nome, "tipo": "pet"}
            for pet in todos_pets
            if pet.data_nascimento and _mes_dia(pet.data_nascimento) == amanha_mm_dd
        )
    except Exception:
        pass

    inativos_30d = 0
    inativos_60d = 0
    novos_inativos_hoje = 0
    try:
        corte_30 = datetime.combine(hoje - timedelta(days=30), datetime.min.time())
        corte_60 = datetime.combine(hoje - timedelta(days=60), datetime.min.time())

        ativos_30d_ids = set(
            row[0]
            for row in db.query(VendaModel.cliente_id)
            .filter(
                VendaModel.tenant_id == tenant_id,
                VendaModel.cliente_id.isnot(None),
                VendaModel.status == "finalizada",
                VendaModel.data_venda >= corte_30,
            )
            .distinct()
            .all()
        )
        ativos_60d_ids = set(
            row[0]
            for row in db.query(VendaModel.cliente_id)
            .filter(
                VendaModel.tenant_id == tenant_id,
                VendaModel.cliente_id.isnot(None),
                VendaModel.status == "finalizada",
                VendaModel.data_venda >= corte_60,
            )
            .distinct()
            .all()
        )
        todos_com_venda_ids = set(
            row[0]
            for row in db.query(VendaModel.cliente_id)
            .filter(
                VendaModel.tenant_id == tenant_id,
                VendaModel.cliente_id.isnot(None),
                VendaModel.status == "finalizada",
            )
            .distinct()
            .all()
        )
        inativos_30d = len(todos_com_venda_ids - ativos_30d_ids)
        inativos_60d = len(todos_com_venda_ids - ativos_60d_ids)

        corte_31 = datetime.combine(hoje - timedelta(days=31), datetime.min.time())
        ultimas_compras_subq = (
            db.query(
                VendaModel.cliente_id,
                sqlfunc.max(VendaModel.data_venda).label("ultima_compra"),
            )
            .filter(
                VendaModel.tenant_id == tenant_id,
                VendaModel.cliente_id.isnot(None),
                VendaModel.status == "finalizada",
            )
            .group_by(VendaModel.cliente_id)
            .subquery()
        )
        novos_inativos_hoje = (
            db.query(sqlfunc.count())
            .select_from(ultimas_compras_subq)
            .filter(
                ultimas_compras_subq.c.ultima_compra >= corte_31,
                ultimas_compras_subq.c.ultima_compra < corte_30,
            )
            .scalar()
        ) or 0
    except Exception:
        novos_inativos_hoje = 0

    sorteios_pendentes = []
    try:
        sorteios_pendentes_query = (
            db.query(Drawing)
            .filter(
                Drawing.tenant_id == tenant_id,
                Drawing.status != DrawingStatusEnum.done,
            )
            .order_by(Drawing.draw_date.asc().nullsfirst())
            .limit(10)
            .all()
        )
        sorteios_pendentes = [
            {
                "id": sorteio.id,
                "name": sorteio.name,
                "status": sorteio.status.value,
                "draw_date": sorteio.draw_date.isoformat()
                if sorteio.draw_date
                else None,
            }
            for sorteio in sorteios_pendentes_query
        ]
    except Exception:
        pass

    sorteios_semana = []
    try:
        semana = hoje + timedelta(days=7)
        sorteios_semana_query = (
            db.query(Drawing)
            .filter(
                Drawing.tenant_id == tenant_id,
                Drawing.draw_date >= datetime.combine(hoje, datetime.min.time()),
                Drawing.draw_date <= datetime.combine(semana, datetime.max.time()),
                Drawing.status != DrawingStatusEnum.done,
            )
            .order_by(Drawing.draw_date.asc())
            .limit(5)
            .all()
        )
        sorteios_semana = [
            {
                "id": sorteio.id,
                "name": sorteio.name,
                "draw_date": sorteio.draw_date.isoformat()
                if sorteio.draw_date
                else None,
            }
            for sorteio in sorteios_semana_query
        ]
    except Exception:
        pass

    brindes_pendentes = []
    try:
        brindes_query = (
            db.query(Coupon)
            .filter(
                Coupon.tenant_id == tenant_id,
                Coupon.coupon_type == CouponTypeEnum.gift,
                Coupon.status == CouponStatusEnum.active,
                Coupon.meta["tipo_premio"].astext == "mensagem",
            )
            .order_by(Coupon.id.desc())
            .all()
        )
        cliente_ids = [
            brinde.customer_id for brinde in brindes_query if brinde.customer_id
        ]
        clientes_brindes = {}
        if cliente_ids:
            clientes_brindes = {
                cliente.id: cliente.nome
                for cliente in db.query(Cliente)
                .filter(Cliente.id.in_(cliente_ids))
                .all()
            }
        brindes_pendentes = [
            {
                "code": brinde.code,
                "customer_id": brinde.customer_id,
                "nome_cliente": clientes_brindes.get(
                    brinde.customer_id, f"#{brinde.customer_id}"
                ),
                "mensagem": brinde.meta.get("mensagem", "") if brinde.meta else "",
                "retirar_de": brinde.meta.get("retirar_de") if brinde.meta else None,
                "retirar_ate": brinde.meta.get("retirar_ate") if brinde.meta else None,
                "categoria": brinde.meta.get("categoria", "") if brinde.meta else "",
                "periodo": brinde.meta.get("periodo", "") if brinde.meta else "",
            }
            for brinde in brindes_query
        ]
    except Exception:
        pass

    _, ultimo_dia = calendar.monthrange(hoje.year, hoje.month)
    fim_mes = date(hoje.year, hoje.month, ultimo_dia)
    dias_ate_fim_mes = (fim_mes - hoje).days

    return {
        "hoje": hoje.isoformat(),
        "campanhas_ativas": campanhas_ativas,
        "cupons_emitidos_hoje": cupons_hoje,
        "cupons_usados_hoje": cupons_usados_hoje,
        "cupons_expirados_hoje": cupons_expirados_hoje,
        "cupons_ativos_total": cupons_ativos_total,
        "saldo_passivo_cashback": round(saldo_passivo, 2),
        "aniversarios_hoje": aniversarios_clientes + aniversarios_pets,
        "total_aniversarios": len(aniversarios_clientes) + len(aniversarios_pets),
        "alertas": {
            "inativos_30d": inativos_30d,
            "inativos_60d": inativos_60d,
            "novos_inativos_hoje": novos_inativos_hoje,
            "sorteios_pendentes": sorteios_pendentes,
            "total_sorteios_pendentes": len(sorteios_pendentes),
            "brindes_pendentes": brindes_pendentes,
            "total_brindes_pendentes": len(brindes_pendentes),
        },
        "proximos_eventos": {
            "aniversarios_amanha": aniversarios_amanha,
            "total_aniversarios_amanha": len(aniversarios_amanha),
            "sorteios_esta_semana": sorteios_semana,
            "dias_ate_fim_mes": dias_ate_fim_mes,
        },
    }
