"""Sincronizacao financeira do atendimento de Banho & Tosa."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_models import BanhoTosaAtendimento
from app.banho_tosa_entrega import entrega_sem_cobranca_registrada
from app.banho_tosa_vendas import _montar_itens_venda
from app.financeiro_models import ContaReceber
from app.vendas_models import Venda


TAMANHO_LOTE_PENDENCIAS = 200
MAX_PAGINAS_PENDENCIAS = 50


def sincronizar_fechamento_atendimento(
    db: Session, tenant_id, atendimento_id: int
) -> dict:
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

    return montar_resumo_fechamento(
        atendimento, venda, contas, sincronizado=sincronizado
    )


def listar_pendencias_fechamento(
    db: Session, tenant_id, limit: int = 200, cursor: int | None = None
) -> dict:
    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise HTTPException(
            422, "O limite de pendencias deve ser um inteiro entre 1 e 500."
        )
    if cursor is not None and (not isinstance(cursor, int) or cursor <= 0):
        raise HTTPException(422, "O cursor deve ser um inteiro positivo.")
    query = _query_pendencias(db, tenant_id)
    atendimentos, proximo_cursor = _buscar_pendencias_limitadas(
        db, tenant_id, query, limit, cursor
    )
    contas_por_venda = _contas_por_venda(
        db, tenant_id, [item.venda_id for item in atendimentos if item.venda_id]
    )
    itens = [
        _montar_pendencia(item, contas_por_venda.get(item.venda_id, []))
        for item in atendimentos
    ]
    return {
        "total": len(itens),
        "itens": itens,
        "proximo_cursor": proximo_cursor,
        "busca_incompleta": proximo_cursor is not None,
    }


def _buscar_pendencias_limitadas(db, tenant_id, query, limit, cursor):
    atendimentos = []
    ultimo_id = cursor
    # O custo da busca tem limite proprio, independente do parametro da URL.
    for _ in range(MAX_PAGINAS_PENDENCIAS):
        pagina = query
        if ultimo_id is not None:
            pagina = pagina.filter(BanhoTosaAtendimento.id < ultimo_id)
        lote = pagina.limit(TAMANHO_LOTE_PENDENCIAS).all()
        if not lote:
            return atendimentos, None
        encontrados, ultimo_id = _filtrar_lote_pendencias(
            db, tenant_id, lote, limit - len(atendimentos)
        )
        atendimentos.extend(encontrados)
        if len(atendimentos) == limit:
            return atendimentos, _cursor_pendencias_anteriores(query, ultimo_id)
        if len(lote) < TAMANHO_LOTE_PENDENCIAS:
            return atendimentos, None
    return atendimentos, _cursor_pendencias_anteriores(query, ultimo_id)


def _filtrar_lote_pendencias(db, tenant_id, lote, vagas):
    encontrados = []
    for item in lote:
        if _atendimento_tem_pendencia(db, tenant_id, item):
            encontrados.append(item)
        if len(encontrados) == vagas:
            return encontrados, item.id
    return encontrados, lote[-1].id


def _atendimento_tem_pendencia(db, tenant_id, item):
    if item.venda_id:
        return True
    if entrega_sem_cobranca_registrada(item):
        return False
    return not (item.pacote_credito_id and not _montar_itens_venda(db, tenant_id, item))


def _cursor_pendencias_anteriores(query, ultimo_id):
    if query.filter(BanhoTosaAtendimento.id < ultimo_id).first() is not None:
        return ultimo_id
    return None


def sincronizar_pendencias_fechamento(
    db: Session, tenant_id, limit: int = 200, cursor: int | None = None
) -> dict:
    resultado = listar_pendencias_fechamento(db, tenant_id, limit, cursor)
    pendencias = resultado["itens"]
    sincronizados = 0
    sem_venda = 0
    for item in pendencias:
        if not item["venda_id"]:
            sem_venda += 1
            continue
        resumo = sincronizar_fechamento_atendimento(
            db, tenant_id, item["atendimento_id"]
        )
        if resumo.get("sincronizado"):
            sincronizados += 1

    restantes = listar_pendencias_fechamento(db, tenant_id, limit, cursor)["total"]
    return {
        "total_processados": len(pendencias),
        "sincronizados": sincronizados,
        "sem_venda": sem_venda,
        "pendentes_restantes": restantes,
        "proximo_cursor": resultado["proximo_cursor"],
        "busca_incompleta": resultado["busca_incompleta"],
    }


def montar_resumo_fechamento(
    atendimento, venda=None, contas=None, sincronizado=False
) -> dict:
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
        "contas_receber_pendentes": len(
            [c for c in contas if c.status in {"pendente", "parcial", "vencido"}]
        ),
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
            or_(
                BanhoTosaAtendimento.venda_id.is_(None),
                BanhoTosaAtendimento.conta_receber_id.is_(None),
                Venda.status.in_(["aberta", "baixa_parcial", "cancelada"]),
            ),
        )
        .order_by(BanhoTosaAtendimento.id.desc())
    )


def _contas_por_venda(
    db: Session, tenant_id, venda_ids: list[int]
) -> dict[int, list[ContaReceber]]:
    if not venda_ids:
        return {}
    contas = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == tenant_id, ContaReceber.venda_id.in_(venda_ids)
        )
        .order_by(ContaReceber.data_vencimento.asc(), ContaReceber.id.asc())
        .all()
    )
    agrupadas = {}
    for conta in contas:
        agrupadas.setdefault(conta.venda_id, []).append(conta)
    return agrupadas


def _montar_pendencia(atendimento, contas: list[ContaReceber]) -> dict:
    resumo = montar_resumo_fechamento(
        atendimento, atendimento.venda, contas, sincronizado=False
    )
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
        "pdv_url": f"/pdv?venda_id={atendimento.venda_id}"
        if atendimento.venda_id
        else None,
    }


def _obter_atendimento(db: Session, tenant_id, atendimento_id: int):
    return (
        db.query(BanhoTosaAtendimento)
        .options(joinedload(BanhoTosaAtendimento.venda).joinedload(Venda.pagamentos))
        .filter(
            BanhoTosaAtendimento.id == atendimento_id,
            BanhoTosaAtendimento.tenant_id == tenant_id,
        )
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
    pendentes = [
        conta for conta in contas if conta.status in {"pendente", "parcial", "vencido"}
    ]
    return pendentes[0] if pendentes else contas[0]


def _status_pagamento(total: Decimal, total_pago: Decimal) -> str:
    if total <= 0:
        return "sem_valor"
    if total_pago >= total - Decimal("0.01"):
        return "pago"
    if total_pago > 0:
        return "parcial"
    return "pendente"


def _montar_alertas(
    atendimento, venda, status_pagamento: str, contas: list[ContaReceber]
) -> list[str]:
    alertas = []
    if venda.status == "cancelada":
        alertas.append("Venda vinculada foi cancelada.")
    if atendimento.status in {"pronto", "entregue"} and venda.status in {
        "aberta",
        "baixa_parcial",
    }:
        alertas.append(
            "Atendimento pronto/entregue com cobranca ainda nao finalizada no PDV."
        )
    if status_pagamento in {"pendente", "parcial"}:
        alertas.append("Pagamento ainda nao cobre o valor total do atendimento.")
    if venda.status == "finalizada" and not contas:
        alertas.append(
            "Venda finalizada sem conta a receber localizada; sincronize/valide o financeiro."
        )
    return alertas


def _resumo_sem_venda(atendimento) -> dict:
    if atendimento.pacote_credito_id or entrega_sem_cobranca_registrada(atendimento):
        return {
            "atendimento_id": atendimento.id,
            "venda_id": None,
            "conta_receber_id": atendimento.conta_receber_id,
            "venda_status": None,
            "status_pagamento": "coberto_pacote"
            if atendimento.pacote_credito_id
            else "sem_cobranca",
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
