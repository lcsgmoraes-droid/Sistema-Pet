"""
Rotas da API — Campanhas
=========================

Prefixo: /campanhas
Auth: requer JWT multi-tenant padrão do projeto

Rotas implementadas:
  GET  /campanhas/health                       → healthcheck
  GET  /campanhas                              → lista campanhas do tenant
  POST /campanhas/{id}/pausar                  → pausa/resume campanha
  PUT  /campanhas/{id}/parametros              → atualiza parâmetros da campanha
  GET  /campanhas/cupons                       → lista cupons do tenant
  POST /campanhas/cupons/manual                → cria cupom manual
  POST /campanhas/cupons/{code}/resgatar       → valida e resgata cupom no PDV
  GET  /campanhas/clientes/{customer_id}/saldo → saldo cashback + carimbos + rank do cliente
  POST /campanhas/carimbos/manual              → lança carimbo manual para um cliente
  GET  /campanhas/ranking                      → lista clientes com nível de ranking atual
  POST /campanhas/ranking/recalcular           → força recálculo de ranking para todos os clientes
  POST /campanhas/ranking/envio-em-lote        → enfileira e-mails para um nível de ranking
  GET  /campanhas/dashboard                    → alertas do dia e resumo de campanhas
  GET  /campanhas/relatorio                    → histórico de cashback (créditos e resgates)
  POST /campanhas/seed                         → cria campanhas padrão para o tenant (admin)
  POST /campanhas                              → cria campanha personalizada
  DELETE /campanhas/{id}                       → arquiva campanha personalizada
  POST /campanhas/cashback/manual              → ajuste manual de cashback para um cliente (Gestor de Benefícios)
  GET  /campanhas/destaque-mensal              → calcula vencedores do mês (maior gasto, mais compras)
  POST /campanhas/destaque-mensal/enviar       → gera cupons para os vencedores do destaque mensal
  GET  /campanhas/sorteios                     → lista sorteios do tenant
  POST /campanhas/sorteios                     → cria sorteio
  PUT  /campanhas/sorteios/{id}                → edita sorteio
  POST /campanhas/sorteios/{id}/inscrever      → inscreve clientes elegíveis
  POST /campanhas/sorteios/{id}/executar       → executa sorteio com seed auditável
  GET  /campanhas/sorteios/{id}/resultado      → retorna ganhador e participantes
  DELETE /campanhas/sorteios/{id}              → cancela sorteio
  GET  /campanhas/unificacao/sugestoes         → sugestões de unificação por CPF/telefone
  POST /campanhas/unificacao/confirmar         → confirma merge de dois clientes
  DELETE /campanhas/unificacao/{merge_id}      → desfaz merge
"""

import logging
import json as _json
import uuid as _uuid
from datetime import datetime, date, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc, or_ as sql_or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.models import Cliente
from app.produtos_models import (
    CampanhaValidadeAutomatica,
    CampanhaValidadeExclusao,
    Produto,
    ProdutoLote,
)
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    Coupon,
    CouponRedemption,
    CouponStatusEnum,
    CouponTypeEnum,
    CouponChannelEnum,
    LoyaltyStamp,
    CashbackTransaction,
    CashbackSourceTypeEnum,
    CustomerRankHistory,
    RankLevelEnum,
    Drawing,
    DrawingEntry,
    DrawingStatusEnum,
    NotificationQueue,
    NotificationChannelEnum,
    NotificationStatusEnum,
    CustomerMergeLog,
)
from app.campaigns.models import CampaignTypeEnum, CampaignExecution, CampaignEventQueue, EventStatusEnum
from app.campaigns.coupon_service import preview_coupon_redemption
from app.services.validade_campanha_service import (
    contar_exclusoes_ativas,
    obter_campanha_validade_config,
    serializar_campanha_validade_config,
)
from app.campaigns.loyalty_service import (
    build_consumed_loyalty_stamp_ids,
    get_loyalty_balance_for_campaign,
    revoke_loyalty_reward_by_coupon,
    summarize_loyalty_balances_for_customer,
)
from app.db import SessionLocal

logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/campanhas", tags=["Campanhas"])


def _serializar_exclusao_validade(exclusao: CampanhaValidadeExclusao) -> dict:
    return {
        "id": exclusao.id,
        "produto_id": exclusao.produto_id,
        "lote_id": exclusao.lote_id,
        "ativo": bool(exclusao.ativo),
        "motivo": exclusao.motivo,
        "observacao": exclusao.observacao,
        "created_at": exclusao.created_at.isoformat() if exclusao.created_at else None,
    }


class CampanhaValidadeConfigBody(BaseModel):
    ativo: bool = False
    aplicar_app: bool = True
    aplicar_ecommerce: bool = True
    desconto_60_dias: float = 10
    desconto_30_dias: float = 20
    desconto_7_dias: float = 35
    rotulo_publico: Optional[str] = "Validade proxima"
    mensagem_publica: Optional[str] = "Oferta por lote com quantidade limitada."


class CampanhaValidadeExclusaoBody(BaseModel):
    produto_id: int
    lote_id: Optional[int] = None
    motivo: Optional[str] = None
    observacao: Optional[str] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
def campaigns_health():
    """Healthcheck do módulo de campanhas."""
    return {"status": "ok", "module": "campaigns"}


@router.get("/validade/config")
def obter_config_campanha_validade(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    config = obter_campanha_validade_config(db, tenant_id)
    total_exclusoes = contar_exclusoes_ativas(db, tenant_id)
    return serializar_campanha_validade_config(
        config,
        total_exclusoes=total_exclusoes,
    )


@router.put("/validade/config")
def salvar_config_campanha_validade(
    body: CampanhaValidadeConfigBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    config = obter_campanha_validade_config(db, tenant_id)
    if not config:
        config = CampanhaValidadeAutomatica(tenant_id=tenant_id)
        db.add(config)

    config.ativo = bool(body.ativo)
    config.aplicar_app = bool(body.aplicar_app)
    config.aplicar_ecommerce = bool(body.aplicar_ecommerce)
    config.desconto_60_dias = min(max(float(body.desconto_60_dias or 0), 0.0), 95.0)
    config.desconto_30_dias = min(max(float(body.desconto_30_dias or 0), 0.0), 95.0)
    config.desconto_7_dias = min(max(float(body.desconto_7_dias or 0), 0.0), 95.0)
    config.rotulo_publico = (body.rotulo_publico or "Validade proxima").strip() or "Validade proxima"
    config.mensagem_publica = (
        (body.mensagem_publica or "Oferta por lote com quantidade limitada.").strip()
        or "Oferta por lote com quantidade limitada."
    )

    db.commit()
    db.refresh(config)

    return serializar_campanha_validade_config(
        config,
        total_exclusoes=contar_exclusoes_ativas(db, tenant_id),
    )


@router.post("/validade/exclusoes")
def criar_exclusao_campanha_validade(
    body: CampanhaValidadeExclusaoBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant

    produto = (
        db.query(Produto)
        .filter(Produto.id == body.produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    if body.lote_id:
        lote = (
            db.query(ProdutoLote)
            .filter(
                ProdutoLote.id == body.lote_id,
                ProdutoLote.produto_id == body.produto_id,
                ProdutoLote.tenant_id == tenant_id,
            )
            .first()
        )
        if not lote:
            raise HTTPException(status_code=404, detail="Lote nao encontrado")

    query_existente = db.query(CampanhaValidadeExclusao).filter(
        CampanhaValidadeExclusao.tenant_id == tenant_id,
        CampanhaValidadeExclusao.produto_id == body.produto_id,
        CampanhaValidadeExclusao.ativo.is_(True),
    )
    if body.lote_id:
        query_existente = query_existente.filter(
            CampanhaValidadeExclusao.lote_id == body.lote_id
        )
    else:
        query_existente = query_existente.filter(
            CampanhaValidadeExclusao.lote_id.is_(None)
        )

    existente = query_existente.first()
    if existente:
        return _serializar_exclusao_validade(existente)

    exclusao = CampanhaValidadeExclusao(
        tenant_id=tenant_id,
        produto_id=body.produto_id,
        lote_id=body.lote_id,
        motivo=(body.motivo or "Opt-out manual").strip() or "Opt-out manual",
        observacao=(body.observacao or "").strip() or None,
        ativo=True,
    )
    db.add(exclusao)
    db.commit()
    db.refresh(exclusao)

    return _serializar_exclusao_validade(exclusao)


@router.delete("/validade/exclusoes/{exclusao_id}")
def remover_exclusao_campanha_validade(
    exclusao_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    exclusao = (
        db.query(CampanhaValidadeExclusao)
        .filter(
            CampanhaValidadeExclusao.id == exclusao_id,
            CampanhaValidadeExclusao.tenant_id == tenant_id,
            CampanhaValidadeExclusao.ativo.is_(True),
        )
        .first()
    )
    if not exclusao:
        raise HTTPException(status_code=404, detail="Exclusao nao encontrada")

    exclusao.ativo = False
    db.commit()

    return {"ok": True, "id": exclusao_id}


# ---------------------------------------------------------------------------
# Campanhas — listagem e gestão
# ---------------------------------------------------------------------------

@router.get("")
def listar_campanhas(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as campanhas ativas e pausadas do tenant."""
    _, tenant_id = user_and_tenant
    campanhas = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.status.in_([CampaignStatusEnum.active, CampaignStatusEnum.paused]),
        )
        .order_by(Campaign.priority)
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "campaign_type": c.campaign_type.value,
            "status": c.status.value,
            "priority": c.priority,
            "params": c.params,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in campanhas
    ]


@router.post("/{campanha_id}/pausar")
def pausar_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Alterna o status da campanha entre active ↔ paused."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(Campaign.id == campanha_id, Campaign.tenant_id == tenant_id)
        .first()
    )
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    if campanha.status == CampaignStatusEnum.active:
        campanha.status = CampaignStatusEnum.paused
        novo_status = "paused"
    else:
        campanha.status = CampaignStatusEnum.active
        novo_status = "active"

    db.commit()
    return {"id": campanha_id, "status": novo_status}


# ---------------------------------------------------------------------------
# Campanhas — atualizar parâmetros
# ---------------------------------------------------------------------------

class AtualizarParametrosBody(BaseModel):
    params: dict
    name: Optional[str] = None


@router.put("/{campanha_id}/parametros")
def atualizar_parametros(
    campanha_id: int,
    body: AtualizarParametrosBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza os parâmetros e/ou nome de uma campanha."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(Campaign.id == campanha_id, Campaign.tenant_id == tenant_id)
        .first()
    )
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    campanha.params = {**(campanha.params or {}), **body.params}
    if body.name:
        campanha.name = body.name
    db.commit()
    return {
        "id": campanha.id,
        "name": campanha.name,
        "params": campanha.params,
    }


# ---------------------------------------------------------------------------
# Cupons — listagem
# ---------------------------------------------------------------------------

@router.get("/cupons")
def listar_cupons(
    status: Optional[str] = Query(None, description="Filtrar por status: active, used, expired"),
    customer_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    busca: Optional[str] = Query(None, description="Busca por código ou nome do cliente"),
    data_inicio: Optional[str] = Query(None, description="Data de criação inicial YYYY-MM-DD"),
    data_fim: Optional[str] = Query(None, description="Data de criação final YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista cupons do tenant com filtros opcionais."""
    from app.models import Cliente
    from app.campaigns.models import Campaign as CampaignModel

    _, tenant_id = user_and_tenant
    q = db.query(Coupon).filter(Coupon.tenant_id == tenant_id)
    if status:
        try:
            q = q.filter(Coupon.status == CouponStatusEnum(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")
    if customer_id:
        q = q.filter(Coupon.customer_id == customer_id)
    if campaign_id:
        q = q.filter(Coupon.campaign_id == campaign_id)
    if data_inicio:
        try:
            q = q.filter(Coupon.created_at >= datetime.fromisoformat(data_inicio))
        except ValueError:
            pass
    if data_fim:
        try:
            from datetime import timedelta as _td
            q = q.filter(Coupon.created_at < datetime.fromisoformat(data_fim) + _td(days=1))
        except ValueError:
            pass
    if busca:
        busca_like = f"%{busca}%"
        matching_ids = [
            c.id for c in db.query(Cliente.id).filter(
                Cliente.tenant_id == tenant_id,
                Cliente.nome.ilike(busca_like),
            ).all()
        ]
        if matching_ids:
            q = q.filter(
                (Coupon.code.ilike(busca_like)) | (Coupon.customer_id.in_(matching_ids))
            )
        else:
            q = q.filter(Coupon.code.ilike(busca_like))

    cupons = q.order_by(Coupon.id.desc()).limit(300).all()

    # Enriquecer com nome do cliente
    cids = [c.customer_id for c in cupons if c.customer_id]
    clientes_map: dict = {}
    if cids:
        for cl in db.query(Cliente).filter(Cliente.id.in_(cids)).all():
            clientes_map[cl.id] = cl.nome

    # Enriquecer com nome da campanha
    camp_ids = [c.campaign_id for c in cupons if c.campaign_id]
    campanhas_map: dict = {}
    if camp_ids:
        for camp in db.query(CampaignModel).filter(CampaignModel.id.in_(camp_ids)).all():
            campanhas_map[camp.id] = camp.name

    # Enriquecer com data de uso (redeemed_at) de cada cupom
    coupon_ids = [c.id for c in cupons]
    redeemed_at_map: dict = {}
    if coupon_ids:
        redemptions = (
            db.query(CouponRedemption.coupon_id, CouponRedemption.redeemed_at)
            .filter(CouponRedemption.coupon_id.in_(coupon_ids))
            .all()
        )
        for r in redemptions:
            redeemed_at_map[r.coupon_id] = r.redeemed_at

    return [
        {
            "id": c.id,
            "code": c.code,
            "coupon_type": c.coupon_type.value,
            "discount_value": float(c.discount_value) if c.discount_value else None,
            "discount_percent": float(c.discount_percent) if c.discount_percent else None,
            "channel": c.channel.value,
            "status": c.status.value,
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "min_purchase_value": float(c.min_purchase_value) if c.min_purchase_value else None,
            "customer_id": c.customer_id,
            "nome_cliente": clientes_map.get(c.customer_id),
            "campaign_id": c.campaign_id,
            "nome_campanha": campanhas_map.get(c.campaign_id),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "used_at": redeemed_at_map[c.id].isoformat() if c.id in redeemed_at_map else None,
            "meta": c.meta,
        }
        for c in cupons
    ]


# ---------------------------------------------------------------------------
# Cupons — criar cupom manual
# ---------------------------------------------------------------------------

class CriarCupomManualBody(BaseModel):
    coupon_type: str  # "percent" | "fixed" | "gift"
    discount_value: Optional[float] = None
    discount_percent: Optional[float] = None
    channel: str = "all"  # "pdv" | "app" | "ecommerce" | "all"
    valid_until: Optional[str] = None  # ISO date string "YYYY-MM-DD"
    min_purchase_value: Optional[float] = None
    customer_id: Optional[int] = None
    descricao: Optional[str] = None


@router.post("/cupons/manual")
def criar_cupom_manual(
    body: CriarCupomManualBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um cupom manualmente para casos especiais."""
    user_id, tenant_id = user_and_tenant

    try:
        tipo = CouponTypeEnum(body.coupon_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"coupon_type inválido: {body.coupon_type}")

    try:
        canal = CouponChannelEnum(body.channel)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"channel inválido: {body.channel}")

    if tipo == CouponTypeEnum.percent and not body.discount_percent:
        raise HTTPException(status_code=400, detail="discount_percent é obrigatório para cupom de %")
    if tipo == CouponTypeEnum.fixed and not body.discount_value:
        raise HTTPException(status_code=400, detail="discount_value é obrigatório para cupom de valor fixo")

    # Gerar código único
    code = f"MAN-{_uuid.uuid4().hex[:8].upper()}"

    valid_until = None
    if body.valid_until:
        try:
            valid_until = datetime.fromisoformat(body.valid_until).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="valid_until deve ser YYYY-MM-DD")

    cupom = Coupon(
        tenant_id=tenant_id,
        code=code,
        coupon_type=tipo,
        discount_value=body.discount_value,
        discount_percent=body.discount_percent,
        channel=canal,
        valid_until=valid_until,
        min_purchase_value=body.min_purchase_value,
        customer_id=body.customer_id,
        campaign_id=None,
        meta={"descricao": body.descricao or "Cupom manual", "criado_por": "manual"},
    )
    db.add(cupom)
    db.commit()
    db.refresh(cupom)

    return {
        "id": cupom.id,
        "code": cupom.code,
        "coupon_type": cupom.coupon_type.value,
        "discount_value": float(cupom.discount_value) if cupom.discount_value else None,
        "discount_percent": float(cupom.discount_percent) if cupom.discount_percent else None,
        "channel": cupom.channel.value,
        "status": cupom.status.value,
        "valid_until": cupom.valid_until.isoformat() if cupom.valid_until else None,
        "customer_id": cupom.customer_id,
    }


# ---------------------------------------------------------------------------
# Cupons — resgate no PDV
# ---------------------------------------------------------------------------

class ResgateBody(BaseModel):
    venda_total: Optional[float] = None
    customer_id: Optional[int] = None


@router.post("/cupons/{code}/resgatar")
def resgatar_cupom(
    code: str,
    body: ResgateBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Valida um cupom no PDV e retorna a previa do desconto.

    O consumo efetivo acontece apenas no fechamento atomico da venda.
    """
    _, tenant_id = user_and_tenant
    preview = preview_coupon_redemption(
        db,
        tenant_id=tenant_id,
        code=code,
        venda_total=body.venda_total or 0.0,
        customer_id=body.customer_id,
    )
    logger.info(
        "[Campanhas] Cupom validado em previa: code=%s tenant=%s discount=R$%.2f",
        preview["code"],
        tenant_id,
        float(preview["discount_applied"] or 0),
    )
    return preview


# ---------------------------------------------------------------------------
# Clientes — saldo cashback, carimbos e ranking
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Busca de clientes (para o Gestor de Benefícios — sem exigir clientes.visualizar)
# ---------------------------------------------------------------------------

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
            Cliente.ativo == True,
            (
                Cliente.nome.ilike(termo)
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
                Cliente.ativo == True,
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
                {"id": c.id, "nome": c.nome, "cpf": c.cpf, "telefone": c.telefone or c.celular, "detalhe": f"{total} carimbo(s)"}
                for c, total in rows
            ]
        }

    elif tipo == "cashback":
        subq = (
            db.query(
                CashbackTransaction.customer_id,
                sqlfunc.sum(CashbackTransaction.amount).label("saldo"),
            )
            .filter(CashbackTransaction.tenant_id == tenant_id)
            .group_by(CashbackTransaction.customer_id)
            .having(sqlfunc.sum(CashbackTransaction.amount) > 0)
            .subquery()
        )
        rows = (
            db.query(Cliente, subq.c.saldo)
            .join(subq, Cliente.id == subq.c.customer_id)
            .filter(Cliente.tenant_id == tenant_id, Cliente.ativo == True)
            .order_by(subq.c.saldo.desc())
            .limit(limit)
            .all()
        )
        return {
            "clientes": [
                {"id": c.id, "nome": c.nome, "cpf": c.cpf, "telefone": c.telefone or c.celular, "detalhe": f"R$ {float(saldo):.2f}".replace('.', ',')}
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
            .filter(Cliente.tenant_id == tenant_id, Cliente.ativo == True)
            .order_by(subq.c.total.desc())
            .limit(limit)
            .all()
        )
        return {
            "clientes": [
                {"id": c.id, "nome": c.nome, "cpf": c.cpf, "telefone": c.telefone or c.celular, "detalhe": f"{total} cupom(ns) ativo(s)"}
                for c, total in rows
            ]
        }

    else:  # ranking
        from datetime import date
        periodo_atual = date.today().strftime("%Y-%m")
        rows = (
            db.query(Cliente, CustomerRankHistory.rank_level, CustomerRankHistory.total_spent)
            .join(CustomerRankHistory, Cliente.id == CustomerRankHistory.customer_id)
            .filter(
                CustomerRankHistory.tenant_id == tenant_id,
                CustomerRankHistory.period == periodo_atual,
                Cliente.ativo == True,
            )
            .order_by(CustomerRankHistory.total_spent.desc())
            .limit(limit)
            .all()
        )
        rank_map = {"platinum": "🏆 Platinum", "gold": "🥇 Ouro", "silver": "🥈 Prata", "bronze": "🥉 Bronze"}
        return {
            "clientes": [
                {"id": c.id, "nome": c.nome, "cpf": c.cpf, "telefone": c.telefone or c.celular, "detalhe": rank_map.get(str(rank), str(rank))}
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

    # Saldo cashback = soma de todos os lançamentos.
    # Lançamentos com expires_at no passado e tx_type='credit' são ignorados
    # (o job de expiração já insere um lançamento negativo para eles,
    # mas enquanto isso não aconteceu, excluímos manualmente da soma).
    now_utc = datetime.now(timezone.utc)
    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            # Inclui lançamentos sem prazo OU com prazo ainda no futuro
            # OU lançamentos negativos (debit/expired/reversal) — sempre contam
            sql_or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now_utc,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .scalar()
    )
    saldo_cashback = float(saldo_raw or 0)

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
        )
        .order_by(Coupon.id.desc())
        .limit(10)
        .all()
    )

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
                "discount_percent": float(c.discount_percent) if c.discount_percent else None,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            }
            for c in cupons_ativos
        ],
    }


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
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(limit)
        .all()
    )

    # Saldo atual (reaproveitando a mesma lógica do /saldo)
    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            sql_or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now_utc,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .scalar()
    )
    saldo_atual = float(saldo_raw or 0)

    items = []
    for t in txs:
        # Determina se este crédito específico está expirado
        is_expired_credit = (
            t.tx_type == "credit"
            and t.expires_at is not None
            and t.expires_at <= now_utc
        )
        items.append({
            "id": t.id,
            "amount": float(t.amount),
            "tx_type": t.tx_type,   # 'credit' | 'debit' | 'expired'
            "source_type": t.source_type.value,
            "description": t.description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "expired": is_expired_credit,
        })

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

    # Saldo disponível
    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            sql_or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now_utc,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .scalar()
    )
    saldo = float(saldo_raw or 0)

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
        ticket_medio_cashback = sum(float(t.amount) for t in ultimas_compras) / len(ultimas_compras)
        # Estimativa groossa: se o cashback médio é ~2%, ticket médio é ~50x
        # Mas sem acesso direto às vendas, usamos o valor de cashback como referência
        ticket_sugerido = round(ticket_medio_cashback * 50, 2)  # fallback heurístico
    else:
        ticket_sugerido = 100.0

    valor_com_cashback = max(0.0, round(ticket_sugerido - saldo, 2))

    # Próximo cashback que vai expirar
    proximo_expirando = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer_id,
            CashbackTransaction.tx_type == "credit",
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
            "amount": float(proximo_expirando.amount),
            "expires_at": proximo_expirando.expires_at.isoformat(),
            "dias_restantes": max(0, (proximo_expirando.expires_at - now_utc).days),
        } if proximo_expirando else None,
    }


# ---------------------------------------------------------------------------
# Carimbos — listagem por cliente
# ---------------------------------------------------------------------------

@router.get("/clientes/{customer_id}/carimbos")
def listar_carimbos_cliente(
    customer_id: int,
    incluir_estornados: bool = Query(False, description="Inclui carimbos já estornados"),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todos os carimbos de um cliente (ativos e opcionalmente estornados)."""
    _, tenant_id = user_and_tenant

    q = db.query(LoyaltyStamp).filter(
        LoyaltyStamp.tenant_id == tenant_id,
        LoyaltyStamp.customer_id == customer_id,
    )
    if not incluir_estornados:
        q = q.filter(LoyaltyStamp.voided_at.is_(None))
    stamps = q.order_by(LoyaltyStamp.created_at.desc()).all()
    stamps_by_campaign: dict[int, list[LoyaltyStamp]] = {}
    for stamp in stamps:
        stamps_by_campaign.setdefault(int(stamp.campaign_id), []).append(stamp)

    converted_stamp_ids: set[int] = set()
    if stamps_by_campaign:
        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.tenant_id == tenant_id,
                Campaign.id.in_(list(stamps_by_campaign.keys())),
            )
            .all()
        )
        campaign_map = {int(c.id): c for c in campaigns}
        for campaign_id, campaign_stamps in stamps_by_campaign.items():
            campaign = campaign_map.get(campaign_id)
            if campaign is None:
                continue
            loyalty_balance = get_loyalty_balance_for_campaign(
                db,
                campaign=campaign,
                customer_id=customer_id,
            )
            converted_stamp_ids.update(
                build_consumed_loyalty_stamp_ids(
                    campaign_stamps,
                    consumed_count=loyalty_balance["converted_stamps"],
                )
            )

    return [
        {
            "id": s.id,
            "customer_id": s.customer_id,
            "venda_id": s.venda_id,
            "campaign_id": s.campaign_id,
            "is_manual": s.is_manual,
            "notes": s.notes,
            "created_at": s.created_at.isoformat(),
            "voided_at": s.voided_at.isoformat() if s.voided_at else None,
            "is_converted": s.id in converted_stamp_ids and s.voided_at is None,
            "status": (
                "estornado"
                if s.voided_at
                else "convertido"
                if s.id in converted_stamp_ids
                else "ativo"
            ),
        }
        for s in stamps
    ]


# ---------------------------------------------------------------------------
# Ranking — listagem de clientes por nível
# ---------------------------------------------------------------------------

@router.get("/ranking")
def listar_ranking(
    nivel: Optional[str] = Query(None, description="bronze | silver | gold | diamond | platinum"),
    periodo: Optional[str] = Query(None, description="Período YYYY-MM (padrão: mais recente)"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista clientes com seu nível de ranking atual, com distribuição por nível.
    """
    from app.models import Cliente

    _, tenant_id = user_and_tenant

    # Descobrir o período mais recente se não informado
    if not periodo:
        ultimo = (
            db.query(CustomerRankHistory.period)
            .filter(CustomerRankHistory.tenant_id == tenant_id)
            .order_by(CustomerRankHistory.period.desc())
            .first()
        )
        if not ultimo:
            return {"periodo": None, "distribuicao": {}, "clientes": []}
        periodo = ultimo[0]

    q = db.query(CustomerRankHistory).filter(
        CustomerRankHistory.tenant_id == tenant_id,
        CustomerRankHistory.period == periodo,
    )
    if nivel:
        try:
            q = q.filter(CustomerRankHistory.rank_level == RankLevelEnum(nivel))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Nível inválido: {nivel}")

    registros = q.order_by(CustomerRankHistory.total_spent.desc()).limit(limit).all()

    # Buscar nomes dos clientes em lote
    customer_ids = [r.customer_id for r in registros]
    clientes_map = {}
    if customer_ids:
        clientes = db.query(Cliente).filter(
            Cliente.id.in_(customer_ids),
            Cliente.tenant_id == tenant_id,
        ).all()
        clientes_map = {c.id: {"nome": c.nome, "telefone": getattr(c, "telefone", None)} for c in clientes}

    # Distribuição por nível (todos os clientes do período)
    dist = (
        db.query(CustomerRankHistory.rank_level, sqlfunc.count())
        .filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.period == periodo,
        )
        .group_by(CustomerRankHistory.rank_level)
        .all()
    )
    distribuicao = {r[0].value: r[1] for r in dist}

    return {
        "periodo": periodo,
        "distribuicao": distribuicao,
        "clientes": [
            {
                "customer_id": r.customer_id,
                "nome": clientes_map.get(r.customer_id, {}).get("nome", f"Cliente #{r.customer_id}"),
                "telefone": clientes_map.get(r.customer_id, {}).get("telefone"),
                "rank_level": r.rank_level.value,
                "total_spent": float(r.total_spent),
                "total_purchases": r.total_purchases,
                "active_months": r.active_months,
                "period": r.period,
            }
            for r in registros
        ],
    }


# ---------------------------------------------------------------------------
# Dashboard — alertas do dia e resumo de campanhas
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def dashboard_campanhas(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Resumo do dia: cupons emitidos hoje, aniversários do dia, saldo passivo de cashback.
    """
    from app.models import Cliente, Pet
    from datetime import timedelta

    _, tenant_id = user_and_tenant
    hoje = date.today()
    hoje_mm_dd = f"{hoje.month:02d}-{hoje.day:02d}"

    # Cupons emitidos hoje
    cupons_hoje = (
        db.query(sqlfunc.count(Coupon.id))
        .filter(
            Coupon.tenant_id == tenant_id,
            sqlfunc.date(Coupon.created_at) == hoje,
        )
        .scalar()
    ) or 0

    # Cupons usados hoje
    cupons_usados_hoje = (
        db.query(sqlfunc.count(CouponRedemption.id))
        .filter(
            CouponRedemption.tenant_id == tenant_id,
            sqlfunc.date(CouponRedemption.redeemed_at) == hoje,
        )
        .scalar()
    ) or 0

    # Cupons expirados hoje (valid_until = hoje)
    cupons_expirados_hoje = (
        db.query(sqlfunc.count(Coupon.id))
        .filter(
            Coupon.tenant_id == tenant_id,
            sqlfunc.date(Coupon.valid_until) == hoje,
        )
        .scalar()
    ) or 0

    # Cupons ativos (todos)
    cupons_ativos_total = (
        db.query(sqlfunc.count(Coupon.id))
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.status == CouponStatusEnum.active,
        )
        .scalar()
    ) or 0

    # Saldo passivo de cashback (quanto os clientes têm para usar)
    saldo_passivo = float(
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(CashbackTransaction.tenant_id == tenant_id)
        .scalar()
        or 0
    )

    # Aniversários de cliente hoje
    aniversarios_clientes = []
    try:
        todos_clientes = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.data_nascimento.isnot(None),
        ).all()
        for c in todos_clientes:
            if c.data_nascimento:
                dn = c.data_nascimento
                if hasattr(dn, 'month') and f"{dn.month:02d}-{dn.day:02d}" == hoje_mm_dd:
                    aniversarios_clientes.append({
                        "id": c.id,
                        "nome": c.nome,
                        "tipo": "cliente",
                        "idade": hoje.year - dn.year,
                    })
    except Exception:
        pass

    # Aniversários de pet hoje
    aniversarios_pets = []
    try:
        todos_pets = db.query(Pet).filter(
            Pet.tenant_id == tenant_id,
            Pet.data_nascimento.isnot(None),
        ).all()
        for p in todos_pets:
            if p.data_nascimento:
                dn = p.data_nascimento
                if hasattr(dn, 'month') and f"{dn.month:02d}-{dn.day:02d}" == hoje_mm_dd:
                    aniversarios_pets.append({
                        "id": p.id,
                        "nome": p.nome,
                        "tipo": "pet",
                        "dono_id": p.cliente_id,
                    })
    except Exception:
        pass

    # Campanhas ativas
    _campanhas_list = (
        db.query(Campaign.id, Campaign.name)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.status == CampaignStatusEnum.active,
        )
        .all()
    )
    campanhas_ativas = {
        "total": len(_campanhas_list),
        "nomes": [c.name for c in _campanhas_list],
    }

    # ── Aniversários de amanhã ─────────────────────────────────────────────
    amanha = hoje + timedelta(days=1)
    amanha_mm_dd = f"{amanha.month:02d}-{amanha.day:02d}"
    aniversarios_amanha = []
    try:
        for c in todos_clientes:
            if c.data_nascimento:
                dn = c.data_nascimento
                if hasattr(dn, 'month') and f"{dn.month:02d}-{dn.day:02d}" == amanha_mm_dd:
                    aniversarios_amanha.append({"nome": c.nome, "tipo": "cliente"})
        for p in todos_pets:
            if p.data_nascimento:
                dn = p.data_nascimento
                if hasattr(dn, 'month') and f"{dn.month:02d}-{dn.day:02d}" == amanha_mm_dd:
                    aniversarios_amanha.append({"nome": p.nome, "tipo": "pet"})
    except Exception:
        pass

    # ── Clientes inativos (sem venda finalizada nos últimos N dias) ────────
    inativos_30d = 0
    inativos_60d = 0
    try:
        from app.vendas_models import Venda as VendaModel
        corte_30 = datetime.combine(hoje - timedelta(days=30), datetime.min.time())
        corte_60 = datetime.combine(hoje - timedelta(days=60), datetime.min.time())

        # IDs de clientes que compraram na janela recente
        ativos_30d_ids = set(
            r[0] for r in db.query(VendaModel.cliente_id)
            .filter(
                VendaModel.tenant_id == tenant_id,
                VendaModel.cliente_id.isnot(None),
                VendaModel.status == "finalizada",
                VendaModel.data_venda >= corte_30,
            ).distinct().all()
        )
        ativos_60d_ids = set(
            r[0] for r in db.query(VendaModel.cliente_id)
            .filter(
                VendaModel.tenant_id == tenant_id,
                VendaModel.cliente_id.isnot(None),
                VendaModel.status == "finalizada",
                VendaModel.data_venda >= corte_60,
            ).distinct().all()
        )
        todos_com_venda_ids = set(
            r[0] for r in db.query(VendaModel.cliente_id)
            .filter(
                VendaModel.tenant_id == tenant_id,
                VendaModel.cliente_id.isnot(None),
                VendaModel.status == "finalizada",
            ).distinct().all()
        )
        inativos_30d = len(todos_com_venda_ids - ativos_30d_ids)
        inativos_60d = len(todos_com_venda_ids - ativos_60d_ids)

        # Clientes que atingiram inatividade HOJE (última compra foi há exatamente 30 dias)
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

    # ── Sorteios pendentes (não concluídos) ───────────────────────────────
    sorteios_pendentes = []
    try:
        sp = db.query(Drawing).filter(
            Drawing.tenant_id == tenant_id,
            Drawing.status != DrawingStatusEnum.done,
        ).order_by(Drawing.draw_date.asc().nullsfirst()).limit(10).all()
        sorteios_pendentes = [
            {
                "id": s.id,
                "name": s.name,
                "status": s.status.value,
                "draw_date": s.draw_date.isoformat() if s.draw_date else None,
            }
            for s in sp
        ]
    except Exception:
        pass

    # ── Sorteios desta semana ─────────────────────────────────────────────
    sorteios_semana = []
    try:
        semana = hoje + timedelta(days=7)
        ss = db.query(Drawing).filter(
            Drawing.tenant_id == tenant_id,
            Drawing.draw_date >= datetime.combine(hoje, datetime.min.time()),
            Drawing.draw_date <= datetime.combine(semana, datetime.max.time()),
            Drawing.status != DrawingStatusEnum.done,
        ).order_by(Drawing.draw_date.asc()).limit(5).all()
        sorteios_semana = [
            {
                "id": s.id,
                "name": s.name,
                "draw_date": s.draw_date.isoformat() if s.draw_date else None,
            }
            for s in ss
        ]
    except Exception:
        pass

    # ── Brindes pendentes de retirada (cupons gift do destaque mensal) ────
    brindes_pendentes = []
    try:
        from app.models import Cliente as ClienteModel
        brindes_q = (
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
        b_cids = [b.customer_id for b in brindes_q if b.customer_id]
        b_clientes: dict = {}
        if b_cids:
            for cl in db.query(ClienteModel).filter(ClienteModel.id.in_(b_cids)).all():
                b_clientes[cl.id] = cl.nome
        brindes_pendentes = [
            {
                "code": b.code,
                "customer_id": b.customer_id,
                "nome_cliente": b_clientes.get(b.customer_id, f"#{b.customer_id}"),
                "mensagem": b.meta.get("mensagem", "") if b.meta else "",
                "retirar_de": b.meta.get("retirar_de") if b.meta else None,
                "retirar_ate": b.meta.get("retirar_ate") if b.meta else None,
                "categoria": b.meta.get("categoria", "") if b.meta else "",
                "periodo": b.meta.get("periodo", "") if b.meta else "",
            }
            for b in brindes_q
        ]
    except Exception:
        pass

    # ── Dias até o fim do mês (para destaque mensal) ──────────────────────
    import calendar as _calendar
    _, ultimo_dia = _calendar.monthrange(hoje.year, hoje.month)
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
        # Sprint 9 — alertas do dia
        "alertas": {
            "inativos_30d": inativos_30d,
            "inativos_60d": inativos_60d,
            "novos_inativos_hoje": novos_inativos_hoje,
            "sorteios_pendentes": sorteios_pendentes,
            "total_sorteios_pendentes": len(sorteios_pendentes),
            "brindes_pendentes": brindes_pendentes,
            "total_brindes_pendentes": len(brindes_pendentes),
        },
        # Sprint 9 — próximos eventos
        "proximos_eventos": {
            "aniversarios_amanha": aniversarios_amanha,
            "total_aniversarios_amanha": len(aniversarios_amanha),
            "sorteios_esta_semana": sorteios_semana,
            "dias_ate_fim_mes": dias_ate_fim_mes,
        },
    }


# ---------------------------------------------------------------------------
# Cashback — ajuste manual (Gestor de Benefícios)
# ---------------------------------------------------------------------------

class CashbackManualBody(BaseModel):
    customer_id: int
    amount: float  # positivo = crédito, negativo = débito
    description: str = "Ajuste manual"


@router.post("/cashback/manual")
def cashback_manual(
    body: CashbackManualBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lança um ajuste manual de cashback para um cliente.
    Positivo = crédito, negativo = débito.
    Usado no Gestor de Benefícios para corригir ou ajustar saldo.
    """
    _, tenant_id = user_and_tenant
    if body.amount == 0:
        raise HTTPException(status_code=400, detail="O valor do ajuste não pode ser zero.")

    transacao = CashbackTransaction(
        tenant_id=tenant_id,
        customer_id=body.customer_id,
        amount=round(body.amount, 2),
        source_type=CashbackSourceTypeEnum.manual,
        description=body.description,
    )
    db.add(transacao)
    db.commit()
    db.refresh(transacao)

    novo_saldo = float(
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == body.customer_id,
        )
        .scalar() or 0
    )

    logger.info(
        "[Campanhas] Cashback manual: customer_id=%d amount=%.2f tenant=%s novo_saldo=%.2f",
        body.customer_id, body.amount, tenant_id, novo_saldo,
    )
    return {
        "ok": True,
        "transaction_id": transacao.id,
        "amount": float(body.amount),
        "description": body.description,
        "novo_saldo": round(novo_saldo, 2),
    }


# ---------------------------------------------------------------------------
# Anular cupom (Sprint 9)
# ---------------------------------------------------------------------------

@router.delete("/cupons/{code}", status_code=200)
def anular_cupom(
    code: str,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Marca o cupao como void (cancelado).
    Se o cupao for de fidelidade (gerado por consumo de carimbos),
    devolve automaticamente os carimbos comprometidos para saldo disponivel.
    So e possivel anular cupoes com status `active`.
    """
    _, tenant_id = user_and_tenant
    cupom = (
        db.query(Coupon)
        .filter(Coupon.tenant_id == tenant_id, Coupon.code == code)
        .first()
    )
    if not cupom:
        raise HTTPException(404, detail="Cupão não encontrado.")
    if cupom.status != CouponStatusEnum.active:
        raise HTTPException(400, detail=f"Não é possível anular um cupão com status '{cupom.status.value}'.")

    loyalty_reversal = revoke_loyalty_reward_by_coupon(
        db,
        tenant_id=tenant_id,
        coupon_id=cupom.id,
        reason="cupom_anulado_manualmente",
    )

    cupom.status = CouponStatusEnum.voided
    db.commit()
    return {
        "ok": True,
        "code": code,
        "status": "voided",
        "fidelidade": {
            "cupom_vinculado": bool(loyalty_reversal.get("matched")),
            "carimbos_restaurados": bool(loyalty_reversal.get("revoked")),
        },
    }


# ---------------------------------------------------------------------------
# Relátorio de campanhas — histórico de cashback (créditos e resgates)
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
    from sqlalchemy import func as sqlfunc
    from app.models import Cliente
    from app.vendas_models import Venda

    _, tenant_id = user_and_tenant

    q = db.query(CashbackTransaction).filter(
        CashbackTransaction.tenant_id == tenant_id,
    )

    if data_inicio:
        q = q.filter(CashbackTransaction.created_at >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:
        q = q.filter(CashbackTransaction.created_at <= datetime.combine(data_fim, datetime.max.time()))
    if tipo == "credito":
        q = q.filter(CashbackTransaction.amount > 0)
    elif tipo == "resgate":
        q = q.filter(CashbackTransaction.amount < 0)

    transacoes = q.order_by(CashbackTransaction.created_at.desc()).limit(500).all()

    # Buscar nomes de clientes em lote
    customer_ids = list({t.customer_id for t in transacoes})
    clientes_map = {}
    if customer_ids:
        clientes = db.query(Cliente).filter(
            Cliente.id.in_(customer_ids),
            Cliente.tenant_id == tenant_id,
        ).all()
        clientes_map = {c.id: c.nome for c in clientes}

    # Buscar números de venda em lote (source_id é venda_id para resgates)
    venda_ids = list({t.source_id for t in transacoes if t.source_id and t.amount < 0})
    vendas_map = {}
    if venda_ids:
        vendas = db.query(Venda).filter(
            Venda.id.in_(venda_ids),
            Venda.tenant_id == tenant_id,
        ).all()
        vendas_map = {v.id: v.numero_venda for v in vendas}

    resultado = []
    for t in transacoes:
        eh_resgate = t.amount < 0
        resultado.append({
            "id": t.id,
            "data": t.created_at.isoformat(),
            "cliente_id": t.customer_id,
            "cliente_nome": clientes_map.get(t.customer_id, f"Cliente #{t.customer_id}"),
            "tipo": "resgate" if eh_resgate else "credito",
            "valor": float(abs(t.amount)),
            "source_type": t.source_type.value if t.source_type else None,
            "venda_id": t.source_id if eh_resgate else None,
            "numero_venda": vendas_map.get(t.source_id) if eh_resgate and t.source_id else None,
            "descricao": t.description,
        })

    # Totais
    total_creditado = sum(r["valor"] for r in resultado if r["tipo"] == "credito")
    total_resgatado = sum(r["valor"] for r in resultado if r["tipo"] == "resgate")

    return {
        "transacoes": resultado,
        "total_creditado": round(total_creditado, 2),
        "total_resgatado": round(total_resgatado, 2),
        "saldo_total": round(total_creditado - total_resgatado, 2),
    }


# ---------------------------------------------------------------------------
# Carimbos — lançamento manual
# ---------------------------------------------------------------------------

class LancarCarimboManualBody(BaseModel):
    customer_id: int
    venda_id: Optional[int] = None
    nota: Optional[str] = None


@router.post("/carimbos/manual")
def lancar_carimbo_manual(
    body: LancarCarimboManualBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lança um carimbo manual para um cliente.

    Usado para converter cartões físicos antigos ou como ajuste operacional.
    Idempotente: se já existe um carimbo manual sem venda_id para este cliente
    na mesma hora, retorna o existente.
    """
    _, tenant_id = user_and_tenant

    # Buscar campanha de fidelidade ativa do tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == "loyalty_stamp",
            Campaign.status.in_([CampaignStatusEnum.active, CampaignStatusEnum.paused]),
        )
        .first()
    )
    if not campanha:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma campanha de cartão fidelidade encontrada. Ative a campanha primeiro.",
        )

    stamp = LoyaltyStamp(
        tenant_id=tenant_id,
        customer_id=body.customer_id,
        venda_id=body.venda_id,
        campaign_id=campanha.id,
        stamp_index=1,
        is_manual=True,
        notes=body.nota or "Carimbo lançado manualmente",
    )
    db.add(stamp)
    try:
        db.flush()
    except Exception:
        db.rollback()
        # Já existe (UNIQUE constraint) — buscar o existente
        existing = (
            db.query(LoyaltyStamp)
            .filter(
                LoyaltyStamp.tenant_id == tenant_id,
                LoyaltyStamp.campaign_id == campanha.id,
                LoyaltyStamp.customer_id == body.customer_id,
                LoyaltyStamp.venda_id == body.venda_id,
            )
            .first()
        )
        if existing:
            saldo = summarize_loyalty_balances_for_customer(
                db,
                tenant_id=tenant_id,
                customer_id=body.customer_id,
            )
            return {
                "ok": True,
                "novo": False,
                "total_carimbos": saldo["total_carimbos"],
                "total_carimbos_brutos": saldo["total_carimbos_brutos"],
                "carimbos_comprometidos_total": saldo["carimbos_comprometidos_total"],
                "carimbos_em_debito": saldo["carimbos_em_debito"],
                "carimbos_convertidos": saldo["carimbos_convertidos"],
                "stamp_id": existing.id,
            }
        raise HTTPException(status_code=500, detail="Erro ao lançar carimbo")

    from app.campaigns.loyalty_service import sync_loyalty_rewards_for_customer

    sync_loyalty_rewards_for_customer(
        db,
        campaign=campanha,
        customer_id=body.customer_id,
        source_event_id=None,
    )

    db.commit()
    db.refresh(stamp)

    saldo = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=body.customer_id,
    )

    logger.info(
        "[Campanhas] Carimbo manual lançado customer_id=%d tenant=%s total=%d",
        body.customer_id, tenant_id, saldo["total_carimbos"],
    )

    return {
        "ok": True,
        "novo": True,
        "stamp_id": stamp.id,
        "total_carimbos": saldo["total_carimbos"],
        "total_carimbos_brutos": saldo["total_carimbos_brutos"],
        "carimbos_comprometidos_total": saldo["carimbos_comprometidos_total"],
        "carimbos_em_debito": saldo["carimbos_em_debito"],
        "carimbos_convertidos": saldo["carimbos_convertidos"],
        "params": campanha.params,
        "stamps_to_complete": campanha.params.get("stamps_to_complete", 10),
    }


# ---------------------------------------------------------------------------
# Carimbos — estorno (remoção) de carimbo individual
# ---------------------------------------------------------------------------

@router.delete("/carimbos/{stamp_id}", status_code=200)
def estornar_carimbo(
    stamp_id: int,
    motivo: Optional[str] = Query(None, description="Motivo do estorno"),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Estorna (remove) um carimbo de fidelidade lançado por engano.
    Registra voided_at — não deleta o registro para manter rastreabilidade.
    """
    _, tenant_id = user_and_tenant

    stamp = (
        db.query(LoyaltyStamp)
        .filter(LoyaltyStamp.id == stamp_id, LoyaltyStamp.tenant_id == tenant_id)
        .first()
    )
    if not stamp:
        raise HTTPException(status_code=404, detail="Carimbo não encontrado")
    if stamp.voided_at is not None:
        raise HTTPException(status_code=409, detail="Carimbo já foi estornado")

    stamp.voided_at = datetime.now(timezone.utc)
    if motivo:
        stamp.notes = f"{stamp.notes or ''} [ESTORNO: {motivo}]".strip()

    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.id == stamp.campaign_id,
            Campaign.tenant_id == tenant_id,
        )
        .first()
    )
    if campanha is not None:
        from app.campaigns.loyalty_service import sync_loyalty_rewards_for_customer

        sync_loyalty_rewards_for_customer(
            db,
            campaign=campanha,
            customer_id=stamp.customer_id,
            source_event_id=None,
        )

    db.commit()

    saldo = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=stamp.customer_id,
    )

    logger.info(
        "[Campanhas] Carimbo #%d estornado customer_id=%d tenant=%s restantes=%d",
        stamp_id, stamp.customer_id, tenant_id, saldo["total_carimbos"],
    )
    return {
        "ok": True,
        "stamp_id": stamp_id,
        "total_carimbos_ativos": saldo["total_carimbos"],
        "total_carimbos_brutos": saldo["total_carimbos_brutos"],
        "carimbos_comprometidos_total": saldo["carimbos_comprometidos_total"],
        "carimbos_em_debito": saldo["carimbos_em_debito"],
        "carimbos_convertidos": saldo["carimbos_convertidos"],
    }


# ---------------------------------------------------------------------------
# Ranking — configurar critérios por nível
# ---------------------------------------------------------------------------

class RankingConfigBody(BaseModel):
    silver_min_spent: float = 300
    silver_min_purchases: int = 4
    silver_min_months: int = 2
    gold_min_spent: float = 1000
    gold_min_purchases: int = 10
    gold_min_months: int = 4
    diamond_min_spent: float = 3000
    diamond_min_purchases: int = 20
    diamond_min_months: int = 6
    platinum_min_spent: float = 8000
    platinum_min_purchases: int = 40
    platinum_min_months: int = 10


@router.get("/ranking/config")
def get_ranking_config(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna os critérios de ranking configurados para o tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    params = campanha.params if campanha else {}
    defaults = RankingConfigBody().model_dump()
    return {k: params.get(k, v) for k, v in defaults.items()}


@router.put("/ranking/config")
def salvar_ranking_config(
    body: RankingConfigBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Salva os critérios de ranking no tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha de ranking não encontrada. Execute o seed primeiro.")
    campanha.params = {**(campanha.params or {}), **body.model_dump()}
    db.commit()
    return {"ok": True, "params": campanha.params}


# ---------------------------------------------------------------------------
# Configuração global de horários do scheduler
# ---------------------------------------------------------------------------

class SchedulerConfigBody(BaseModel):
    birthday_send_hour: int = 8          # hora de envio das mensagens de aniversário (0-23)
    inactivity_send_hour: int = 9        # hora de envio das mensagens de inatividade (0-23)
    inactivity_day_of_week: str = "mon"  # dia da semana: mon/tue/wed/thu/fri/sat/sun
    ranking_send_day: int = 1            # dia do mês para recálculo do ranking (1-28)
    ranking_send_hour: int = 6           # hora do recálculo de ranking (0-23)
    auto_destaque_mensal: bool = False   # True = enviar destaque mensal automaticamente no dia 1
    auto_destaque_coupon_value: float = 50.0  # valor do cupom do destaque automático
    auto_destaque_coupon_days: int = 10       # validade do cupom do destaque automático


@router.get("/config/horarios")
def get_scheduler_config(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna as configurações de horário do scheduler para o tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.birthday_customer,
        )
        .first()
    )
    params = campanha.params if campanha else {}
    defaults = SchedulerConfigBody().model_dump()
    return {k: params.get(k, v) for k, v in defaults.items()}


@router.put("/config/horarios")
def salvar_scheduler_config(
    body: SchedulerConfigBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Salva as configurações de horário do scheduler para o tenant."""
    _, tenant_id = user_and_tenant
    campanha = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.birthday_customer,
        )
        .first()
    )
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha de aniversário não encontrada. Execute o seed primeiro.")
    campanha.params = {**(campanha.params or {}), **body.model_dump()}

    # Salvar params de destaque automático na campanha ranking_monthly também
    ranking_camp = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    if ranking_camp:
        ranking_camp.params = {
            **(ranking_camp.params or {}),
            "auto_destaque_mensal": body.auto_destaque_mensal,
            "auto_destaque_coupon_value": body.auto_destaque_coupon_value,
            "auto_destaque_coupon_days": body.auto_destaque_coupon_days,
        }

    db.commit()
    return {"ok": True, "params": campanha.params}


# ---------------------------------------------------------------------------
# Ranking — forçar recálculo
# ---------------------------------------------------------------------------

@router.post("/ranking/recalcular")
def recalcular_ranking(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Força recálculo imediato do ranking de todos os clientes do tenant.
    Publica um evento monthly_ranking_recalc na fila do worker.
    """
    _, tenant_id = user_and_tenant

    from app.campaigns.models import CampaignEventQueue, EventOriginEnum

    evento = CampaignEventQueue(
        tenant_id=tenant_id,
        event_type="monthly_ranking_recalc",
        event_origin=EventOriginEnum.user_action,
        event_depth=0,
        payload={"triggered_by": "manual", "triggered_at": datetime.now(timezone.utc).isoformat()},
    )
    db.add(evento)
    db.commit()

    return {"ok": True, "message": "Recálculo de ranking enfileirado. O worker processará em até 10 segundos."}


# ---------------------------------------------------------------------------
# Seed — criar campanhas padrão para o tenant
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CRUD de campanhas personalizadas
# ---------------------------------------------------------------------------

# Tipos que o usuário pode criar livremente (sem ser via seed)
_USER_CREATABLE_TYPES = {
    CampaignTypeEnum.inactivity,
    CampaignTypeEnum.quick_repurchase,
    CampaignTypeEnum.bulk_segment,
}


class CriarCampanhaBody(BaseModel):
    name: str
    campaign_type: str
    params: Optional[dict] = None
    priority: Optional[int] = 50


@router.post("/campanhas", status_code=201)
def criar_campanha(
    body: CriarCampanhaBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria uma nova campanha personalizada.
    Permite apenas tipos: inactivity, quick_repurchase, bulk_segment.
    """
    _, tenant_id = user_and_tenant

    try:
        tipo = CampaignTypeEnum(body.campaign_type)
    except ValueError:
        raise HTTPException(400, detail=f"Tipo de campanha inválido: {body.campaign_type}")

    if tipo not in _USER_CREATABLE_TYPES:
        raise HTTPException(
            400,
            detail=f"Tipo '{body.campaign_type}' é gerenciado automaticamente e não pode ser criado manualmente.",
        )

    campaign = Campaign(
        tenant_id=tenant_id,
        name=body.name.strip(),
        campaign_type=tipo,
        status=CampaignStatusEnum.active,
        priority=max(0, min(999, body.priority or 50)),
        params=body.params or {},
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "priority": campaign.priority,
        "params": campaign.params,
    }


@router.delete("/campanhas/{campaign_id}", status_code=204)
def deletar_campanha(
    campaign_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Arquiva (soft-delete) uma campanha personalizada.
    Campanhas do seed (birthday, cashback, loyalty, ranking, welcome) não podem ser removidas.
    """
    _, tenant_id = user_and_tenant

    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        .first()
    )
    if not campaign:
        raise HTTPException(404, detail="Campanha não encontrada.")

    if campaign.campaign_type not in _USER_CREATABLE_TYPES:
        raise HTTPException(
            400,
            detail="Campanha do sistema não pode ser removida manualmente.",
        )

    campaign.status = CampaignStatusEnum.archived
    db.commit()
    return


# ---------------------------------------------------------------------------
# Retenção Dinâmica — CRUD dedicado (filtra por campaign_type = inactivity)
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
                    desempate_info.append({
                        "categoria": categoria,
                        "pulado": lista[0],
                        "eleito": candidato,
                        "posicao_eleito": i + 1,  # 2, 3, ...
                        "motivo": f"1º colocado já venceu em outra categoria",
                    })
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
    tipo_premio: str = "cupom"          # "cupom" | "mensagem"
    coupon_value: float = 50.0
    coupon_valid_days: int = 10
    mensagem_brinde: Optional[str] = None
    retirar_de: Optional[str] = None    # data string YYYY-MM-DD
    retirar_ate: Optional[str] = None   # data string YYYY-MM-DD
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
    last_month = (first_day_this_month - timedelta(days=1))
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

            resultados.append({
                "categoria": categoria,
                "customer_id": customer_id,
                "tipo_premio": "mensagem",
                "mensagem": mensagem,
                "retirar_de": retirar_de,
                "retirar_ate": retirar_ate,
                "ja_existia": ja_existia_brinde,
            })
            logger.info(
                "[DestaqueEnviar] Brinde registrado — cliente %s, categoria %s, periodo %s",
                customer_id, categoria, period,
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
            resultados.append({
                "categoria": categoria,
                "customer_id": customer_id,
                "tipo_premio": "cupom",
                "coupon_code": already.code,
                "coupon_value": float(already.discount_value or 0),
                "ja_existia": True,
            })
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
            resultados.append({
                "categoria": categoria,
                "customer_id": customer_id,
                "tipo_premio": "cupom",
                "coupon_code": coupon.code,
                "coupon_value": val_cupom,
                "ja_existia": False,
            })
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
        "message": f"{criadas} campanha(s) criada(s)" if criadas else "Todas as campanhas padrão já existem",
    }


# ---------------------------------------------------------------------------
# SPRINT 7 — Sorteios
# ---------------------------------------------------------------------------

class CriarSorteioBody(BaseModel):
    name: str
    description: Optional[str] = None
    prize_description: Optional[str] = None
    rank_filter: Optional[str] = None   # bronze | silver | gold | diamond | platinum | None = todos
    draw_date: Optional[str] = None     # ISO 8601 date string
    auto_execute: bool = False          # True = executar automaticamente na draw_date


class EditarSorteioBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prize_description: Optional[str] = None
    rank_filter: Optional[str] = None
    draw_date: Optional[str] = None
    auto_execute: Optional[bool] = None


def _drawing_to_dict(d: Drawing, entry_count: int = 0) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "prize_description": d.prize_description,
        "rank_filter": d.rank_filter.value if d.rank_filter else None,
        "status": d.status.value,
        "draw_date": d.draw_date.isoformat() if d.draw_date else None,
        "auto_execute": d.auto_execute,
        "entries_frozen_at": d.entries_frozen_at.isoformat() if d.entries_frozen_at else None,
        "entries_hash": d.entries_hash,
        "seed_uuid": str(d.seed_uuid) if d.seed_uuid else None,
        "winner_entry_id": d.winner_entry_id,
        "created_at": d.created_at.isoformat(),
        "entry_count": entry_count,
    }


@router.get("/sorteios")
def listar_sorteios(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todos os sorteios do tenant."""
    _, tenant_id = user_and_tenant

    drawings = (
        db.query(Drawing)
        .filter(Drawing.tenant_id == tenant_id)
        .order_by(Drawing.created_at.desc())
        .all()
    )

    # Contar participantes para cada sorteio
    drawing_ids = [d.id for d in drawings]
    counts = {}
    if drawing_ids:
        rows = (
            db.query(DrawingEntry.drawing_id, sqlfunc.count(DrawingEntry.id))
            .filter(DrawingEntry.drawing_id.in_(drawing_ids))
            .group_by(DrawingEntry.drawing_id)
            .all()
        )
        counts = {row[0]: row[1] for row in rows}

    return [_drawing_to_dict(d, counts.get(d.id, 0)) for d in drawings]


@router.post("/sorteios", status_code=201)
def criar_sorteio(
    body: CriarSorteioBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo sorteio em status 'draft'."""
    _, tenant_id = user_and_tenant

    rank_filter = None
    if body.rank_filter:
        try:
            rank_filter = RankLevelEnum(body.rank_filter)
        except ValueError:
            raise HTTPException(400, detail=f"Nível de ranking inválido: {body.rank_filter}")

    draw_date = None
    if body.draw_date:
        try:
            from datetime import datetime as _dt
            draw_date = _dt.fromisoformat(body.draw_date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(400, detail="draw_date inválido (use ISO 8601)")

    drawing = Drawing(
        tenant_id=tenant_id,
        name=body.name.strip(),
        description=body.description,
        prize_description=body.prize_description,
        rank_filter=rank_filter,
        status=DrawingStatusEnum.draft,
        draw_date=draw_date,
        auto_execute=body.auto_execute,
    )
    db.add(drawing)
    db.commit()
    db.refresh(drawing)
    return _drawing_to_dict(drawing, 0)


@router.put("/sorteios/{drawing_id}")
def editar_sorteio(
    drawing_id: int,
    body: EditarSorteioBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Edita campos de um sorteio ainda não executado."""
    _, tenant_id = user_and_tenant

    drawing = (
        db.query(Drawing)
        .filter(Drawing.id == drawing_id, Drawing.tenant_id == tenant_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, detail="Sorteio não encontrado.")
    if drawing.status == DrawingStatusEnum.drawn:
        raise HTTPException(400, detail="Sorteio já executado não pode ser editado.")

    if body.name is not None:
        drawing.name = body.name.strip()
    if body.description is not None:
        drawing.description = body.description
    if body.prize_description is not None:
        drawing.prize_description = body.prize_description
    if body.rank_filter is not None:
        try:
            drawing.rank_filter = RankLevelEnum(body.rank_filter) if body.rank_filter else None
        except ValueError:
            raise HTTPException(400, detail=f"Nível inválido: {body.rank_filter}")
    if body.draw_date is not None:
        try:
            from datetime import datetime as _dt
            drawing.draw_date = _dt.fromisoformat(body.draw_date).replace(tzinfo=timezone.utc) if body.draw_date else None
        except ValueError:
            raise HTTPException(400, detail="draw_date inválido (use ISO 8601)")
    if body.auto_execute is not None:
        drawing.auto_execute = body.auto_execute

    db.commit()
    db.refresh(drawing)

    entry_count = db.query(DrawingEntry).filter(DrawingEntry.drawing_id == drawing_id).count()
    return _drawing_to_dict(drawing, entry_count)


@router.post("/sorteios/{drawing_id}/inscrever")
def inscrever_participantes(
    drawing_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Inscreve automaticamente todos os clientes elegíveis (baseado em rank_filter).
    Clientes já inscritos são ignorados (idempotente).
    Muda o status do sorteio para 'open'.
    """
    _, tenant_id = user_and_tenant

    drawing = (
        db.query(Drawing)
        .filter(Drawing.id == drawing_id, Drawing.tenant_id == tenant_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, detail="Sorteio não encontrado.")
    if drawing.status in (DrawingStatusEnum.drawn, DrawingStatusEnum.cancelled):
        raise HTTPException(400, detail=f"Sorteio em status '{drawing.status.value}' não aceita inscrições.")

    # Descobrir período mais recente do ranking
    ultimo_periodo = (
        db.query(CustomerRankHistory.period)
        .filter(CustomerRankHistory.tenant_id == tenant_id)
        .order_by(CustomerRankHistory.period.desc())
        .first()
    )
    if not ultimo_periodo:
        raise HTTPException(400, detail="Nenhum dado de ranking disponível. Execute o recálculo primeiro.")
    periodo = ultimo_periodo[0]

    # Filtrar clientes elegíveis
    q = db.query(CustomerRankHistory).filter(
        CustomerRankHistory.tenant_id == tenant_id,
        CustomerRankHistory.period == periodo,
    )
    if drawing.rank_filter:
        q = q.filter(CustomerRankHistory.rank_level == drawing.rank_filter)
    clientes_ranking = q.all()

    # Clientes já inscritos (para skip)
    ja_inscritos = set(
        row[0]
        for row in db.query(DrawingEntry.customer_id)
        .filter(DrawingEntry.drawing_id == drawing_id)
        .all()
    )

    novos = 0
    for cr in clientes_ranking:
        if cr.customer_id in ja_inscritos:
            continue
        entry = DrawingEntry(
            tenant_id=tenant_id,
            drawing_id=drawing_id,
            customer_id=cr.customer_id,
            ticket_count=1,
            rank_level=cr.rank_level,
        )
        db.add(entry)
        novos += 1

    if drawing.status == DrawingStatusEnum.draft:
        drawing.status = DrawingStatusEnum.open

    db.commit()

    total = db.query(DrawingEntry).filter(DrawingEntry.drawing_id == drawing_id).count()
    return {
        "ok": True,
        "novos_inscritos": novos,
        "total_participantes": total,
        "periodo_ranking": periodo,
        "status": drawing.status.value,
    }


@router.post("/sorteios/{drawing_id}/executar")
def executar_sorteio(
    drawing_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Executa o sorteio com semente aleatória auditável (seed_uuid).

    Algoritmo:
    1. Congela a lista de participantes (hash SHA-256)
    2. Gera seed_uuid aleatório
    3. Usa seed para embaralhar deterministicamente a lista
    4. Sorteia 1 ganhador por peso (ticket_count)
    5. Grava resultado e muda status para 'drawn'
    """
    import hashlib
    import random as _random

    _, tenant_id = user_and_tenant

    drawing = (
        db.query(Drawing)
        .filter(Drawing.id == drawing_id, Drawing.tenant_id == tenant_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, detail="Sorteio não encontrado.")
    if drawing.status == DrawingStatusEnum.drawn:
        raise HTTPException(400, detail="Sorteio já executado.")
    if drawing.status == DrawingStatusEnum.cancelled:
        raise HTTPException(400, detail="Sorteio cancelado.")

    entries = (
        db.query(DrawingEntry)
        .filter(DrawingEntry.drawing_id == drawing_id)
        .order_by(DrawingEntry.id.asc())
        .all()
    )
    if not entries:
        raise HTTPException(400, detail="Nenhum participante inscrito.")

    # Congela lista: SHA-256 do CSV de IDs
    ids_csv = ",".join(str(e.id) for e in entries)
    entries_hash = hashlib.sha256(ids_csv.encode()).hexdigest()

    # Seed aleatório auditável
    seed_uuid = _uuid.uuid4()

    # Construir pool com pesos (ticket_count)
    pool = []
    for e in entries:
        pool.extend([e] * max(1, e.ticket_count))

    # Deterministic shuffle usando seed
    rng = _random.Random(str(seed_uuid))
    rng.shuffle(pool)
    winner_entry = pool[0]

    # Gravar resultado
    now = datetime.now(timezone.utc)
    drawing.status = DrawingStatusEnum.drawn
    drawing.seed_uuid = seed_uuid
    drawing.entries_hash = entries_hash
    drawing.entries_frozen_at = now
    drawing.winner_entry_id = winner_entry.id

    db.commit()
    db.refresh(drawing)

    # Buscar nome do ganhador
    from app.models import Cliente
    cliente = db.query(Cliente).filter(Cliente.id == winner_entry.customer_id, Cliente.tenant_id == tenant_id).first()

    # Enfileirar notificação de parabéns para o ganhador
    if cliente and cliente.email:
        from app.campaigns.notification_service import enqueue_email
        prize_text = drawing.prize_description or "o prêmio"
        enqueue_email(
            db,
            tenant_id=tenant_id,
            customer_id=cliente.id,
            subject=f"🏆 Você ganhou o sorteio: {drawing.name}!",
            body=(
                f"Parabéns, {cliente.nome}! 🎉\n\n"
                f"Você foi sorteado(a) como ganhador(a) do sorteio **{drawing.name}**.\n"
                f"Prêmio: {prize_text}\n\n"
                f"Entre em contato conosco para retirar seu prêmio. Boa sorte sempre!"
            ),
            email_address=cliente.email,
            idempotency_key=f"sorteio:{drawing.id}:ganhador:{cliente.id}",
        )
        db.commit()

    return {
        "ok": True,
        "winner_entry_id": winner_entry.id,
        "winner_customer_id": winner_entry.customer_id,
        "winner_name": cliente.nome if cliente else f"Cliente #{winner_entry.customer_id}",
        "total_participantes": len(entries),
        "seed_uuid": str(seed_uuid),
        "entries_hash": entries_hash,
    }


@router.get("/sorteios/{drawing_id}/resultado")
def resultado_sorteio(
    drawing_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o resultado de um sorteio executado, com lista de participantes."""
    from app.models import Cliente

    _, tenant_id = user_and_tenant

    drawing = (
        db.query(Drawing)
        .filter(Drawing.id == drawing_id, Drawing.tenant_id == tenant_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, detail="Sorteio não encontrado.")

    entries = (
        db.query(DrawingEntry)
        .filter(DrawingEntry.drawing_id == drawing_id)
        .order_by(DrawingEntry.registered_at.asc())
        .all()
    )

    customer_ids = [e.customer_id for e in entries]
    clientes_map = {}
    if customer_ids:
        clientes = db.query(Cliente).filter(
            Cliente.id.in_(customer_ids), Cliente.tenant_id == tenant_id
        ).all()
        clientes_map = {c.id: c.nome for c in clientes}

    winner_customer_id = None
    if drawing.winner_entry_id:
        winner_entry = next((e for e in entries if e.id == drawing.winner_entry_id), None)
        if winner_entry:
            winner_customer_id = winner_entry.customer_id

    return {
        "drawing": _drawing_to_dict(drawing, len(entries)),
        "winner_customer_id": winner_customer_id,
        "winner_name": clientes_map.get(winner_customer_id, f"Cliente #{winner_customer_id}") if winner_customer_id else None,
        "participantes": [
            {
                "entry_id": e.id,
                "customer_id": e.customer_id,
                "nome": clientes_map.get(e.customer_id, f"Cliente #{e.customer_id}"),
                "rank_level": e.rank_level.value if e.rank_level else None,
                "ticket_count": e.ticket_count,
                "is_winner": e.id == drawing.winner_entry_id,
            }
            for e in entries
        ],
    }


@router.get("/sorteios/{drawing_id}/codigos-offline")
def codigos_offline_sorteio(
    drawing_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna a lista de participantes com códigos numerados para sorteio offline.
    Útil para imprimir e sortear fisicamente (coloca em um chapéu, etc).
    Cada participante tem tantos 'tickets' quanto seu ticket_count.
    """
    from app.models import Cliente

    _, tenant_id = user_and_tenant

    drawing = (
        db.query(Drawing)
        .filter(Drawing.id == drawing_id, Drawing.tenant_id == tenant_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, detail="Sorteio não encontrado.")

    entries = (
        db.query(DrawingEntry)
        .filter(DrawingEntry.drawing_id == drawing_id)
        .order_by(DrawingEntry.id.asc())
        .all()
    )
    cids = [e.customer_id for e in entries]
    clientes_map = {}
    if cids:
        for cl in db.query(Cliente).filter(Cliente.id.in_(cids), Cliente.tenant_id == tenant_id).all():
            clientes_map[cl.id] = cl.nome

    # Gera lista com 1 linha por ticket
    tickets = []
    numero = 1
    for e in entries:
        nome = clientes_map.get(e.customer_id, f"Cliente #{e.customer_id}")
        for _ in range(max(1, e.ticket_count)):
            tickets.append({
                "numero": numero,
                "customer_id": e.customer_id,
                "nome": nome,
                "rank_level": e.rank_level.value if e.rank_level else None,
            })
            numero += 1

    return {
        "sorteio_id": drawing.id,
        "sorteio_nome": drawing.name,
        "premio": drawing.prize_description,
        "total_tickets": len(tickets),
        "total_participantes": len(entries),
        "tickets": tickets,
    }


@router.delete("/sorteios/{drawing_id}", status_code=204)
def cancelar_sorteio(
    drawing_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cancela um sorteio que ainda não foi executado."""
    _, tenant_id = user_and_tenant

    drawing = (
        db.query(Drawing)
        .filter(Drawing.id == drawing_id, Drawing.tenant_id == tenant_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, detail="Sorteio não encontrado.")
    if drawing.status == DrawingStatusEnum.drawn:
        raise HTTPException(400, detail="Sorteio já executado não pode ser cancelado.")

    drawing.status = DrawingStatusEnum.cancelled
    db.commit()
    return


# ---------------------------------------------------------------------------
# SPRINT 7 — Envio em lote por nível de ranking
# ---------------------------------------------------------------------------

class EnvioLoteBody(BaseModel):
    nivel: str                     # bronze | silver | gold | diamond | platinum | todos
    assunto: str
    mensagem: str                  # corpo do e-mail / notificação
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
            raise HTTPException(400, detail="Nenhum dado de ranking. Execute o recálculo primeiro.")
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
    clientes = db.query(Cliente).filter(
        Cliente.id.in_(customer_ids),
        Cliente.tenant_id == tenant_id,
        Cliente.email.isnot(None),
    ).all()
    clientes_map = {c.id: c for c in clientes}

    enfileirados = 0
    sem_email = 0
    for r in registros:
        cliente = clientes_map.get(r.customer_id)
        if not cliente or not cliente.email:
            sem_email += 1
            continue

        idempotency_key = f"lote:{tenant_id}:{periodo}:{body.nivel}:{r.customer_id}:{hash(body.assunto)}"
        # Verifica duplicidade
        exists = (
            db.query(NotificationQueue.id)
            .filter(NotificationQueue.idempotency_key == idempotency_key)
            .first()
        )
        if exists:
            continue

        notif = NotificationQueue(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            customer_id=r.customer_id,
            channel=NotificationChannelEnum.email,
            subject=body.assunto,
            body=body.mensagem,
            email_address=cliente.email,
            status=NotificationStatusEnum.pending,
        )
        db.add(notif)
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

def _serialize_cliente_resumo(c):
    return {
        "id": c.id,
        "nome": c.nome,
        "cpf": getattr(c, "cpf", None),
        "telefone": getattr(c, "telefone", None),
        "email": getattr(c, "email", None),
    }


@router.get("/unificacao/sugestoes")
def listar_sugestoes_unificacao(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna pares de clientes que provavelmente são a mesma pessoa,
    identificados por mesmo CPF ou mesmo telefone no mesmo tenant.
    """
    from app.models import Cliente

    _, tenant_id = user_and_tenant
    sugestoes = []
    seen_pairs: set = set()

    # Agrupar clientes com mesmo CPF não-nulo
    cpf_groups: dict = {}
    for c in (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.cpf.isnot(None),
            Cliente.cpf != "",
        )
        .all()
    ):
        cpf_groups.setdefault(c.cpf, []).append(c)

    for cpf_val, grupo in cpf_groups.items():
        if len(grupo) < 2:
            continue
        for i in range(len(grupo)):
            for j in range(i + 1, len(grupo)):
                a, b = grupo[i], grupo[j]
                key = (min(a.id, b.id), max(a.id, b.id))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    sugestoes.append({
                        "motivo": "mesmo_cpf",
                        "cliente_a": _serialize_cliente_resumo(a),
                        "cliente_b": _serialize_cliente_resumo(b),
                    })

    # Agrupar clientes com mesmo telefone não-nulo
    tel_groups: dict = {}
    for c in (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.telefone.isnot(None),
            Cliente.telefone != "",
        )
        .all()
    ):
        tel_normalizado = "".join(d for d in (c.telefone or "") if d.isdigit())
        if len(tel_normalizado) >= 8:
            tel_groups.setdefault(tel_normalizado, []).append(c)

    for tel_val, grupo in tel_groups.items():
        if len(grupo) < 2:
            continue
        for i in range(len(grupo)):
            for j in range(i + 1, len(grupo)):
                a, b = grupo[i], grupo[j]
                key = (min(a.id, b.id), max(a.id, b.id))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    sugestoes.append({
                        "motivo": "mesmo_telefone",
                        "cliente_a": _serialize_cliente_resumo(a),
                        "cliente_b": _serialize_cliente_resumo(b),
                    })

    return sugestoes


class ConfirmarMergeBody(BaseModel):
    customer_keep_id: int
    customer_remove_id: int
    motivo: Optional[str] = "manual"


@router.post("/unificacao/confirmar", status_code=200)
def confirmar_unificacao(
    body: ConfirmarMergeBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Mescla o cliente 'remove' no cliente 'keep':
    - Transfere registros de campanhas (cashback, carimbos, cupons, ranking, sorteios)
    - Cria CustomerMergeLog com snapshot dos IDs movidos (para permitir desfazer)
    """
    from app.models import Cliente

    user, tenant_id = user_and_tenant

    keep = db.query(Cliente).filter(
        Cliente.id == body.customer_keep_id,
        Cliente.tenant_id == tenant_id,
    ).first()
    remove = db.query(Cliente).filter(
        Cliente.id == body.customer_remove_id,
        Cliente.tenant_id == tenant_id,
    ).first()

    if not keep or not remove:
        raise HTTPException(status_code=404, detail="Cliente não encontrado neste tenant.")
    if keep.id == remove.id:
        raise HTTPException(status_code=400, detail="Os clientes devem ser diferentes.")

    # Verificar se já existe merge não desfeito envolvendo estes dois
    existing = db.query(CustomerMergeLog).filter(
        CustomerMergeLog.tenant_id == tenant_id,
        CustomerMergeLog.customer_keep_id == keep.id,
        CustomerMergeLog.customer_remove_id == remove.id,
        CustomerMergeLog.undone.is_(False),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Estes clientes já foram unificados. Desfaça antes de refazer.")

    snapshot: dict = {}

    # Transfere CashbackTransaction
    cashback_ids = [
        r.id for r in db.query(CashbackTransaction.id).filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == remove.id,
        ).all()
    ]
    if cashback_ids:
        db.query(CashbackTransaction).filter(
            CashbackTransaction.id.in_(cashback_ids)
        ).update({"customer_id": keep.id}, synchronize_session=False)
    snapshot["cashback_ids"] = cashback_ids

    # Transfere LoyaltyStamp
    stamp_ids = [
        r.id for r in db.query(LoyaltyStamp.id).filter(
            LoyaltyStamp.tenant_id == tenant_id,
            LoyaltyStamp.customer_id == remove.id,
        ).all()
    ]
    if stamp_ids:
        db.query(LoyaltyStamp).filter(
            LoyaltyStamp.id.in_(stamp_ids)
        ).update({"customer_id": keep.id}, synchronize_session=False)
    snapshot["stamp_ids"] = stamp_ids

    # Transfere Coupon (nominais do cliente removido)
    coupon_ids = [
        r.id for r in db.query(Coupon.id).filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == remove.id,
        ).all()
    ]
    if coupon_ids:
        db.query(Coupon).filter(
            Coupon.id.in_(coupon_ids)
        ).update({"customer_id": keep.id}, synchronize_session=False)
    snapshot["coupon_ids"] = coupon_ids

    # Transfere CustomerRankHistory (remove duplicatas combinando os dados)
    rank_ids = [
        r.id for r in db.query(CustomerRankHistory.id).filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.customer_id == remove.id,
        ).all()
    ]
    if rank_ids:
        db.query(CustomerRankHistory).filter(
            CustomerRankHistory.id.in_(rank_ids)
        ).update({"customer_id": keep.id}, synchronize_session=False)
    snapshot["rank_ids"] = rank_ids

    # Transfere DrawingEntry
    drawing_ids = [
        r.id for r in db.query(DrawingEntry.id).filter(
            DrawingEntry.tenant_id == tenant_id,
            DrawingEntry.customer_id == remove.id,
        ).all()
    ]
    if drawing_ids:
        db.query(DrawingEntry).filter(
            DrawingEntry.id.in_(drawing_ids)
        ).update({"customer_id": keep.id}, synchronize_session=False)
    snapshot["drawing_ids"] = drawing_ids

    # Transfere NotificationQueue (pendentes)
    notif_ids = [
        r.id for r in db.query(NotificationQueue.id).filter(
            NotificationQueue.tenant_id == tenant_id,
            NotificationQueue.customer_id == remove.id,
            NotificationQueue.status == NotificationStatusEnum.pending,
        ).all()
    ]
    if notif_ids:
        db.query(NotificationQueue).filter(
            NotificationQueue.id.in_(notif_ids)
        ).update({"customer_id": keep.id}, synchronize_session=False)
    snapshot["notif_ids"] = notif_ids

    # Transfere Vendas (para ranking e destaque mensal contarem o histórico completo)
    from app.vendas_models import Venda
    venda_ids = [
        r.id for r in db.query(Venda.id).filter(
            Venda.cliente_id == remove.id,
        ).all()
    ]
    if venda_ids:
        db.query(Venda).filter(
            Venda.id.in_(venda_ids)
        ).update({"cliente_id": keep.id}, synchronize_session=False)
    snapshot["venda_ids"] = venda_ids

    # Transfere CampaignExecution (idempotência: evita remissolicitada duplicada)
    # Se já existe execution para o keep com o mesmo (campaign_id, reference_period),
    # apenas descarta a do remove (não podemos ter duplicata pela constraint UNIQUE).
    exec_transferidos = []
    exec_descartados = []
    executions_remove = db.query(CampaignExecution).filter(
        CampaignExecution.tenant_id == tenant_id,
        CampaignExecution.customer_id == remove.id,
    ).all()
    for exc_row in executions_remove:
        conflito = db.query(CampaignExecution).filter(
            CampaignExecution.tenant_id == tenant_id,
            CampaignExecution.campaign_id == exc_row.campaign_id,
            CampaignExecution.customer_id == keep.id,
            CampaignExecution.reference_period == exc_row.reference_period,
        ).first()
        if conflito:
            # keep já tem esse registro — descarta o do remove
            exec_descartados.append(exc_row.id)
            db.delete(exc_row)
        else:
            exc_row.customer_id = keep.id
            exec_transferidos.append(exc_row.id)
    snapshot["exec_transferidos"] = exec_transferidos
    snapshot["exec_descartados"] = exec_descartados

    # Transfere CampaignEventQueue (eventos pendentes do cliente removido)
    event_ids = [
        r.id for r in db.query(CampaignEventQueue.id).filter(
            CampaignEventQueue.tenant_id == tenant_id,
            CampaignEventQueue.status == EventStatusEnum.pending,
            CampaignEventQueue.payload["customer_id"].astext == str(remove.id),
        ).all()
    ]
    if event_ids:
        for ev in db.query(CampaignEventQueue).filter(CampaignEventQueue.id.in_(event_ids)).all():
            payload = dict(ev.payload)
            payload["customer_id"] = keep.id
            ev.payload = payload
    snapshot["event_ids"] = event_ids

    # Copiar CPF para o cliente mantido (se não tiver)
    if not keep.cpf and remove.cpf:
        keep.cpf = remove.cpf

    # Salvar merge log
    merge_log = CustomerMergeLog(
        tenant_id=tenant_id,
        customer_keep_id=keep.id,
        customer_remove_id=remove.id,
        motivo=body.motivo,
        merged_by_user_id=user.id if user else None,
        snapshot_json=snapshot,
        undone=False,
    )
    db.add(merge_log)
    db.commit()
    db.refresh(merge_log)

    return {
        "ok": True,
        "merge_id": merge_log.id,
        "customer_keep": _serialize_cliente_resumo(keep),
        "transferencias": {
            "cashback": len(cashback_ids),
            "carimbos": len(stamp_ids),
            "cupons": len(coupon_ids),
            "ranking": len(rank_ids),
            "sorteios": len(drawing_ids),
            "notificacoes": len(notif_ids),
            "vendas": len(venda_ids),
            "execucoes_campanhas": len(exec_transferidos),
            "execucoes_descartadas": len(exec_descartados),
            "eventos_pendentes": len(event_ids),
        },
    }


@router.delete("/unificacao/{merge_id}", status_code=200)
def desfazer_unificacao(
    merge_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Desfaz uma unificação anterior, restaurando customer_id nas linhas
    que foram movidas (usando o snapshot_json do merge log).
    """
    _, tenant_id = user_and_tenant

    merge_log = db.query(CustomerMergeLog).filter(
        CustomerMergeLog.id == merge_id,
        CustomerMergeLog.tenant_id == tenant_id,
    ).first()
    if not merge_log:
        raise HTTPException(status_code=404, detail="Merge não encontrado.")
    if merge_log.undone:
        raise HTTPException(status_code=400, detail="Este merge já foi desfeito.")

    snap = merge_log.snapshot_json or {}
    remove_id = merge_log.customer_remove_id

    cashback_ids = snap.get("cashback_ids", [])
    if cashback_ids:
        db.query(CashbackTransaction).filter(
            CashbackTransaction.id.in_(cashback_ids)
        ).update({"customer_id": remove_id}, synchronize_session=False)

    stamp_ids = snap.get("stamp_ids", [])
    if stamp_ids:
        db.query(LoyaltyStamp).filter(
            LoyaltyStamp.id.in_(stamp_ids)
        ).update({"customer_id": remove_id}, synchronize_session=False)

    coupon_ids = snap.get("coupon_ids", [])
    if coupon_ids:
        db.query(Coupon).filter(
            Coupon.id.in_(coupon_ids)
        ).update({"customer_id": remove_id}, synchronize_session=False)

    rank_ids = snap.get("rank_ids", [])
    if rank_ids:
        db.query(CustomerRankHistory).filter(
            CustomerRankHistory.id.in_(rank_ids)
        ).update({"customer_id": remove_id}, synchronize_session=False)

    drawing_ids = snap.get("drawing_ids", [])
    if drawing_ids:
        db.query(DrawingEntry).filter(
            DrawingEntry.id.in_(drawing_ids)
        ).update({"customer_id": remove_id}, synchronize_session=False)

    notif_ids = snap.get("notif_ids", [])
    if notif_ids:
        db.query(NotificationQueue).filter(
            NotificationQueue.id.in_(notif_ids)
        ).update({"customer_id": remove_id}, synchronize_session=False)

    # Restaura Vendas
    from app.vendas_models import Venda
    venda_ids = snap.get("venda_ids", [])
    if venda_ids:
        db.query(Venda).filter(
            Venda.id.in_(venda_ids)
        ).update({"cliente_id": remove_id}, synchronize_session=False)

    # Restaura CampaignExecution (apenas os transferidos; os descartados são perdidos)
    exec_transferidos = snap.get("exec_transferidos", [])
    if exec_transferidos:
        db.query(CampaignExecution).filter(
            CampaignExecution.id.in_(exec_transferidos)
        ).update({"customer_id": remove_id}, synchronize_session=False)

    # Restaura CampaignEventQueue (recoloca customer_id original no payload)
    event_ids = snap.get("event_ids", [])
    if event_ids:
        for ev in db.query(CampaignEventQueue).filter(CampaignEventQueue.id.in_(event_ids)).all():
            payload = dict(ev.payload)
            payload["customer_id"] = remove_id
            ev.payload = payload

    merge_log.undone = True
    merge_log.undone_at = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True, "merge_id": merge_log.id, "desfeito": True}


# ---------------------------------------------------------------------------
# Sprint 9 — Envio Escalonado para Clientes Inativos
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
        r[0] for r in db.query(VendaModel.cliente_id)
        .filter(
            VendaModel.tenant_id == tenant_id,
            VendaModel.cliente_id.isnot(None),
            VendaModel.status == "finalizada",
            VendaModel.data_venda >= corte,
        ).distinct().all()
    )

    # Todos com pelo menos 1 venda
    todos_ids = set(
        r[0] for r in db.query(VendaModel.cliente_id)
        .filter(
            VendaModel.tenant_id == tenant_id,
            VendaModel.cliente_id.isnot(None),
            VendaModel.status == "finalizada",
        ).distinct().all()
    )

    inativos_ids = list(todos_ids - ativos_ids)
    if not inativos_ids:
        return {"ok": True, "enfileirados": 0, "sem_email": 0, "total_inativos": 0}

    clientes = db.query(Cliente).filter(
        Cliente.id.in_(inativos_ids),
        Cliente.tenant_id == tenant_id,
        Cliente.email.isnot(None),
    ).all()

    enfileirados = 0
    sem_email = len(inativos_ids) - len(clientes)

    for cliente in clientes:
        idempotency_key = (
            f"inativos:{tenant_id}:{body.dias_sem_compra}:{cliente.id}:{date.today().isoformat()}"
        )
        exists = (
            db.query(NotificationQueue.id)
            .filter(NotificationQueue.idempotency_key == idempotency_key)
            .first()
        )
        if exists:
            continue

        notif = NotificationQueue(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            customer_id=cliente.id,
            channel=NotificationChannelEnum.email,
            subject=body.assunto,
            body=body.mensagem,
            email_address=cliente.email,
            status=NotificationStatusEnum.pending,
        )
        db.add(notif)
        enfileirados += 1

    db.commit()
    return {
        "ok": True,
        "enfileirados": enfileirados,
        "sem_email": sem_email,
        "total_inativos": len(inativos_ids),
        "dias_sem_compra": body.dias_sem_compra,
    }

