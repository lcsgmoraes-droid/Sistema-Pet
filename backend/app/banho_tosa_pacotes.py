"""Regras de pacotes, creditos e recorrencias do Banho & Tosa."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_models import (
    BanhoTosaAtendimento,
    BanhoTosaPacoteCredito,
    BanhoTosaPacoteMovimento,
)


def calcular_saldo_creditos(total, usados=0, cancelados=0) -> Decimal:
    saldo = _decimal(total) - _decimal(usados) - _decimal(cancelados)
    return max(saldo, Decimal("0"))


def calcular_validade_pacote(data_inicio: date, validade_dias: int) -> date:
    return data_inicio + timedelta(days=max(int(validade_dias or 1), 1))


def credito_disponivel(credito, hoje: date | None = None) -> bool:
    hoje = hoje or date.today()
    return (
        credito.status == "ativo"
        and credito.data_validade >= hoje
        and calcular_saldo_creditos(credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados) > 0
    )


def consumir_credito_atendimento(db: Session, tenant_id, credito_id: int, atendimento_id: int, quantidade, user_id=None, observacoes=None):
    credito = _obter_credito(db, tenant_id, credito_id)
    atendimento = _obter_atendimento(db, tenant_id, atendimento_id)
    _validar_credito_para_atendimento(credito, atendimento)

    movimento_existente = _movimento_consumo_ativo_atendimento(db, tenant_id, atendimento_id)
    if movimento_existente:
        if movimento_existente.credito_id != credito.id:
            raise HTTPException(status_code=409, detail="Atendimento ja consumiu outro pacote.")
        return credito, movimento_existente, True

    quantidade = _decimal(quantidade)
    saldo_atual = calcular_saldo_creditos(credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados)
    if quantidade <= 0:
        raise HTTPException(status_code=422, detail="Quantidade de creditos deve ser maior que zero.")
    if quantidade > saldo_atual:
        raise HTTPException(status_code=422, detail="Pacote sem saldo suficiente para esse atendimento.")
    if atendimento.venda_id:
        raise HTTPException(status_code=422, detail="Atendimento ja possui venda vinculada; ajuste o PDV antes de consumir pacote.")

    credito.creditos_usados = _decimal(credito.creditos_usados) + quantidade
    saldo_apos = calcular_saldo_creditos(credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados)
    if saldo_apos <= 0:
        credito.status = "esgotado"

    movimento = BanhoTosaPacoteMovimento(
        tenant_id=tenant_id,
        credito_id=credito.id,
        atendimento_id=atendimento.id,
        tipo="consumo",
        quantidade=quantidade,
        saldo_apos=saldo_apos,
        observacoes=observacoes,
        created_by=user_id,
    )
    db.add(movimento)
    db.flush()

    atendimento.pacote_credito_id = credito.id
    atendimento.pacote_movimento_id = movimento.id
    db.commit()
    db.refresh(credito)
    db.refresh(movimento)
    return credito, movimento, False


def estornar_consumo_atendimento(db: Session, tenant_id, credito_id: int, atendimento_id=None, movimento_id=None, user_id=None, observacoes=None):
    credito = _obter_credito(db, tenant_id, credito_id)
    movimento = _obter_movimento_estornavel(db, tenant_id, credito_id, atendimento_id, movimento_id)
    estorno_existente = db.query(BanhoTosaPacoteMovimento).filter(
        BanhoTosaPacoteMovimento.tenant_id == tenant_id,
        BanhoTosaPacoteMovimento.movimento_origem_id == movimento.id,
        BanhoTosaPacoteMovimento.tipo == "estorno",
    ).first()
    if estorno_existente:
        return credito, estorno_existente, True

    quantidade = _decimal(movimento.quantidade)
    credito.creditos_usados = max(_decimal(credito.creditos_usados) - quantidade, Decimal("0"))
    if credito.status == "esgotado":
        credito.status = "ativo"

    saldo_apos = calcular_saldo_creditos(credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados)
    estorno = BanhoTosaPacoteMovimento(
        tenant_id=tenant_id,
        credito_id=credito.id,
        atendimento_id=movimento.atendimento_id,
        movimento_origem_id=movimento.id,
        tipo="estorno",
        quantidade=quantidade,
        saldo_apos=saldo_apos,
        observacoes=observacoes,
        created_by=user_id,
    )
    db.add(estorno)

    atendimento = _obter_atendimento(db, tenant_id, movimento.atendimento_id) if movimento.atendimento_id else None
    if atendimento and atendimento.pacote_movimento_id == movimento.id:
        atendimento.pacote_credito_id = None
        atendimento.pacote_movimento_id = None

    db.commit()
    db.refresh(credito)
    db.refresh(estorno)
    return credito, estorno, False


def _validar_credito_para_atendimento(credito, atendimento) -> None:
    if not credito_disponivel(credito):
        raise HTTPException(status_code=422, detail="Credito de pacote indisponivel, vencido ou sem saldo.")
    if credito.pet_id and credito.pet_id != atendimento.pet_id:
        raise HTTPException(status_code=422, detail="Credito pertence a outro pet.")
    if credito.cliente_id != atendimento.cliente_id:
        raise HTTPException(status_code=422, detail="Credito pertence a outro tutor.")
    if atendimento.status in {"cancelado", "no_show"}:
        raise HTTPException(status_code=422, detail="Atendimento cancelado/no-show nao consome pacote.")
    if credito.pacote and credito.pacote.servico_id and not _atendimento_tem_servico(atendimento, credito.pacote.servico_id):
        raise HTTPException(status_code=422, detail="Pacote nao cobre o servico desse atendimento.")


def _atendimento_tem_servico(atendimento, servico_id: int) -> bool:
    servicos = getattr(getattr(atendimento, "agendamento", None), "servicos", []) or []
    return not servicos or any(item.servico_id == servico_id for item in servicos)


def _obter_credito(db: Session, tenant_id, credito_id: int):
    credito = db.query(BanhoTosaPacoteCredito).options(
        joinedload(BanhoTosaPacoteCredito.pacote),
        joinedload(BanhoTosaPacoteCredito.cliente),
        joinedload(BanhoTosaPacoteCredito.pet),
    ).filter(BanhoTosaPacoteCredito.id == credito_id, BanhoTosaPacoteCredito.tenant_id == tenant_id).first()
    if not credito:
        raise HTTPException(status_code=404, detail="Credito de pacote nao encontrado.")
    return credito


def _obter_atendimento(db: Session, tenant_id, atendimento_id: int):
    atendimento = db.query(BanhoTosaAtendimento).options(joinedload(BanhoTosaAtendimento.agendamento)).filter(
        BanhoTosaAtendimento.id == atendimento_id,
        BanhoTosaAtendimento.tenant_id == tenant_id,
    ).first()
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado.")
    return atendimento


def _obter_movimento_estornavel(db: Session, tenant_id, credito_id: int, atendimento_id=None, movimento_id=None):
    query = db.query(BanhoTosaPacoteMovimento).filter(
        BanhoTosaPacoteMovimento.tenant_id == tenant_id,
        BanhoTosaPacoteMovimento.credito_id == credito_id,
        BanhoTosaPacoteMovimento.tipo == "consumo",
    )
    if movimento_id:
        query = query.filter(BanhoTosaPacoteMovimento.id == movimento_id)
    elif atendimento_id:
        atendimento = _obter_atendimento(db, tenant_id, atendimento_id)
        if atendimento.pacote_movimento_id:
            query = query.filter(BanhoTosaPacoteMovimento.id == atendimento.pacote_movimento_id)
        else:
            query = query.filter(BanhoTosaPacoteMovimento.atendimento_id == atendimento_id)
    else:
        raise HTTPException(status_code=422, detail="Informe atendimento_id ou movimento_id para estornar.")
    movimento = query.order_by(BanhoTosaPacoteMovimento.id.desc()).first()
    if not movimento:
        raise HTTPException(status_code=404, detail="Consumo de pacote nao encontrado.")
    return movimento


def _movimento_consumo_ativo_atendimento(db: Session, tenant_id, atendimento_id: int):
    consumos = db.query(BanhoTosaPacoteMovimento).filter(
        BanhoTosaPacoteMovimento.tenant_id == tenant_id,
        BanhoTosaPacoteMovimento.atendimento_id == atendimento_id,
        BanhoTosaPacoteMovimento.tipo == "consumo",
    ).order_by(BanhoTosaPacoteMovimento.id.desc()).all()
    for movimento in consumos:
        estornado = db.query(BanhoTosaPacoteMovimento.id).filter(
            BanhoTosaPacoteMovimento.tenant_id == tenant_id,
            BanhoTosaPacoteMovimento.movimento_origem_id == movimento.id,
            BanhoTosaPacoteMovimento.tipo == "estorno",
        ).first()
        if not estornado:
            return movimento
    return None


def _decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
