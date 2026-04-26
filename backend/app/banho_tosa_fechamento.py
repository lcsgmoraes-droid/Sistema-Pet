"""Sincronizacao financeira do atendimento de Banho & Tosa."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_models import BanhoTosaAtendimento
from app.financeiro_models import ContaReceber
from app.vendas_models import Venda


def sincronizar_fechamento_atendimento(db: Session, tenant_id, atendimento_id: int) -> dict:
    atendimento = _obter_atendimento(db, tenant_id, atendimento_id)
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado")

    if not atendimento.venda_id:
        return _resumo_sem_venda(atendimento)

    venda = atendimento.venda
    contas = _listar_contas_receber(db, tenant_id, atendimento.venda_id)
    conta_referencia = _escolher_conta_referencia(contas)
    sincronizado = False

    if conta_referencia and atendimento.conta_receber_id != conta_referencia.id:
        atendimento.conta_receber_id = conta_referencia.id
        db.commit()
        sincronizado = True

    return montar_resumo_fechamento(atendimento, venda, contas, sincronizado=sincronizado)


def listar_pendencias_fechamento(db: Session, tenant_id, limit: int = 200) -> dict:
    atendimentos = _query_pendencias(db, tenant_id).limit(limit).all()
    contas_por_venda = _contas_por_venda(db, tenant_id, [item.venda_id for item in atendimentos if item.venda_id])
    itens = [_montar_pendencia(item, contas_por_venda.get(item.venda_id, [])) for item in atendimentos]
    return {"total": len(itens), "itens": itens}


def sincronizar_pendencias_fechamento(db: Session, tenant_id, limit: int = 200) -> dict:
    pendencias = listar_pendencias_fechamento(db, tenant_id, limit)["itens"]
    sincronizados = 0
    sem_venda = 0
    for item in pendencias:
        if not item["venda_id"]:
            sem_venda += 1
            continue
        resumo = sincronizar_fechamento_atendimento(db, tenant_id, item["atendimento_id"])
        if resumo.get("sincronizado"):
            sincronizados += 1

    restantes = listar_pendencias_fechamento(db, tenant_id, limit)["total"]
    return {
        "total_processados": len(pendencias),
        "sincronizados": sincronizados,
        "sem_venda": sem_venda,
        "pendentes_restantes": restantes,
    }


def montar_resumo_fechamento(atendimento, venda=None, contas=None, sincronizado=False) -> dict:
    venda = venda or getattr(atendimento, "venda", None)
    contas = contas if contas is not None else []
    if not venda:
        return _resumo_sem_venda(atendimento)

    total = Decimal(str(venda.total or 0))
    total_pago = sum(Decimal(str(pag.valor or 0)) for pag in venda.pagamentos or [])
    valor_restante = max(total - total_pago, Decimal("0"))
    status_pagamento = _status_pagamento(total, total_pago)
    alertas = _montar_alertas(atendimento, venda, status_pagamento, contas)

    return {
        "atendimento_id": atendimento.id,
        "venda_id": venda.id,
        "conta_receber_id": atendimento.conta_receber_id,
        "venda_status": venda.status,
        "status_pagamento": status_pagamento,
        "total": total,
        "total_pago": total_pago,
        "valor_restante": valor_restante,
        "contas_receber_total": len(contas),
        "contas_receber_pendentes": len([c for c in contas if c.status in {"pendente", "parcial", "vencido"}]),
        "contas_receber_recebidas": len([c for c in contas if c.status == "recebido"]),
        "sincronizado": sincronizado,
        "alertas": alertas,
    }


def _query_pendencias(db: Session, tenant_id):
    return (
        db.query(BanhoTosaAtendimento)
        .outerjoin(Venda, BanhoTosaAtendimento.venda_id == Venda.id)
        .options(
            joinedload(BanhoTosaAtendimento.cliente),
            joinedload(BanhoTosaAtendimento.pet),
            joinedload(BanhoTosaAtendimento.venda).joinedload(Venda.pagamentos),
        )
        .filter(
            BanhoTosaAtendimento.tenant_id == tenant_id,
            BanhoTosaAtendimento.status.in_(["pronto", "entregue"]),
            BanhoTosaAtendimento.pacote_credito_id.is_(None),
            or_(
                BanhoTosaAtendimento.venda_id.is_(None),
                BanhoTosaAtendimento.conta_receber_id.is_(None),
                Venda.status.in_(["aberta", "baixa_parcial", "cancelada"]),
            ),
        )
        .order_by(BanhoTosaAtendimento.id.desc())
    )


def _contas_por_venda(db: Session, tenant_id, venda_ids: list[int]) -> dict[int, list[ContaReceber]]:
    if not venda_ids:
        return {}
    contas = (
        db.query(ContaReceber)
        .filter(ContaReceber.tenant_id == tenant_id, ContaReceber.venda_id.in_(venda_ids))
        .order_by(ContaReceber.data_vencimento.asc(), ContaReceber.id.asc())
        .all()
    )
    agrupadas = {}
    for conta in contas:
        agrupadas.setdefault(conta.venda_id, []).append(conta)
    return agrupadas


def _montar_pendencia(atendimento, contas: list[ContaReceber]) -> dict:
    resumo = montar_resumo_fechamento(atendimento, atendimento.venda, contas, sincronizado=False)
    venda = atendimento.venda
    return {
        **resumo,
        "cliente_id": atendimento.cliente_id,
        "cliente_nome": atendimento.cliente.nome if atendimento.cliente else None,
        "pet_id": atendimento.pet_id,
        "pet_nome": atendimento.pet.nome if atendimento.pet else None,
        "status_atendimento": atendimento.status,
        "checkin_em": atendimento.checkin_em,
        "fim_em": atendimento.fim_em,
        "entregue_em": atendimento.entregue_em,
        "venda_numero": venda.numero_venda if venda else None,
        "pdv_url": f"/pdv?venda_id={atendimento.venda_id}" if atendimento.venda_id else None,
    }


def _obter_atendimento(db: Session, tenant_id, atendimento_id: int):
    return (
        db.query(BanhoTosaAtendimento)
        .options(joinedload(BanhoTosaAtendimento.venda).joinedload(Venda.pagamentos))
        .filter(BanhoTosaAtendimento.id == atendimento_id, BanhoTosaAtendimento.tenant_id == tenant_id)
        .first()
    )


def _listar_contas_receber(db: Session, tenant_id, venda_id: int) -> list[ContaReceber]:
    return (
        db.query(ContaReceber)
        .filter(ContaReceber.tenant_id == tenant_id, ContaReceber.venda_id == venda_id)
        .order_by(ContaReceber.data_vencimento.asc(), ContaReceber.id.asc())
        .all()
    )


def _escolher_conta_referencia(contas: list[ContaReceber]):
    if not contas:
        return None
    pendentes = [conta for conta in contas if conta.status in {"pendente", "parcial", "vencido"}]
    return pendentes[0] if pendentes else contas[0]


def _status_pagamento(total: Decimal, total_pago: Decimal) -> str:
    if total <= 0:
        return "sem_valor"
    if total_pago >= total - Decimal("0.01"):
        return "pago"
    if total_pago > 0:
        return "parcial"
    return "pendente"


def _montar_alertas(atendimento, venda, status_pagamento: str, contas: list[ContaReceber]) -> list[str]:
    alertas = []
    if venda.status == "cancelada":
        alertas.append("Venda vinculada foi cancelada.")
    if atendimento.status in {"pronto", "entregue"} and venda.status in {"aberta", "baixa_parcial"}:
        alertas.append("Atendimento pronto/entregue com cobranca ainda nao finalizada no PDV.")
    if status_pagamento in {"pendente", "parcial"}:
        alertas.append("Pagamento ainda nao cobre o valor total do atendimento.")
    if venda.status == "finalizada" and not contas:
        alertas.append("Venda finalizada sem conta a receber localizada; sincronize/valide o financeiro.")
    return alertas


def _resumo_sem_venda(atendimento) -> dict:
    if atendimento.pacote_credito_id:
        return {
            "atendimento_id": atendimento.id,
            "venda_id": None,
            "conta_receber_id": atendimento.conta_receber_id,
            "venda_status": None,
            "status_pagamento": "quitado_pacote",
            "total": Decimal("0"),
            "total_pago": Decimal("0"),
            "valor_restante": Decimal("0"),
            "contas_receber_total": 0,
            "contas_receber_pendentes": 0,
            "contas_receber_recebidas": 0,
            "sincronizado": False,
            "alertas": [],
        }
    alertas = []
    if atendimento.status in {"pronto", "entregue"}:
        alertas.append("Atendimento pronto/entregue sem venda vinculada.")
    return {
        "atendimento_id": atendimento.id,
        "venda_id": None,
        "conta_receber_id": atendimento.conta_receber_id,
        "venda_status": None,
        "status_pagamento": "sem_venda",
        "total": Decimal("0"),
        "total_pago": Decimal("0"),
        "valor_restante": Decimal("0"),
        "contas_receber_total": 0,
        "contas_receber_pendentes": 0,
        "contas_receber_recebidas": 0,
        "sincronizado": False,
        "alertas": alertas,
    }
