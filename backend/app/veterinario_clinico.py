"""Helpers clinicos compartilhados do modulo veterinario."""

import json
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from .models import AuditLog, Cliente, Pet, User
from .veterinario_core import _all_accessible_tenant_ids, _vet_now
from .veterinario_exames_ia import _meses_desde
from .veterinario_models import (
    AgendamentoVet,
    ConsultaVet,
    ExameVet,
    PrescricaoVet,
    ProtocoloVacina,
    VacinaRegistro,
)


def _aliases_especie_vet(especie: str) -> set[str]:
    especie_norm = (especie or "").strip().lower()
    aliases = {especie_norm} if especie_norm else set()
    if especie_norm in {"canino", "cao", "cão", "cachorro", "dog"}:
        aliases.update({"canino", "cao", "cão", "cachorro", "dog"})
    if especie_norm in {"felino", "gato", "cat"}:
        aliases.update({"felino", "gato", "cat"})
    return aliases


def _idade_inicio_meses_protocolo(dose_inicial_semanas: Optional[int]) -> Optional[float]:
    if not dose_inicial_semanas:
        return None
    return round(float(dose_inicial_semanas) / 4, 2)


def _status_vacinal_pet(db: Session, pet: Pet, tenant_id) -> dict:
    especies_pet = _aliases_especie_vet(pet.especie or "")
    protocolos = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,
    ).all()
    protocolos_ativos = [
        protocolo for protocolo in protocolos
        if (
            not protocolo.especie
            or protocolo.especie.strip().lower() in {"", "todos", "all"}
            or protocolo.especie.strip().lower() in especies_pet
        )
    ]

    registros = db.query(VacinaRegistro).filter(
        VacinaRegistro.pet_id == pet.id,
        VacinaRegistro.tenant_id == tenant_id,
    ).order_by(VacinaRegistro.data_aplicacao.desc()).all()

    pendentes = []
    vencidas = []
    carteira = []
    hoje = date.today()
    registros_por_nome = {}
    for registro in registros:
        chave = (registro.nome_vacina or "").strip().lower()
        registros_por_nome.setdefault(chave, []).append(registro)
        status = "em_dia"
        if registro.data_proxima_dose and registro.data_proxima_dose < hoje:
            status = "atrasada"
            vencidas.append({
                "nome": registro.nome_vacina,
                "data_proxima_dose": registro.data_proxima_dose.isoformat(),
                "dias_atraso": (hoje - registro.data_proxima_dose).days,
            })
        elif registro.data_proxima_dose and registro.data_proxima_dose <= hoje + timedelta(days=30):
            status = "vence_breve"
        carteira.append({
            "id": registro.id,
            "nome": registro.nome_vacina,
            "data_aplicacao": registro.data_aplicacao.isoformat(),
            "data_proxima_dose": registro.data_proxima_dose.isoformat() if registro.data_proxima_dose else None,
            "numero_dose": registro.numero_dose,
            "lote": registro.lote,
            "fabricante": registro.fabricante,
            "status": status,
        })

    idade_meses = _meses_desde(pet.data_nascimento)
    for protocolo in protocolos_ativos:
        chave = (protocolo.nome or "").strip().lower()
        registros_vacina = registros_por_nome.get(chave, [])
        if registros_vacina:
            continue
        idade_inicio = _idade_inicio_meses_protocolo(protocolo.dose_inicial_semanas)
        if idade_inicio is None or idade_meses is None or idade_meses >= idade_inicio:
            pendentes.append({
                "nome": protocolo.nome,
                "motivo": "Vacina prevista no protocolo sem registro aplicado.",
                "idade_inicio_meses": idade_inicio,
            })

    return {
        "carteira": carteira,
        "pendentes": pendentes,
        "vencidas": vencidas,
        "resumo": {
            "total_aplicadas": len(carteira),
            "total_pendentes": len(pendentes),
            "total_vencidas": len(vencidas),
        },
    }


def _montar_alertas_pet(db: Session, pet: Pet, tenant_id) -> list[dict]:
    alertas = []
    alergias = pet.alergias_lista if isinstance(getattr(pet, "alergias_lista", None), list) else None
    if not alergias and pet.alergias:
        alergias = [pet.alergias]
    for alergia in alergias or []:
        alertas.append({"tipo": "alergia", "nivel": "critico", "mensagem": f"Alergia registrada: {alergia}"})

    restricoes = getattr(pet, "restricoes_alimentares_lista", None) or []
    for restricao in restricoes:
        alertas.append({"tipo": "restricao", "nivel": "aviso", "mensagem": f"Restrição alimentar: {restricao}"})

    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    for vacina in status_vacinal["vencidas"]:
        alertas.append({
            "tipo": "vacina_atrasada",
            "nivel": "aviso",
            "mensagem": f"Vacina {vacina['nome']} atrasada há {vacina['dias_atraso']} dia(s).",
        })
    for pendente in status_vacinal["pendentes"][:3]:
        alertas.append({
            "tipo": "vacina_pendente",
            "nivel": "info",
            "mensagem": f"Protocolo sem registro: {pendente['nome']}.",
        })

    exames_pendentes = db.query(ExameVet).filter(
        ExameVet.pet_id == pet.id,
        ExameVet.tenant_id == tenant_id,
        ExameVet.status.in_(["solicitado", "aguardando", "disponivel"]),
    ).order_by(ExameVet.created_at.desc()).limit(3).all()
    for exame in exames_pendentes:
        alertas.append({
            "tipo": "exame_pendente",
            "nivel": "info",
            "mensagem": f"Exame {exame.nome} ainda está em {exame.status}.",
        })

    return alertas


def _pet_or_404(db: Session, pet_id: int, tenant_id) -> Pet:
    tenant_ids = _all_accessible_tenant_ids(db, tenant_id)
    pet = (
        db.query(Pet)
        .join(Cliente)
        .options(joinedload(Pet.cliente))
        .filter(Pet.id == pet_id, Cliente.tenant_id.in_(tenant_ids))
        .first()
    )
    if not pet:
        raise HTTPException(status_code=404, detail="Pet não encontrado")
    return pet


def _consulta_or_404(db: Session, consulta_id: int, tenant_id) -> ConsultaVet:
    c = db.query(ConsultaVet).filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return c


def _consulta_esta_finalizada(consulta: Optional[ConsultaVet]) -> bool:
    return (getattr(consulta, "status", None) or "").strip().lower() == "finalizada"


def _bloquear_lancamento_em_consulta_finalizada(consulta: Optional[ConsultaVet], acao: str) -> None:
    if not _consulta_esta_finalizada(consulta):
        return
    raise HTTPException(
        status_code=409,
        detail=(
            f"Consulta finalizada nao permite {acao}. "
            "Registre uma nova consulta/retorno ou reabra o fluxo com auditoria controlada."
        ),
    )


def _auditar_exame_pos_finalizacao(
    db: Session,
    *,
    tenant_id,
    user_id: Optional[int],
    exame: ExameVet,
    action: str,
    details: dict,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> None:
    if not exame.consulta_id:
        return

    consulta = db.query(ConsultaVet).filter(
        ConsultaVet.id == exame.consulta_id,
        ConsultaVet.tenant_id == tenant_id,
    ).first()
    if not _consulta_esta_finalizada(consulta):
        return

    db.add(AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity_type="vet_exame",
        entity_id=exame.id,
        old_value=json.dumps(old_value, ensure_ascii=True, default=str) if old_value else None,
        new_value=json.dumps(new_value, ensure_ascii=True, default=str) if new_value else None,
        details=json.dumps({
            "consulta_id": exame.consulta_id,
            "consulta_finalizada": True,
            **details,
        }, ensure_ascii=True, default=str),
        timestamp=_vet_now(),
    ))


def _prescricao_or_404(db: Session, prescricao_id: int, tenant_id) -> PrescricaoVet:
    p = (
        db.query(PrescricaoVet)
        .options(joinedload(PrescricaoVet.itens), joinedload(PrescricaoVet.pet), joinedload(PrescricaoVet.consulta))
        .filter(PrescricaoVet.id == prescricao_id, PrescricaoVet.tenant_id == tenant_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Prescrição não encontrada")
    return p


def _upsert_lembretes_push_agendamento(db: Session, ag: AgendamentoVet, tenant_id) -> None:
    """Cria/atualiza lembretes push de 24h e 1h para o tutor no app mobile."""
    if not ag.data_hora or not ag.cliente_id:
        return

    if ag.status in {"cancelado", "faltou"}:
        return

    from app.campaigns.models import NotificationChannelEnum, NotificationQueue, NotificationStatusEnum

    cliente = db.query(Cliente).filter(
        Cliente.id == ag.cliente_id,
        Cliente.tenant_id == str(tenant_id),
    ).first()
    if not cliente or not cliente.user_id:
        return

    user_tutor = db.query(User).filter(
        User.id == cliente.user_id,
        User.tenant_id == str(tenant_id),
    ).first()
    if not user_tutor or not getattr(user_tutor, "push_token", None):
        return

    prefixo = f"vet-agendamento:{ag.id}:"

    db.query(NotificationQueue).filter(
        NotificationQueue.idempotency_key.like(f"{prefixo}%"),
        NotificationQueue.status == NotificationStatusEnum.pending,
    ).delete(synchronize_session=False)

    agora = datetime.now(ag.data_hora.tzinfo) if getattr(ag.data_hora, "tzinfo", None) else datetime.now()
    lembretes = [
        (
            24,
            "Lembrete de consulta veterinária",
            f"Olá! A consulta do pet está marcada para amanhã às {ag.data_hora.strftime('%H:%M')}.",
        ),
        (
            1,
            "Lembrete de consulta veterinária",
            f"A consulta do pet começa em 1 hora ({ag.data_hora.strftime('%H:%M')}).",
        ),
    ]

    for horas, assunto, mensagem in lembretes:
        envio_em = ag.data_hora - timedelta(hours=horas)
        if envio_em <= agora:
            continue

        idempotencia = f"{prefixo}{horas}h:{ag.data_hora.isoformat()}"
        existe = db.query(NotificationQueue.id).filter(
            NotificationQueue.idempotency_key == idempotencia
        ).first()
        if existe:
            continue

        db.add(
            NotificationQueue(
                tenant_id=tenant_id,
                idempotency_key=idempotencia,
                customer_id=cliente.id,
                channel=NotificationChannelEnum.push,
                subject=assunto,
                body=mensagem,
                push_token=user_tutor.push_token,
                scheduled_at=envio_em,
            )
        )
