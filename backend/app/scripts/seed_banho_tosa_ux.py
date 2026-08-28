"""Cria cenarios locais de UX para agenda, fila e Taxi Dog do Banho & Tosa.

O modo padrao e dry-run. Use ``--apply`` apenas em DEV/demo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))


from app.scripts.seed_banho_tosa_ux_support import (  # noqa: E402
    MARKER,
    ensure_person as _ensure_person,
    ensure_pet as _ensure_pet,
    grant_profile as _grant_profile,
    one as _one,
)


DEFAULT_TARGET_EMAIL = "corepeterp@gmail.com"
PRODUCTION_ENVS = {"production", "prod", "producao"}

AGENDADOS = (
    ("Bento", "Golden Retriever", "grande", "Banho Completo", 8, "Primeira visita; confirmar sensibilidade nos ouvidos."),
    ("Luna", "Shih-tzu", "pequeno", "Banho + Tosa Higienica", 9, "Taxi Dog na ida; tutora pediu lacinho amarelo."),
    ("Thor", "Bulldog Frances", "medio", "Banho Higienico", 10, "Usar shampoo hipoalergenico."),
    ("Mel", "Yorkshire", "pequeno", "Hidratacao de Pelagem", 11, "Taxi Dog ida e volta; nao usar perfume forte."),
    ("Nina", "Border Collie", "grande", "Desembaraco", 12, "Pelagem longa com alguns nos."),
    ("Fred", "Pug", "pequeno", "Banho medio completo", 13, "Secar bem as dobrinhas."),
    ("Amora", "Lhasa Apso", "pequeno", "Tosa Completa", 14, "Tosa baixa, preservar topete."),
    ("Bob", "Vira-lata", "medio", "Banho + Tosa Higienica", 15, "Tutor busca no balcao apos as 17h."),
)

EM_PROCESSO = (
    ("Pipoca", "Spitz Alemao", "pequeno", "chegou", 0, "Aguardando avaliacao de entrada."),
    ("Zeus", "Rottweiler", "grande", "chegou", 0, "Pet docil, mas estranha secador muito perto."),
    ("Maia", "Beagle", "medio", "banho", 12, "Banho iniciado; conferir ouvido esquerdo."),
    ("Theo", "Maltês", "pequeno", "banho", 28, "Usar shampoo para pele sensivel."),
    ("Belinha", "Poodle", "pequeno", "secagem", 8, "Secagem em temperatura baixa."),
    ("Chico", "Schnauzer", "medio", "secagem", 24, "Tutor prefere barba bem seca e penteada."),
    ("Lola", "Cocker Spaniel", "medio", "tosa", 18, "Tosa tesoura; preservar franja das orelhas."),
    ("Max", "Labrador", "grande", "tosa", 38, "Acabamento de patas e retirada de subpelo."),
)

STATUS_POR_ETAPA = {
    "chegou": "chegou",
    "banho": "em_banho",
    "secagem": "em_secagem",
    "tosa": "em_tosa",
}

RECURSO_POR_ETAPA = {
    "banho": "banheira",
    "secagem": "secador",
    "tosa": "mesa_tosa",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-email", default=DEFAULT_TARGET_EMAIL)
    parser.add_argument("--base-date", default=date.today().isoformat())
    parser.add_argument("--apply", action="store_true")
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        if os.getenv(name):
            return str(os.getenv(name)).strip().lower()
    return ""


def _resolve_context(db, email: str) -> dict[str, Any]:
    row = _one(
        db,
        """
        SELECT id AS user_id, tenant_id::text AS tenant_id
        FROM users
        WHERE lower(email) = lower(:email)
        ORDER BY id
        LIMIT 1
        """,
        {"email": email.strip()},
    )
    if not row:
        raise ValueError(f"Usuario demo nao encontrado: {email}")
    db.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": row["tenant_id"]},
    )
    return row


def _service(db, tenant_id: str, preferred_name: str) -> dict[str, Any]:
    row = _one(
        db,
        """
        SELECT id, nome, duracao_padrao_minutos, preco_base
        FROM banho_tosa_servicos
        WHERE tenant_id = :tenant_id AND ativo IS TRUE
        ORDER BY CASE WHEN nome = :nome THEN 0 ELSE 1 END, id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "nome": preferred_name},
    )
    if not row:
        raise ValueError("Cadastre ao menos um servico ativo de Banho & Tosa.")
    return row


def _resource_id(db, tenant_id: str, resource_type: str) -> int | None:
    return db.execute(
        text(
            """
            SELECT id FROM banho_tosa_recursos
            WHERE tenant_id = :tenant_id AND tipo = :tipo AND ativo IS TRUE
            ORDER BY id LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "tipo": resource_type},
    ).scalar()


def _upsert_appointment(
    db,
    *,
    tenant_id: str,
    user_id: int,
    cliente_id: int,
    pet_id: int,
    profissional_id: int,
    recurso_id: int | None,
    service: dict[str, Any],
    inicio: datetime,
    status: str,
    note: str,
) -> int:
    fim = inicio + timedelta(minutes=int(service["duracao_padrao_minutos"] or 60))
    existing = _one(
        db,
        """
        SELECT id FROM banho_tosa_agendamentos
        WHERE tenant_id = :tenant_id AND pet_id = :pet_id AND origem = 'ux_banho_tosa'
        ORDER BY id LIMIT 1
        """,
        {"tenant_id": tenant_id, "pet_id": pet_id},
    )
    params = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "cliente_id": cliente_id,
        "pet_id": pet_id,
        "profissional_id": profissional_id,
        "recurso_id": recurso_id,
        "inicio": inicio,
        "fim": fim,
        "status": status,
        "observacoes": f"{MARKER} {note}",
        "valor": service["preco_base"],
    }
    if existing:
        appointment_id = int(existing["id"])
        db.execute(
            text(
                """
                UPDATE banho_tosa_agendamentos SET
                    cliente_id = :cliente_id, responsavel_agendamento_user_id = :user_id,
                    profissional_principal_id = :profissional_id,
                    banhista_id = :profissional_id, tosador_id = :profissional_id,
                    recurso_id = :recurso_id, data_hora_inicio = :inicio,
                    data_hora_fim_prevista = :fim, status = :status,
                    observacoes = :observacoes, valor_previsto = :valor,
                    restricoes_veterinarias_snapshot = :restricoes,
                    perfil_comportamental_snapshot = :perfil, updated_at = now()
                WHERE id = :id AND tenant_id = :tenant_id
                """
            ),
            {
                **params,
                "id": appointment_id,
                "restricoes": json.dumps({"alertas": ["Confirmar pele e ouvidos antes do banho"]}),
                "perfil": json.dumps({"temperamento": "docil", "observacao": "Apresentar o secador aos poucos"}),
            },
        )
    else:
        appointment_id = int(
            db.execute(
                text(
                    """
                    INSERT INTO banho_tosa_agendamentos (
                        tenant_id, cliente_id, pet_id, responsavel_agendamento_user_id,
                        profissional_principal_id, banhista_id, tosador_id, recurso_id,
                        data_hora_inicio, data_hora_fim_prevista, status, origem,
                        observacoes, restricoes_veterinarias_snapshot,
                        perfil_comportamental_snapshot, valor_previsto, sinal_pago
                    ) VALUES (
                        :tenant_id, :cliente_id, :pet_id, :user_id, :profissional_id,
                        :profissional_id, :profissional_id, :recurso_id, :inicio, :fim,
                        :status, 'ux_banho_tosa', :observacoes, :restricoes, :perfil,
                        :valor, 0
                    ) RETURNING id
                    """
                ),
                {
                    **params,
                    "restricoes": json.dumps({"alertas": ["Confirmar pele e ouvidos antes do banho"]}),
                    "perfil": json.dumps({"temperamento": "docil", "observacao": "Apresentar o secador aos poucos"}),
                },
            ).scalar_one()
        )

    db.execute(
        text("DELETE FROM banho_tosa_agendamento_servicos WHERE agendamento_id = :id"),
        {"id": appointment_id},
    )
    db.execute(
        text(
            """
            INSERT INTO banho_tosa_agendamento_servicos (
                tenant_id, agendamento_id, servico_id, nome_servico_snapshot,
                quantidade, valor_unitario, desconto, tempo_previsto_minutos
            ) VALUES (
                :tenant_id, :agendamento_id, :servico_id, :nome, 1, :valor, 0, :tempo
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "agendamento_id": appointment_id,
            "servico_id": service["id"],
            "nome": service["nome"],
            "valor": service["preco_base"],
            "tempo": service["duracao_padrao_minutos"],
        },
    )
    return appointment_id


def _set_process_stage(
    db,
    *,
    tenant_id: str,
    appointment_id: int,
    cliente_id: int,
    pet_id: int,
    profissional_id: int,
    stage: str,
    elapsed_minutes: int,
    note: str,
    base_time: datetime,
) -> int:
    status = STATUS_POR_ETAPA[stage]
    checkin = base_time - timedelta(minutes=max(elapsed_minutes + 35, 45))
    atendimento_id = db.execute(
        text(
            """
            SELECT id FROM banho_tosa_atendimentos
            WHERE tenant_id = :tenant_id AND agendamento_id = :agendamento_id
            ORDER BY id LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "agendamento_id": appointment_id},
    ).scalar()
    if atendimento_id is None:
        atendimento_id = db.execute(
            text(
                """
                INSERT INTO banho_tosa_atendimentos (
                    tenant_id, agendamento_id, cliente_id, pet_id, status,
                    checkin_em, inicio_em, porte_snapshot, pelagem_snapshot,
                    observacoes_entrada, ocorrencias
                ) VALUES (
                    :tenant_id, :agendamento_id, :cliente_id, :pet_id, :status,
                    :checkin, :inicio, NULL, NULL, :observacoes, :ocorrencias
                ) RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "agendamento_id": appointment_id,
                "cliente_id": cliente_id,
                "pet_id": pet_id,
                "status": status,
                "checkin": checkin,
                "inicio": checkin if stage != "chegou" else None,
                "observacoes": f"{MARKER} {note}",
                "ocorrencias": json.dumps([]),
            },
        ).scalar_one()
    else:
        db.execute(
            text(
                """
                UPDATE banho_tosa_atendimentos SET status = :status,
                    checkin_em = :checkin, inicio_em = :inicio, fim_em = NULL,
                    entregue_em = NULL, observacoes_entrada = :observacoes,
                    ocorrencias = :ocorrencias, updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": atendimento_id,
                "status": status,
                "checkin": checkin,
                "inicio": checkin if stage != "chegou" else None,
                "observacoes": f"{MARKER} {note}",
                "ocorrencias": json.dumps([]),
            },
        )
    atendimento_id = int(atendimento_id)
    db.execute(
        text("DELETE FROM banho_tosa_etapas WHERE atendimento_id = :id"),
        {"id": atendimento_id},
    )

    flow = ("banho", "secagem", "tosa")
    if stage in flow:
        current_index = flow.index(stage)
        cursor = checkin + timedelta(minutes=15)
        for index, etapa in enumerate(flow[: current_index + 1]):
            is_current = etapa == stage
            duration = elapsed_minutes if is_current else 20 + (index * 5)
            inicio = base_time - timedelta(minutes=elapsed_minutes) if is_current else cursor
            fim = None if is_current else inicio + timedelta(minutes=duration)
            resource_id = _resource_id(db, tenant_id, RECURSO_POR_ETAPA[etapa])
            db.execute(
                text(
                    """
                    INSERT INTO banho_tosa_etapas (
                        tenant_id, atendimento_id, tipo, responsavel_id, recurso_id,
                        inicio_em, fim_em, duracao_minutos, duracao_segundos,
                        observacoes, ordem_fluxo, tempo_previsto_minutos
                    ) VALUES (
                        :tenant_id, :atendimento_id, :tipo, :responsavel_id,
                        :recurso_id, :inicio, :fim, :duracao_minutos,
                        :duracao_segundos, :observacoes, :ordem, :previsto
                    )
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "atendimento_id": atendimento_id,
                    "tipo": etapa,
                    "responsavel_id": profissional_id,
                    "recurso_id": resource_id,
                    "inicio": inicio,
                    "fim": fim,
                    "duracao_minutos": None if is_current else duration,
                    "duracao_segundos": None if is_current else duration * 60,
                    "observacoes": f"{MARKER} etapa de teste",
                    "ordem": index + 1,
                    "previsto": {"banho": 25, "secagem": 20, "tosa": 35}[etapa],
                },
            )
            if fim:
                cursor = fim

    db.execute(
        text(
            """
            UPDATE banho_tosa_agendamentos
            SET status = 'em_atendimento', updated_at = now()
            WHERE id = :id AND tenant_id = :tenant_id
            """
        ),
        {"id": appointment_id, "tenant_id": tenant_id},
    )
    return atendimento_id


def _reset_scheduled_attendance(db, tenant_id: str, appointment_id: int) -> None:
    attendance_ids = [
        row[0]
        for row in db.execute(
            text(
                """
                SELECT id FROM banho_tosa_atendimentos
                WHERE tenant_id = :tenant_id AND agendamento_id = :agendamento_id
                """
            ),
            {"tenant_id": tenant_id, "agendamento_id": appointment_id},
        ).all()
    ]
    if attendance_ids:
        db.execute(
            text("DELETE FROM banho_tosa_etapas WHERE atendimento_id = ANY(:ids)"),
            {"ids": attendance_ids},
        )
        db.execute(
            text("DELETE FROM banho_tosa_atendimentos WHERE id = ANY(:ids)"),
            {"ids": attendance_ids},
        )


def _upsert_taxi(
    db,
    *,
    tenant_id: str,
    appointment_id: int,
    cliente_id: int,
    pet_id: int,
    motorista_id: int,
    status: str,
    janela: datetime,
) -> int:
    existing_id = db.execute(
        text(
            """
            SELECT id FROM banho_tosa_taxi_dog
            WHERE tenant_id = :tenant_id AND agendamento_id = :agendamento_id
            ORDER BY id LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "agendamento_id": appointment_id},
    ).scalar()
    params = {
        "tenant_id": tenant_id,
        "appointment_id": appointment_id,
        "cliente_id": cliente_id,
        "pet_id": pet_id,
        "motorista_id": motorista_id,
        "status": status,
        "janela": janela,
        "janela_fim": janela + timedelta(minutes=45),
    }
    if existing_id:
        taxi_id = int(existing_id)
        db.execute(
            text(
                """
                UPDATE banho_tosa_taxi_dog SET motorista_id = :motorista_id,
                    tipo = 'ida_volta', status = :status,
                    endereco_origem = 'Rua das Acacias, 120 - Centro, Sao Paulo - SP',
                    endereco_destino = 'Core Pet - Unidade Demo',
                    janela_inicio = :janela, janela_fim = :janela_fim,
                    km_estimado = 4.8, valor_cobrado = 24.90,
                    custo_estimado = 11.50, updated_at = now()
                WHERE id = :id AND tenant_id = :tenant_id
                """
            ),
            {**params, "id": taxi_id},
        )
    else:
        taxi_id = int(
            db.execute(
                text(
                    """
                    INSERT INTO banho_tosa_taxi_dog (
                        tenant_id, cliente_id, pet_id, agendamento_id, tipo, status,
                        motorista_id, endereco_origem, endereco_destino,
                        janela_inicio, janela_fim, km_estimado, km_real,
                        valor_cobrado, custo_estimado, custo_real
                    ) VALUES (
                        :tenant_id, :cliente_id, :pet_id, :appointment_id,
                        'ida_volta', :status, :motorista_id,
                        'Rua das Acacias, 120 - Centro, Sao Paulo - SP',
                        'Core Pet - Unidade Demo', :janela, :janela_fim,
                        4.8, 0, 24.90, 11.50, 0
                    ) RETURNING id
                    """
                ),
                params,
            ).scalar_one()
        )
    db.execute(
        text("UPDATE banho_tosa_agendamentos SET taxi_dog_id = :taxi_id WHERE id = :id"),
        {"taxi_id": taxi_id, "id": appointment_id},
    )
    return taxi_id


def seed(db, *, email: str, base_date: date, dry_run: bool) -> dict[str, Any]:
    context = _resolve_context(db, email)
    tenant_id = str(context["tenant_id"])
    user_id = int(context["user_id"])
    funcionario_id = _ensure_person(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        codigo="DEMO-FUNC-001",
        nome="Beatriz Vendedora Demo",
        tipo="funcionario",
    )
    motorista_id = _ensure_person(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        codigo="DEMO-ENT-001",
        nome="Carlos Entregador Demo",
        tipo="funcionario",
        is_entregador=True,
    )
    _grant_profile(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        cliente_id=funcionario_id,
        profile_type="funcionario",
    )
    _grant_profile(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        cliente_id=motorista_id,
        profile_type="entregador",
    )

    appointments: list[dict[str, int]] = []
    all_scenarios = list(AGENDADOS) + list(EM_PROCESSO)
    for index, (nome, raca, porte, service_or_stage, hour_or_elapsed, note) in enumerate(all_scenarios):
        codigo = f"UX-BT-CLI-{index + 1:02d}"
        cliente_id = _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            codigo=codigo,
            nome=f"Tutor(a) de {nome}",
            tipo="cliente",
        )
        pet_id = _ensure_pet(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            cliente_id=cliente_id,
            codigo=f"UX-BT-PET-{index + 1:02d}",
            nome=nome,
            raca=raca,
            porte=porte,
            index=index,
        )
        if index < len(AGENDADOS):
            service = _service(db, tenant_id, service_or_stage)
            inicio = datetime.combine(base_date, time(hour=hour_or_elapsed))
            appointment_id = _upsert_appointment(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                cliente_id=cliente_id,
                pet_id=pet_id,
                profissional_id=funcionario_id,
                recurso_id=_resource_id(db, tenant_id, "box"),
                service=service,
                inicio=inicio,
                status="agendado",
                note=note,
            )
            _reset_scheduled_attendance(db, tenant_id, appointment_id)
            appointments.append(
                {"id": appointment_id, "cliente_id": cliente_id, "pet_id": pet_id}
            )
        else:
            process_index = index - len(AGENDADOS)
            service = _service(db, tenant_id, "Banho + Tosa Higienica")
            inicio = datetime.combine(base_date, time(hour=7, minute=15)) + timedelta(
                minutes=process_index * 10
            )
            appointment_id = _upsert_appointment(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                cliente_id=cliente_id,
                pet_id=pet_id,
                profissional_id=funcionario_id,
                recurso_id=_resource_id(db, tenant_id, "box"),
                service=service,
                inicio=inicio,
                status="em_atendimento",
                note=note,
            )
            _set_process_stage(
                db,
                tenant_id=tenant_id,
                appointment_id=appointment_id,
                cliente_id=cliente_id,
                pet_id=pet_id,
                profissional_id=funcionario_id,
                stage=service_or_stage,
                elapsed_minutes=hour_or_elapsed,
                note=note,
                base_time=datetime.combine(base_date, datetime.now().time()),
            )
            appointments.append(
                {"id": appointment_id, "cliente_id": cliente_id, "pet_id": pet_id}
            )

    taxi_scenarios = (
        (1, "agendado"),
        (3, "motorista_a_caminho"),
        (4, "pet_coletado"),
        (8, "entregue_na_clinica"),
    )
    for appointment_index, taxi_status in taxi_scenarios:
        item = appointments[appointment_index]
        _upsert_taxi(
            db,
            tenant_id=tenant_id,
            appointment_id=item["id"],
            cliente_id=item["cliente_id"],
            pet_id=item["pet_id"],
            motorista_id=motorista_id,
            status=taxi_status,
            janela=datetime.combine(base_date, time(hour=7, minute=30))
            + timedelta(minutes=appointment_index * 35),
        )

    summary = {
        "ok": True,
        "dry_run": dry_run,
        "tenant_id": tenant_id,
        "base_date": base_date.isoformat(),
        "agendados": len(AGENDADOS),
        "em_processo": len(EM_PROCESSO),
        "taxi_dog": len(taxi_scenarios),
        "perfis_app": ["funcionario", "entregador"],
        "marker": MARKER,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    dry_run = not args.apply
    try:
        base_date = date.fromisoformat(args.base_date)
        environment = _environment_name()
        if args.apply and environment in PRODUCTION_ENVS:
            raise ValueError("Seed bloqueado em ambiente de producao.")

        import app.db.base  # noqa: F401
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            result = seed(
                db,
                email=args.target_email,
                base_date=base_date,
                dry_run=dry_run,
            )
            db.commit() if args.apply else db.rollback()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "dry_run": dry_run, "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
