from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAgendamentoServico,
    BanhoTosaAtendimento,
    BanhoTosaConfiguracao,
    BanhoTosaEtapa,
)
from app.banho_tosa_pacotes import calcular_saldo_creditos
from app.models import Cliente, Pet
from app.utils.serialization import safe_decimal_to_float


STATUS_AGENDAMENTO_FINAIS = {"entregue", "cancelado", "no_show"}
STATUS_ATENDIMENTO_FINAIS = {"entregue", "cancelado", "no_show"}


def obter_ou_criar_configuracao(db: Session, tenant_id) -> BanhoTosaConfiguracao:
    config = (
        db.query(BanhoTosaConfiguracao)
        .filter(BanhoTosaConfiguracao.tenant_id == tenant_id, BanhoTosaConfiguracao.ativo == True)
        .order_by(BanhoTosaConfiguracao.id.asc())
        .first()
    )
    if config:
        return config

    config = BanhoTosaConfiguracao(
        tenant_id=tenant_id,
        dias_funcionamento=["segunda", "terca", "quarta", "quinta", "sexta", "sabado"],
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def validar_cliente_pet(db: Session, tenant_id, cliente_id: int, pet_id: int) -> tuple[Cliente, Pet]:
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id,
        Cliente.ativo == True,
    ).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Tutor nao encontrado")

    pet = db.query(Pet).filter(
        Pet.id == pet_id,
        Pet.tenant_id == tenant_id,
        Pet.cliente_id == cliente_id,
        Pet.ativo == True,
    ).first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet nao encontrado para esse tutor")

    return cliente, pet


def serializar_etapa(etapa: BanhoTosaEtapa) -> dict:
    responsavel = etapa.responsavel
    recurso = etapa.recurso
    return {
        "id": etapa.id,
        "atendimento_id": etapa.atendimento_id,
        "tipo": etapa.tipo,
        "responsavel_id": etapa.responsavel_id,
        "responsavel_nome": responsavel.nome if responsavel else None,
        "recurso_id": etapa.recurso_id,
        "recurso_nome": recurso.nome if recurso else None,
        "inicio_em": etapa.inicio_em,
        "fim_em": etapa.fim_em,
        "duracao_minutos": etapa.duracao_minutos,
        "observacoes": etapa.observacoes,
    }


def serializar_agendamento(agendamento: BanhoTosaAgendamento) -> dict:
    pet = agendamento.pet
    cliente = agendamento.cliente
    recurso = getattr(agendamento, "recurso", None)
    return {
        "id": agendamento.id,
        "cliente_id": agendamento.cliente_id,
        "cliente_nome": cliente.nome if cliente else None,
        "pet_id": agendamento.pet_id,
        "pet_nome": pet.nome if pet else None,
        "pet_especie": pet.especie if pet else None,
        "pet_porte": pet.porte if pet else None,
        "profissional_principal_id": agendamento.profissional_principal_id,
        "banhista_id": agendamento.banhista_id,
        "tosador_id": agendamento.tosador_id,
        "recurso_id": agendamento.recurso_id,
        "recurso_nome": recurso.nome if recurso else None,
        "recurso_tipo": recurso.tipo if recurso else None,
        "data_hora_inicio": agendamento.data_hora_inicio,
        "data_hora_fim_prevista": agendamento.data_hora_fim_prevista,
        "status": agendamento.status,
        "origem": agendamento.origem,
        "observacoes": agendamento.observacoes,
        "valor_previsto": agendamento.valor_previsto,
        "taxi_dog_id": agendamento.taxi_dog_id,
        "restricoes_veterinarias_snapshot": agendamento.restricoes_veterinarias_snapshot or {},
        "perfil_comportamental_snapshot": agendamento.perfil_comportamental_snapshot or {},
        "servicos": agendamento.servicos,
    }


def serializar_atendimento(atendimento: BanhoTosaAtendimento) -> dict:
    pet = atendimento.pet
    cliente = atendimento.cliente
    agendamento = getattr(atendimento, "agendamento", None)
    etapas = getattr(atendimento, "etapas", []) or []
    venda = getattr(atendimento, "venda", None)
    pacote_credito = getattr(atendimento, "pacote_credito", None)
    valor_pago = sum(float(pag.valor or 0) for pag in venda.pagamentos) if venda else 0
    venda_total = safe_decimal_to_float(venda.total) if venda else None
    status_pagamento = None
    if venda:
        status_pagamento = "pago" if valor_pago >= (venda_total or 0) else "parcial" if valor_pago > 0 else "pendente"

    return {
        "id": atendimento.id,
        "agendamento_id": atendimento.agendamento_id,
        "cliente_id": atendimento.cliente_id,
        "cliente_nome": cliente.nome if cliente else None,
        "pet_id": atendimento.pet_id,
        "pet_nome": pet.nome if pet else None,
        "pet_especie": pet.especie if pet else None,
        "pet_porte": pet.porte if pet else None,
        "status": atendimento.status,
        "checkin_em": atendimento.checkin_em,
        "inicio_em": atendimento.inicio_em,
        "fim_em": atendimento.fim_em,
        "entregue_em": atendimento.entregue_em,
        "porte_snapshot": atendimento.porte_snapshot,
        "pelagem_snapshot": atendimento.pelagem_snapshot,
        "observacoes_entrada": atendimento.observacoes_entrada,
        "observacoes_saida": atendimento.observacoes_saida,
        "restricoes_veterinarias_snapshot": (
            agendamento.restricoes_veterinarias_snapshot if agendamento else {}
        ) or {},
        "perfil_comportamental_snapshot": (
            agendamento.perfil_comportamental_snapshot if agendamento else {}
        ) or {},
        "ocorrencias": atendimento.ocorrencias or [],
        "venda_id": atendimento.venda_id,
        "venda_numero": venda.numero_venda if venda else None,
        "venda_status": venda.status if venda else None,
        "venda_total": venda_total,
        "venda_total_pago": valor_pago,
        "venda_valor_restante": max((venda_total or 0) - valor_pago, 0),
        "venda_status_pagamento": status_pagamento,
        "conta_receber_id": atendimento.conta_receber_id,
        "pacote_credito_id": atendimento.pacote_credito_id,
        "pacote_movimento_id": atendimento.pacote_movimento_id,
        "pacote_nome": pacote_credito.pacote.nome if pacote_credito and pacote_credito.pacote else None,
        "pacote_saldo_creditos": (
            calcular_saldo_creditos(
                pacote_credito.creditos_total,
                pacote_credito.creditos_usados,
                pacote_credito.creditos_cancelados,
            )
            if pacote_credito
            else None
        ),
        "fechamento_alertas": _alertas_fechamento_atendimento(atendimento, venda, status_pagamento),
        "pdv_url": f"/pdv?venda_id={atendimento.venda_id}" if atendimento.venda_id else None,
        "etapas": [serializar_etapa(etapa) for etapa in etapas],
    }


def _alertas_fechamento_atendimento(atendimento, venda, status_pagamento: Optional[str]) -> list[str]:
    if atendimento.pacote_credito_id:
        return []
    if not venda:
        return ["Atendimento pronto/entregue sem venda vinculada."] if atendimento.status in {"pronto", "entregue"} else []
    alertas = []
    if venda.status == "cancelada":
        alertas.append("Venda vinculada foi cancelada.")
    if atendimento.status in {"pronto", "entregue"} and venda.status in {"aberta", "baixa_parcial"}:
        alertas.append("Cobranca ainda nao finalizada no PDV.")
    if status_pagamento in {"pendente", "parcial"}:
        alertas.append("Pagamento ainda nao cobre o valor total.")
    return alertas


def calcular_total_servicos(servicos: list[BanhoTosaAgendamentoServico]) -> Decimal:
    total = Decimal("0")
    for item in servicos:
        total += (item.quantidade * item.valor_unitario) - item.desconto
    return max(total, Decimal("0"))


def validar_conflito_agenda(
    db: Session,
    tenant_id,
    *,
    pet_id: int,
    inicio: datetime,
    fim: datetime,
    profissional_principal_id: Optional[int] = None,
    ignorar_agendamento_id: Optional[int] = None,
):
    query = db.query(BanhoTosaAgendamento).filter(
        BanhoTosaAgendamento.tenant_id == tenant_id,
        BanhoTosaAgendamento.status.notin_(list(STATUS_AGENDAMENTO_FINAIS)),
        BanhoTosaAgendamento.data_hora_inicio < fim,
        func.coalesce(BanhoTosaAgendamento.data_hora_fim_prevista, BanhoTosaAgendamento.data_hora_inicio) > inicio,
    )
    if ignorar_agendamento_id:
        query = query.filter(BanhoTosaAgendamento.id != ignorar_agendamento_id)

    conflitos = [BanhoTosaAgendamento.pet_id == pet_id]
    if profissional_principal_id:
        conflitos.append(BanhoTosaAgendamento.profissional_principal_id == profissional_principal_id)

    conflito = query.filter(or_(*conflitos)).first()
    if conflito:
        raise HTTPException(status_code=409, detail="Ja existe conflito de agenda para esse horario")
