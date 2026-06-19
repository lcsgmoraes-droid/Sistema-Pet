"""
Rotas de sorteios das campanhas.

Sub-router incluido por ``app.campaigns.routes`` sob o prefixo ``/campanhas``.
"""

import secrets
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.models import (
    CustomerRankHistory,
    Drawing,
    DrawingEntry,
    DrawingStatusEnum,
    RankLevelEnum,
)
from app.db import SessionLocal


router = APIRouter()
SORTEIO_NAO_ENCONTRADO = "Sorteio não encontrado."


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# SPRINT 7 — Sorteios
# ---------------------------------------------------------------------------


class CriarSorteioBody(BaseModel):
    name: str
    description: Optional[str] = None
    prize_description: Optional[str] = None
    rank_filter: Optional[str] = None
    draw_date: Optional[str] = None
    auto_execute: bool = False


class EditarSorteioBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prize_description: Optional[str] = None
    rank_filter: Optional[str] = None
    draw_date: Optional[str] = None
    auto_execute: Optional[bool] = None


def _parse_rank_filter(
    value: str | None, *, detail_prefix: str
) -> RankLevelEnum | None:
    if not value:
        return None
    try:
        return RankLevelEnum(value)
    except ValueError as exc:
        raise HTTPException(400, detail=f"{detail_prefix}: {value}") from exc


def _parse_draw_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(400, detail="draw_date inválido (use ISO 8601)") from exc


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
        "entries_frozen_at": d.entries_frozen_at.isoformat()
        if d.entries_frozen_at
        else None,
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

    rank_filter = _parse_rank_filter(
        body.rank_filter, detail_prefix="Nível de ranking inválido"
    )
    draw_date = _parse_draw_date(body.draw_date)

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
        raise HTTPException(404, detail=SORTEIO_NAO_ENCONTRADO)
    if drawing.status == DrawingStatusEnum.drawn:
        raise HTTPException(400, detail="Sorteio já executado não pode ser editado.")

    if body.name is not None:
        drawing.name = body.name.strip()
    if body.description is not None:
        drawing.description = body.description
    if body.prize_description is not None:
        drawing.prize_description = body.prize_description
    if body.rank_filter is not None:
        drawing.rank_filter = _parse_rank_filter(
            body.rank_filter, detail_prefix="Nível inválido"
        )
    if body.draw_date is not None:
        drawing.draw_date = _parse_draw_date(body.draw_date)
    if body.auto_execute is not None:
        drawing.auto_execute = body.auto_execute

    db.commit()
    db.refresh(drawing)

    entry_count = (
        db.query(DrawingEntry).filter(DrawingEntry.drawing_id == drawing_id).count()
    )
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
        raise HTTPException(404, detail=SORTEIO_NAO_ENCONTRADO)
    if drawing.status in (DrawingStatusEnum.drawn, DrawingStatusEnum.cancelled):
        raise HTTPException(
            400,
            detail=f"Sorteio em status '{drawing.status.value}' não aceita inscrições.",
        )

    # Descobrir período mais recente do ranking
    ultimo_periodo = (
        db.query(CustomerRankHistory.period)
        .filter(CustomerRankHistory.tenant_id == tenant_id)
        .order_by(CustomerRankHistory.period.desc())
        .first()
    )
    if not ultimo_periodo:
        raise HTTPException(
            400,
            detail="Nenhum dado de ranking disponível. Execute o recálculo primeiro.",
        )
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
    ja_inscritos = {
        row[0]
        for row in db.query(DrawingEntry.customer_id)
        .filter(DrawingEntry.drawing_id == drawing_id)
        .all()
    }

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
    Executa o sorteio e grava um identificador auditável (seed_uuid).

    Algoritmo:
    1. Congela a lista de participantes (hash SHA-256)
    2. Gera seed_uuid de auditoria
    3. Seleciona o ganhador com gerador criptograficamente seguro
    4. Sorteia 1 ganhador por peso (ticket_count)
    5. Grava resultado e muda status para 'drawn'
    """
    import hashlib

    _, tenant_id = user_and_tenant

    drawing = (
        db.query(Drawing)
        .filter(Drawing.id == drawing_id, Drawing.tenant_id == tenant_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, detail=SORTEIO_NAO_ENCONTRADO)
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

    # Identificador auditável do sorteio executado.
    seed_uuid = _uuid.uuid4()

    # Construir pool com pesos (ticket_count)
    pool = []
    for e in entries:
        pool.extend([e] * max(1, e.ticket_count))

    winner_entry = secrets.choice(pool)

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

    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == winner_entry.customer_id, Cliente.tenant_id == tenant_id)
        .first()
    )

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
        "winner_name": cliente.nome
        if cliente
        else f"Cliente #{winner_entry.customer_id}",
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
        raise HTTPException(404, detail=SORTEIO_NAO_ENCONTRADO)

    entries = (
        db.query(DrawingEntry)
        .filter(DrawingEntry.drawing_id == drawing_id)
        .order_by(DrawingEntry.registered_at.asc())
        .all()
    )

    customer_ids = [e.customer_id for e in entries]
    clientes_map = {}
    if customer_ids:
        clientes = (
            db.query(Cliente)
            .filter(Cliente.id.in_(customer_ids), Cliente.tenant_id == tenant_id)
            .all()
        )
        clientes_map = {c.id: c.nome for c in clientes}

    winner_customer_id = None
    if drawing.winner_entry_id:
        winner_entry = next(
            (e for e in entries if e.id == drawing.winner_entry_id), None
        )
        if winner_entry:
            winner_customer_id = winner_entry.customer_id

    return {
        "drawing": _drawing_to_dict(drawing, len(entries)),
        "winner_customer_id": winner_customer_id,
        "winner_name": clientes_map.get(
            winner_customer_id, f"Cliente #{winner_customer_id}"
        )
        if winner_customer_id
        else None,
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
        raise HTTPException(404, detail=SORTEIO_NAO_ENCONTRADO)

    entries = (
        db.query(DrawingEntry)
        .filter(DrawingEntry.drawing_id == drawing_id)
        .order_by(DrawingEntry.id.asc())
        .all()
    )
    cids = [e.customer_id for e in entries]
    clientes_map = {}
    if cids:
        for cl in (
            db.query(Cliente)
            .filter(Cliente.id.in_(cids), Cliente.tenant_id == tenant_id)
            .all()
        ):
            clientes_map[cl.id] = cl.nome

    # Gera lista com 1 linha por ticket
    tickets = []
    numero = 1
    for e in entries:
        nome = clientes_map.get(e.customer_id, f"Cliente #{e.customer_id}")
        for _ in range(max(1, e.ticket_count)):
            tickets.append(
                {
                    "numero": numero,
                    "customer_id": e.customer_id,
                    "nome": nome,
                    "rank_level": e.rank_level.value if e.rank_level else None,
                }
            )
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
        raise HTTPException(404, detail=SORTEIO_NAO_ENCONTRADO)
    if drawing.status == DrawingStatusEnum.drawn:
        raise HTTPException(400, detail="Sorteio já executado não pode ser cancelado.")

    drawing.status = DrawingStatusEnum.cancelled
    db.commit()
