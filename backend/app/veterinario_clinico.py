"""Helpers clinicos compartilhados do modulo veterinario."""

import json
import hashlib
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from .models import AuditLog, Cliente, Pet
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


def _idade_inicio_meses_protocolo(
    dose_inicial_semanas: Optional[int],
) -> Optional[float]:
    if not dose_inicial_semanas:
        return None
    return round(float(dose_inicial_semanas) / 4, 2)


def _idade_meses_pet(pet: Pet) -> Optional[int]:
    idade_meses = _meses_desde(pet.data_nascimento)
    if idade_meses is not None:
        return idade_meses
    idade_aproximada = getattr(pet, "idade_aproximada", None)
    if idade_aproximada is None:
        return None
    try:
        return int(idade_aproximada)
    except (TypeError, ValueError):
        return None


def _assinatura_publica_vacina(registro: VacinaRegistro, pet: Pet, tenant_id) -> str:
    payload = "|".join(
        [
            str(tenant_id or ""),
            str(registro.id or ""),
            str(pet.id or ""),
            str(registro.nome_vacina or ""),
            str(registro.data_aplicacao or ""),
            str(registro.lote or ""),
            str(registro.fabricante or ""),
            str(getattr(registro, "veterinario_id", None) or ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _status_vacinal_pet(db: Session, pet: Pet, tenant_id) -> dict:
    especies_pet = _aliases_especie_vet(pet.especie or "")
    protocolos = (
        db.query(ProtocoloVacina)
        .filter(
            ProtocoloVacina.tenant_id == tenant_id,
            ProtocoloVacina.ativo.is_(True),
        )
        .all()
    )
    protocolos_ativos = [
        protocolo
        for protocolo in protocolos
        if (
            not protocolo.especie
            or protocolo.especie.strip().lower() in {"", "todos", "all"}
            or protocolo.especie.strip().lower() in especies_pet
        )
    ]

    registros = (
        db.query(VacinaRegistro)
        .filter(
            VacinaRegistro.pet_id == pet.id,
            VacinaRegistro.tenant_id == tenant_id,
        )
        .order_by(VacinaRegistro.data_aplicacao.desc())
        .all()
    )

    veterinarios_por_id = {}
    veterinario_ids = {
        getattr(registro, "veterinario_id", None)
        for registro in registros
        if getattr(registro, "veterinario_id", None)
    }
    if veterinario_ids:
        veterinarios = (
            db.query(Cliente)
            .filter(
                Cliente.id.in_(veterinario_ids),
                Cliente.tenant_id == str(tenant_id),
            )
            .all()
        )
        veterinarios_por_id = {
            veterinario.id: veterinario for veterinario in veterinarios
        }

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
            vencidas.append(
                {
                    "nome": registro.nome_vacina,
                    "data_proxima_dose": registro.data_proxima_dose.isoformat(),
                    "dias_atraso": (hoje - registro.data_proxima_dose).days,
                }
            )
        elif (
            registro.data_proxima_dose
            and registro.data_proxima_dose <= hoje + timedelta(days=30)
        ):
            status = "vence_breve"
        assinatura_hash = _assinatura_publica_vacina(registro, pet, tenant_id)
        veterinario_id = getattr(registro, "veterinario_id", None)
        veterinario = veterinarios_por_id.get(veterinario_id)
        carteira.append(
            {
                "id": registro.id,
                "nome": registro.nome_vacina,
                "data_aplicacao": registro.data_aplicacao.isoformat(),
                "data_proxima_dose": registro.data_proxima_dose.isoformat()
                if registro.data_proxima_dose
                else None,
                "numero_dose": registro.numero_dose,
                "lote": registro.lote,
                "fabricante": registro.fabricante,
                "veterinario_id": veterinario_id,
                "veterinario_nome": getattr(veterinario, "nome", None)
                if veterinario
                else None,
                "assinatura_digital": f"VAC-{assinatura_hash[:12].upper()}"
                if veterinario_id
                else None,
                "assinatura_valida": bool(veterinario_id),
                "hash_validacao": assinatura_hash,
                "status": status,
            }
        )

    idade_meses = _idade_meses_pet(pet)
    for protocolo in protocolos_ativos:
        chave = (protocolo.nome or "").strip().lower()
        registros_vacina = registros_por_nome.get(chave, [])
        if registros_vacina:
            continue
        idade_inicio = _idade_inicio_meses_protocolo(protocolo.dose_inicial_semanas)
        if idade_inicio is None or idade_meses is None or idade_meses >= idade_inicio:
            pendentes.append(
                {
                    "nome": protocolo.nome,
                    "motivo": "Vacina prevista no protocolo sem registro aplicado.",
                    "idade_inicio_meses": idade_inicio,
                }
            )

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
    alergias = (
        pet.alergias_lista
        if isinstance(getattr(pet, "alergias_lista", None), list)
        else None
    )
    if not alergias and pet.alergias:
        alergias = [pet.alergias]
    for alergia in alergias or []:
        alertas.append(
            {
                "tipo": "alergia",
                "nivel": "critico",
                "mensagem": f"Alergia registrada: {alergia}",
            }
        )

    restricoes = getattr(pet, "restricoes_alimentares_lista", None) or []
    for restricao in restricoes:
        alertas.append(
            {
                "tipo": "restricao",
                "nivel": "aviso",
                "mensagem": f"Restrição alimentar: {restricao}",
            }
        )

    status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
    for vacina in status_vacinal["vencidas"]:
        alertas.append(
            {
                "tipo": "vacina_atrasada",
                "nivel": "aviso",
                "mensagem": f"Vacina {vacina['nome']} atrasada há {vacina['dias_atraso']} dia(s).",
            }
        )
    for pendente in status_vacinal["pendentes"][:3]:
        alertas.append(
            {
                "tipo": "vacina_pendente",
                "nivel": "info",
                "mensagem": f"Protocolo sem registro: {pendente['nome']}.",
            }
        )

    exames_pendentes = (
        db.query(ExameVet)
        .filter(
            ExameVet.pet_id == pet.id,
            ExameVet.tenant_id == tenant_id,
            ExameVet.status.in_(["solicitado", "aguardando", "disponivel"]),
        )
        .order_by(ExameVet.created_at.desc())
        .limit(3)
        .all()
    )
    for exame in exames_pendentes:
        alertas.append(
            {
                "tipo": "exame_pendente",
                "nivel": "info",
                "mensagem": f"Exame {exame.nome} ainda está em {exame.status}.",
            }
        )

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
    c = (
        db.query(ConsultaVet)
        .filter(ConsultaVet.id == consulta_id, ConsultaVet.tenant_id == tenant_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return c


def _consulta_esta_finalizada(consulta: Optional[ConsultaVet]) -> bool:
    return (getattr(consulta, "status", None) or "").strip().lower() == "finalizada"


def _bloquear_lancamento_em_consulta_finalizada(
    consulta: Optional[ConsultaVet], acao: str
) -> None:
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

    consulta = (
        db.query(ConsultaVet)
        .filter(
            ConsultaVet.id == exame.consulta_id,
            ConsultaVet.tenant_id == tenant_id,
        )
        .first()
    )
    if not _consulta_esta_finalizada(consulta):
        return

    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type="vet_exame",
            entity_id=exame.id,
            old_value=json.dumps(old_value, ensure_ascii=True, default=str)
            if old_value
            else None,
            new_value=json.dumps(new_value, ensure_ascii=True, default=str)
            if new_value
            else None,
            details=json.dumps(
                {
                    "consulta_id": exame.consulta_id,
                    "consulta_finalizada": True,
                    **details,
                },
                ensure_ascii=True,
                default=str,
            ),
            timestamp=_vet_now(),
        )
    )


def _prescricao_or_404(db: Session, prescricao_id: int, tenant_id) -> PrescricaoVet:
    p = (
        db.query(PrescricaoVet)
        .options(
            joinedload(PrescricaoVet.itens),
            joinedload(PrescricaoVet.pet),
            joinedload(PrescricaoVet.consulta),
        )
        .filter(PrescricaoVet.id == prescricao_id, PrescricaoVet.tenant_id == tenant_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Prescrição não encontrada")
    return p


def _upsert_lembretes_push_agendamento(
    db: Session, ag: AgendamentoVet, tenant_id
) -> None:
    """Cria/atualiza lembretes push de 24h e 1h para o tutor no app mobile."""
    if not ag.data_hora or not ag.cliente_id:
        return

    from app.services.appointment_reminders import (
        build_reminder_jobs,
        config_from_model,
        enqueue_reminder_jobs,
        replace_pending_reminder_jobs,
    )
    from app.veterinario_lembrete_configuracoes import (
        obter_ou_criar_configuracao_lembretes_vet,
    )

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == ag.cliente_id,
            Cliente.tenant_id == tenant_id,
        )
        .first()
    )
    if not cliente:
        return

    prefixo = f"vet-agendamento:{ag.id}:"
    replace_pending_reminder_jobs(db, tenant_id=tenant_id, idempotency_prefix=prefixo)

    if ag.status in {"cancelado", "faltou", "finalizado"}:
        return

    pet_nome = getattr(getattr(ag, "pet", None), "nome", None)
    config = obter_ou_criar_configuracao_lembretes_vet(db, tenant_id)
    jobs = build_reminder_jobs(
        config=config_from_model(config),
        tenant_id=tenant_id,
        customer_id=cliente.id,
        appointment_id=ag.id,
        starts_at=ag.data_hora,
        module="veterinario",
        kind="veterinario_agendamento",
        pet_id=ag.pet_id,
        pet_name=pet_nome,
        title="Lembrete de consulta veterinaria",
        body_for_hours=lambda horas: _mensagem_lembrete_vet(ag, pet_nome, horas),
        idempotency_prefix=prefixo,
    )
    enqueue_reminder_jobs(db, jobs)
    return


def _mensagem_lembrete_vet(ag: AgendamentoVet, pet_nome: str | None, horas: int) -> str:
    pet_label = pet_nome or "Seu pet"
    horario = ag.data_hora.strftime("%H:%M")
    if horas >= 24:
        return f"{pet_label} tem consulta veterinaria amanha as {horario}."
    if horas == 1:
        return f"{pet_label} tem consulta veterinaria em 1 hora ({horario})."
    return f"{pet_label} tem consulta veterinaria em {horas} horas ({horario})."
