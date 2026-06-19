"""
Rotas de engajamento das campanhas.

Sub-router incluido por ``app.campaigns.routes`` sob o prefixo ``/campanhas``.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    CampaignTypeEnum,
    Coupon,
    CouponChannelEnum,
    CouponStatusEnum,
    CouponTypeEnum,
    CustomerRankHistory,
    RankLevelEnum,
)
from app.db import SessionLocal
from app.utils.logger import logger

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Retencao Dinamica - CRUD dedicado (filtra por campaign_type = inactivity)
# ---------------------------------------------------------------------------


class RetencaoBody(BaseModel):
    name: str
    inactivity_days: int = 30
    coupon_type: str = "percent"
    coupon_value: float = 10.0
    coupon_valid_days: int = 7
    coupon_channel: str = "all"
    notification_message: str = ""
    priority: int = 50


def _retencao_to_dict(c: Campaign) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "status": c.status.value,
        "priority": c.priority,
        "params": c.params or {},
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/retencao")
def listar_retencao(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as campanhas de retenção (inatividade) do tenant."""
    _, tenant_id = user_and_tenant
    campanhas = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.inactivity,
            Campaign.status.in_([CampaignStatusEnum.active, CampaignStatusEnum.paused]),
        )
        .order_by(Campaign.priority)
        .all()
    )
    return [_retencao_to_dict(c) for c in campanhas]


@router.post("/retencao", status_code=201)
def criar_retencao(
    body: RetencaoBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova regra de retenção por inatividade."""
    _, tenant_id = user_and_tenant
    campaign = Campaign(
        tenant_id=tenant_id,
        name=body.name.strip(),
        campaign_type=CampaignTypeEnum.inactivity,
        status=CampaignStatusEnum.active,
        priority=max(0, min(999, body.priority)),
        params={
            "inactivity_days": body.inactivity_days,
            "coupon_type": body.coupon_type,
            "coupon_value": body.coupon_value,
            "coupon_valid_days": body.coupon_valid_days,
            "coupon_channel": body.coupon_channel,
            "notification_message": body.notification_message,
        },
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _retencao_to_dict(campaign)


@router.put("/retencao/{campaign_id}")
def editar_retencao(
    campaign_id: int,
    body: RetencaoBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Edita nome e params de uma regra de retenção."""
    _, tenant_id = user_and_tenant
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.inactivity,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(404, detail="Regra de retenção não encontrada.")
    campaign.name = body.name.strip()
    campaign.priority = max(0, min(999, body.priority))
    campaign.params = {
        "inactivity_days": body.inactivity_days,
        "coupon_type": body.coupon_type,
        "coupon_value": body.coupon_value,
        "coupon_valid_days": body.coupon_valid_days,
        "coupon_channel": body.coupon_channel,
        "notification_message": body.notification_message,
    }
    db.commit()
    db.refresh(campaign)
    return _retencao_to_dict(campaign)


@router.delete("/retencao/{campaign_id}", status_code=204)
def deletar_retencao(
    campaign_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Arquiva (soft-delete) uma regra de retenção."""
    _, tenant_id = user_and_tenant
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.inactivity,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(404, detail="Regra de retenção não encontrada.")
    campaign.status = CampaignStatusEnum.archived
    db.commit()
    return


# ---------------------------------------------------------------------------
# Destaque Mensal
# ---------------------------------------------------------------------------


@router.get("/destaque-mensal")
def calcular_destaque_mensal(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Calcula os clientes em destaque do mês anterior:
    - Maior gasto total
    - Maior número de compras
    - Mais meses com compras (fidelidade)

    Anti-duplicidade: cada cliente pode vencer apenas 1 categoria.
    Retorna os 3 vencedores + a lista dos top 5 de cada categoria.
    """
    from app.models import Cliente, User
    from app.vendas_models import Venda
    from datetime import timedelta

    _, tenant_id = user_and_tenant
    now = datetime.now(timezone.utc)
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_day_last_month = (first_day_this_month - timedelta(days=1)).replace(day=1)
    period = first_day_last_month.strftime("%Y-%m")

    agg = (
        db.query(
            Venda.cliente_id,
            sqlfunc.sum(Venda.total).label("total_spent"),
            sqlfunc.count(Venda.id).label("total_purchases"),
        )
        .join(User, User.id == Venda.user_id)
        .filter(
            User.tenant_id == tenant_id,
            Venda.status == "finalizada",
            Venda.cliente_id.isnot(None),
            Venda.data_finalizacao >= first_day_last_month,
            Venda.data_finalizacao < first_day_this_month,
        )
        .group_by(Venda.cliente_id)
        .all()
    )

    # Enriquecer com nome do cliente
    clientes_map = {}
    if agg:
        ids = [r.cliente_id for r in agg]
        for c in db.query(Cliente).filter(Cliente.id.in_(ids)).all():
            clientes_map[c.id] = c.nome

    rows = [
        {
            "customer_id": r.cliente_id,
            "nome": clientes_map.get(r.cliente_id, f"Cliente #{r.cliente_id}"),
            "total_spent": float(r.total_spent or 0),
            "total_purchases": r.total_purchases or 0,
        }
        for r in agg
    ]

    # Top 5 por categoria (antes de aplicar anti-duplicidade)
    by_spent = sorted(rows, key=lambda x: x["total_spent"], reverse=True)[:5]
    by_purchases = sorted(rows, key=lambda x: x["total_purchases"], reverse=True)[:5]

    # Anti-duplicidade: vencedor de cada categoria não pode ganhar outra.
    # Se o 1º de uma categoria já ganhou em outra, usa o 2º colocado.
    vencedores = {}
    usados = set()
    desempate_info = []  # registra quando um candidato foi pulado por desempate

    for categoria, lista in [("maior_gasto", by_spent), ("mais_compras", by_purchases)]:
        for i, candidato in enumerate(lista):
            if candidato["customer_id"] not in usados:
                vencedores[categoria] = candidato
                usados.add(candidato["customer_id"])
                # Se não foi o 1º colocado, houve desempate
                if i > 0:
                    desempate_info.append(
                        {
                            "categoria": categoria,
                            "pulado": lista[0],
                            "eleito": candidato,
                            "posicao_eleito": i + 1,  # 2, 3, ...
                            "motivo": "1º colocado já venceu em outra categoria",
                        }
                    )
                break

    return {
        "periodo": period,
        "vencedores": vencedores,
        "top5_maior_gasto": by_spent,
        "top5_mais_compras": by_purchases,
        "total_clientes_ativos": len(rows),
        "desempate_info": desempate_info,  # lista vazia se não houve desempate
    }


class EnviarDestaqueBody(BaseModel):
    vencedores: dict  # cada entrada: { "customer_id": X, "tipo_premio": T, "coupon_value": V, ... }
    # Fallbacks globais (mantidos por compatibilidade)
    tipo_premio: str = "cupom"  # "cupom" | "mensagem"
    coupon_value: float = 50.0
    coupon_valid_days: int = 10
    mensagem_brinde: Optional[str] = None
    retirar_de: Optional[str] = None  # data string YYYY-MM-DD
    retirar_ate: Optional[str] = None  # data string YYYY-MM-DD
    mensagem_personalizada: Optional[str] = None


@router.post("/destaque-mensal/enviar")
def enviar_destaque_mensal(
    body: EnviarDestaqueBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera cupons OU registra brindes de loja para os vencedores do destaque mensal.
    Suporta prêmios individuais por vencedor: cada entrada em vencedores pode ter
    tipo_premio, coupon_value, coupon_valid_days, mensagem próprios.
    Retorna resultados unificados por vencedor.
    """
    from app.campaigns.coupon_service import create_coupon

    _, tenant_id = user_and_tenant

    now = datetime.now(timezone.utc)
    first_day_this_month = now.replace(day=1)
    from datetime import timedelta

    last_month = first_day_this_month - timedelta(days=1)
    period = last_month.strftime("%Y-%m")

    resultados = []

    for categoria, info in body.vencedores.items():
        customer_id = info.get("customer_id")
        if not customer_id:
            continue

        # Lê config do vencedor, com fallback nos campos globais do body
        tipo = info.get("tipo_premio") or body.tipo_premio
        val_cupom = float(info.get("coupon_value") or body.coupon_value)
        dias_cupom = int(info.get("coupon_valid_days") or body.coupon_valid_days)
        mensagem = (
            info.get("mensagem")
            or info.get("mensagem_brinde")
            or body.mensagem_brinde
            or ""
        )
        retirar_de = info.get("retirar_de") or body.retirar_de
        retirar_ate = info.get("retirar_ate") or body.retirar_ate

        if tipo == "mensagem":
            # Persistir brinde como Coupon gift para rastreamento no dashboard
            meta_key_brinde = f"destaque:{period}:{categoria}"
            brinde_existente = (
                db.query(Coupon)
                .filter(
                    Coupon.tenant_id == tenant_id,
                    Coupon.customer_id == customer_id,
                    Coupon.meta["destaque_key"].astext == meta_key_brinde,
                )
                .first()
            )
            if not brinde_existente:
                brinde_code = f"BRINDE-{period.replace('-', '')}-{categoria[:3].upper()}-{customer_id}"
                novo_brinde = Coupon(
                    tenant_id=tenant_id,
                    code=brinde_code,
                    coupon_type=CouponTypeEnum.gift,
                    channel=CouponChannelEnum.pdv,
                    customer_id=customer_id,
                    status=CouponStatusEnum.active,
                    meta={
                        "destaque_key": meta_key_brinde,
                        "tipo_premio": "mensagem",
                        "mensagem": mensagem,
                        "retirar_de": retirar_de,
                        "retirar_ate": retirar_ate,
                        "categoria": categoria,
                        "periodo": period,
                    },
                )
                db.add(novo_brinde)
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                ja_existia_brinde = False
            else:
                ja_existia_brinde = True

            resultados.append(
                {
                    "categoria": categoria,
                    "customer_id": customer_id,
                    "tipo_premio": "mensagem",
                    "mensagem": mensagem,
                    "retirar_de": retirar_de,
                    "retirar_ate": retirar_ate,
                    "ja_existia": ja_existia_brinde,
                }
            )
            logger.info(
                "[DestaqueEnviar] Brinde registrado — cliente %s, categoria %s, periodo %s",
                customer_id,
                categoria,
                period,
            )
            continue

        # ── Tipo cupom ──────────────────────────────────────────────────────
        meta_key = f"destaque:{period}:{categoria}"
        already = (
            db.query(Coupon)
            .filter(
                Coupon.tenant_id == tenant_id,
                Coupon.customer_id == customer_id,
                Coupon.meta["destaque_key"].astext == meta_key,
            )
            .first()
        )
        if already:
            resultados.append(
                {
                    "categoria": categoria,
                    "customer_id": customer_id,
                    "tipo_premio": "cupom",
                    "coupon_code": already.code,
                    "coupon_value": float(already.discount_value or 0),
                    "ja_existia": True,
                }
            )
            continue

        try:
            coupon = create_coupon(
                db,
                tenant_id=tenant_id,
                campaign=None,
                customer_id=customer_id,
                coupon_type="fixed",
                discount_value=val_cupom,
                discount_percent=None,
                valid_days=dias_cupom,
                channel="pdv",
                prefix="DEST",
                meta={
                    "destaque_key": meta_key,
                    "categoria": categoria,
                    "periodo": period,
                    "mensagem": mensagem,
                },
            )
            resultados.append(
                {
                    "categoria": categoria,
                    "customer_id": customer_id,
                    "tipo_premio": "cupom",
                    "coupon_code": coupon.code,
                    "coupon_value": val_cupom,
                    "ja_existia": False,
                }
            )
        except Exception as exc:
            logger.warning("[DestaqueEnviar] Erro cliente %s: %s", customer_id, exc)

    db.commit()
    return {"ok": True, "enviados": len(resultados), "resultados": resultados}


# ---------------------------------------------------------------------------
# Seed — criar campanhas padrão para o tenant
# ---------------------------------------------------------------------------


@router.post("/seed")
def seed_campanhas(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria campanhas padrão para o tenant se ainda não existirem.
    Operação idempotente — segura para chamar múltiplas vezes.
    """
    _, tenant_id = user_and_tenant

    from app.campaigns.scheduler import seed_campaigns_for_tenant

    criadas = seed_campaigns_for_tenant(db, tenant_id)

    return {
        "ok": True,
        "campanhas_criadas": criadas,
        "message": f"{criadas} campanha(s) criada(s)"
        if criadas
        else "Todas as campanhas padrão já existem",
    }


# ---------------------------------------------------------------------------
# SPRINT 7 — Envio em lote por nível de ranking
# ---------------------------------------------------------------------------


class EnvioLoteBody(BaseModel):
    nivel: str  # bronze | silver | gold | diamond | platinum | todos
    assunto: str
    mensagem: str  # corpo do e-mail / notificação
    periodo: Optional[str] = None  # YYYY-MM (padrão: mais recente)


@router.post("/ranking/envio-em-lote")
def envio_em_lote(
    body: EnvioLoteBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Enfileira notificações de e-mail para todos os clientes de um nível de ranking.

    As mensagens entram na `notification_queue` e são despachadas pelo
    NotificationSender a cada 5 minutos.
    """
    from app.models import Cliente

    _, tenant_id = user_and_tenant

    # Resolver nível
    nivel_enum = None
    if body.nivel != "todos":
        try:
            nivel_enum = RankLevelEnum(body.nivel)
        except ValueError:
            raise HTTPException(400, detail=f"Nível inválido: {body.nivel}")

    # Descobrir período
    periodo = body.periodo
    if not periodo:
        ultimo = (
            db.query(CustomerRankHistory.period)
            .filter(CustomerRankHistory.tenant_id == tenant_id)
            .order_by(CustomerRankHistory.period.desc())
            .first()
        )
        if not ultimo:
            raise HTTPException(
                400, detail="Nenhum dado de ranking. Execute o recálculo primeiro."
            )
        periodo = ultimo[0]

    # Buscar clientes elegíveis
    q = db.query(CustomerRankHistory).filter(
        CustomerRankHistory.tenant_id == tenant_id,
        CustomerRankHistory.period == periodo,
    )
    if nivel_enum:
        q = q.filter(CustomerRankHistory.rank_level == nivel_enum)
    registros = q.all()

    if not registros:
        return {"ok": True, "enfileirados": 0, "sem_email": 0, "periodo": periodo}

    customer_ids = [r.customer_id for r in registros]
    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.id.in_(customer_ids),
            Cliente.tenant_id == tenant_id,
            Cliente.email.isnot(None),
        )
        .all()
    )
    clientes_map = {c.id: c for c in clientes}

    enfileirados = 0
    sem_email = 0
    for r in registros:
        cliente = clientes_map.get(r.customer_id)
        if not cliente or not cliente.email:
            sem_email += 1
            continue

        from app.campaigns.notification_service import enqueue_email

        idempotency_key = f"lote:{tenant_id}:{periodo}:{body.nivel}:{r.customer_id}:{hash(body.assunto)}"
        if enqueue_email(
            db,
            tenant_id=tenant_id,
            customer_id=r.customer_id,
            subject=body.assunto,
            body=body.mensagem,
            email_address=cliente.email,
            idempotency_key=idempotency_key,
        ):
            enfileirados += 1

    db.commit()
    return {
        "ok": True,
        "enfileirados": enfileirados,
        "sem_email": sem_email,
        "total_clientes": len(registros),
        "periodo": periodo,
    }


# ---------------------------------------------------------------------------
# SPRINT 8 — Unificação Cross-Canal via CPF/Telefone
# ---------------------------------------------------------------------------


class EnvioInativosBody(BaseModel):
    dias_sem_compra: int = 30  # 30 ou 60
    assunto: str
    mensagem: str


@router.post("/notificacoes/inativos")
def envio_escalonado_inativos(
    body: EnvioInativosBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Enfileira e-mails de reativação para todos os clientes sem compra nos últimos N dias.
    As mensagens entram na `notification_queue` e são disparadas pelo NotificationSender
    em lotes de 50 por rodada (BATCH_SIZE).
    """
    from app.models import Cliente
    from app.vendas_models import Venda as VendaModel

    _, tenant_id = user_and_tenant

    if body.dias_sem_compra not in (30, 60, 90):
        raise HTTPException(400, detail="dias_sem_compra deve ser 30, 60 ou 90.")

    corte = datetime.combine(
        date.today() - timedelta(days=body.dias_sem_compra),
        datetime.min.time(),
    )

    # IDs ativos (compraram depois do corte)
    ativos_ids = set(
        r[0]
        for r in db.query(VendaModel.cliente_id)
        .filter(
            VendaModel.tenant_id == tenant_id,
            VendaModel.cliente_id.isnot(None),
            VendaModel.status == "finalizada",
            VendaModel.data_venda >= corte,
        )
        .distinct()
        .all()
    )

    # Todos com pelo menos 1 venda
    todos_ids = set(
        r[0]
        for r in db.query(VendaModel.cliente_id)
        .filter(
            VendaModel.tenant_id == tenant_id,
            VendaModel.cliente_id.isnot(None),
            VendaModel.status == "finalizada",
        )
        .distinct()
        .all()
    )

    inativos_ids = list(todos_ids - ativos_ids)
    if not inativos_ids:
        return {"ok": True, "enfileirados": 0, "sem_email": 0, "total_inativos": 0}

    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.id.in_(inativos_ids),
            Cliente.tenant_id == tenant_id,
            Cliente.email.isnot(None),
        )
        .all()
    )

    enfileirados = 0
    sem_email = len(inativos_ids) - len(clientes)

    for cliente in clientes:
        idempotency_key = f"inativos:{tenant_id}:{body.dias_sem_compra}:{cliente.id}:{date.today().isoformat()}"
        from app.campaigns.notification_service import enqueue_email

        if enqueue_email(
            db,
            tenant_id=tenant_id,
            customer_id=cliente.id,
            subject=body.assunto,
            body=body.mensagem,
            email_address=cliente.email,
            idempotency_key=idempotency_key,
        ):
            enfileirados += 1

    db.commit()
    return {
        "ok": True,
        "enfileirados": enfileirados,
        "sem_email": sem_email,
        "total_inativos": len(inativos_ids),
        "dias_sem_compra": body.dias_sem_compra,
    }
