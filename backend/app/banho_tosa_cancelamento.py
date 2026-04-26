"""Cancelamento operacional do fluxo Banho & Tosa."""

from datetime import datetime
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_models import BanhoTosaAtendimento, BanhoTosaEtapa
from app.banho_tosa_pacotes import estornar_consumo_atendimento
from app.vendas.service import VendaService
from app.vendas_models import Venda


def cancelar_processo_atendimento(db: Session, tenant_id, user_id: int, atendimento_id: int, motivo: str) -> dict:
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 3:
        raise HTTPException(status_code=422, detail="Informe um motivo para o cancelamento.")

    atendimento = _obter_atendimento(db, tenant_id, atendimento_id)
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado.")

    vendas = _listar_vendas_vinculadas(db, tenant_id, atendimento)
    vendas_canceladas = 0
    vendas_ja_canceladas = 0
    venda_ids = [venda.id for venda in vendas]

    for venda in vendas:
        if venda.status == "cancelada":
            vendas_ja_canceladas += 1
            continue

        VendaService.cancelar_venda(
            venda_id=venda.id,
            motivo=f"Cancelamento Banho & Tosa atendimento #{atendimento.id}: {motivo_limpo}",
            user_id=venda.user_id or user_id,
            tenant_id=tenant_id,
            db=db,
        )
        vendas_canceladas += 1

    pacote_estornado = False
    atendimento = _obter_atendimento(db, tenant_id, atendimento_id)
    if atendimento.pacote_credito_id and atendimento.pacote_movimento_id:
        estornar_consumo_atendimento(
            db,
            tenant_id,
            atendimento.pacote_credito_id,
            atendimento_id=atendimento.id,
            movimento_id=atendimento.pacote_movimento_id,
            user_id=user_id,
            observacoes=f"Cancelamento do atendimento: {motivo_limpo}",
        )
        pacote_estornado = True
        atendimento = _obter_atendimento(db, tenant_id, atendimento_id)

    agora = datetime.now()
    atendimento.status = "cancelado"
    atendimento.conta_receber_id = None
    atendimento.observacoes_saida = _append_observacao(
        atendimento.observacoes_saida,
        f"Cancelado em {agora.strftime('%d/%m/%Y %H:%M')}: {motivo_limpo}",
    )
    _finalizar_etapas_abertas(atendimento.etapas, agora)

    if atendimento.agendamento:
        atendimento.agendamento.status = "cancelado"
        atendimento.agendamento.observacoes = _append_observacao(
            atendimento.agendamento.observacoes,
            f"Processo cancelado pelo atendimento #{atendimento.id}: {motivo_limpo}",
        )

    db.commit()
    db.refresh(atendimento)

    return {
        "atendimento_id": atendimento.id,
        "status_atendimento": atendimento.status,
        "agendamento_id": atendimento.agendamento_id,
        "status_agendamento": atendimento.agendamento.status if atendimento.agendamento else None,
        "venda_ids": venda_ids,
        "vendas_canceladas": vendas_canceladas,
        "vendas_ja_canceladas": vendas_ja_canceladas,
        "pacote_estornado": pacote_estornado,
        "mensagem": "Processo de Banho & Tosa cancelado com sucesso.",
    }


def _obter_atendimento(db: Session, tenant_id, atendimento_id: int):
    return (
        db.query(BanhoTosaAtendimento)
        .options(
            joinedload(BanhoTosaAtendimento.agendamento),
            joinedload(BanhoTosaAtendimento.venda),
            joinedload(BanhoTosaAtendimento.etapas),
        )
        .filter(BanhoTosaAtendimento.id == atendimento_id, BanhoTosaAtendimento.tenant_id == tenant_id)
        .first()
    )


def _listar_vendas_vinculadas(db: Session, tenant_id, atendimento: BanhoTosaAtendimento) -> list[Venda]:
    filtros = []
    if atendimento.venda_id:
        filtros.append(Venda.id == atendimento.venda_id)

    token = f"BT_ATENDIMENTO:{atendimento.id}"
    filtros.append(Venda.observacoes.contains(token))

    vendas = (
        db.query(Venda)
        .filter(Venda.tenant_id == tenant_id, or_(*filtros))
        .order_by(Venda.id.asc())
        .all()
    )
    return _deduplicar_vendas(vendas)


def _deduplicar_vendas(vendas: Iterable[Venda]) -> list[Venda]:
    vistas = set()
    unicas = []
    for venda in vendas:
        if venda.id in vistas:
            continue
        vistas.add(venda.id)
        unicas.append(venda)
    return unicas


def _append_observacao(atual: str | None, texto: str) -> str:
    if not atual:
        return texto
    if texto in atual:
        return atual
    return f"{atual}\n{texto}"


def _finalizar_etapas_abertas(etapas: Iterable[BanhoTosaEtapa], fim: datetime) -> None:
    for etapa in etapas or []:
        if etapa.fim_em:
            continue
        etapa.fim_em = fim
        if etapa.inicio_em:
            etapa.duracao_minutos = max(0, int((fim - etapa.inicio_em).total_seconds() // 60))
