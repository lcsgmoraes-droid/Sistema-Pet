"""Contexto clinico rastreavel para o assistente veterinario."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from .models import Pet
from .veterinario_models import (
    ConsultaVet,
    ExameVet,
    PrescricaoVet,
    VacinaRegistro,
)


def _valor_data(value: Any) -> Optional[str]:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value) if value not in (None, "") else None


def _lista_clinica(valor_lista: Any, valor_texto: Any = None) -> list[str]:
    valores: list[str] = []
    origem = valor_lista if isinstance(valor_lista, list) else []
    for item in origem:
        texto = str(item or "").strip()
        if texto and texto not in valores:
            valores.append(texto)
    texto_livre = str(valor_texto or "").strip()
    if texto_livre and texto_livre not in valores:
        valores.append(texto_livre)
    return valores


def _resumir_consulta(consulta: ConsultaVet) -> dict[str, Any]:
    return {
        "id": consulta.id,
        "data": _valor_data(consulta.created_at),
        "status": consulta.status,
        "tipo": consulta.tipo,
        "queixa_principal": consulta.queixa_principal,
        "historia_clinica": consulta.historia_clinica,
        "exame_fisico": consulta.exame_fisico,
        "hipotese_diagnostica": consulta.hipotese_diagnostica,
        "diagnostico": consulta.diagnostico,
        "conduta": consulta.conduta,
        "sinais_vitais": {
            "peso_kg": consulta.peso_consulta,
            "temperatura_c": consulta.temperatura,
            "frequencia_cardiaca_bpm": consulta.frequencia_cardiaca,
            "frequencia_respiratoria_mpm": consulta.frequencia_respiratoria,
            "tpc": consulta.tpc,
            "mucosas": consulta.mucosas,
            "hidratacao": consulta.hidratacao,
            "nivel_dor_0_10": consulta.nivel_dor,
            "saturacao_o2_pct": consulta.saturacao_o2,
            "pressao_sistolica_mmhg": consulta.pressao_sistolica,
            "pressao_diastolica_mmhg": consulta.pressao_diastolica,
            "glicemia_mg_dl": consulta.glicemia,
        },
    }


def _resumir_exame(exame: ExameVet) -> dict[str, Any]:
    return {
        "id": exame.id,
        "nome": exame.nome,
        "tipo": exame.tipo,
        "data_resultado": _valor_data(exame.data_resultado),
        "status": exame.status,
        "resultado_texto": exame.resultado_texto,
        "resultado_estruturado": exame.resultado_json or {},
        "interpretacao_veterinario": exame.interpretacao,
        "triagem_ia": exame.interpretacao_ia_resumo or exame.interpretacao_ia,
        "alertas_ia": exame.interpretacao_ia_alertas or [],
    }


def _resumir_prescricao(prescricao: PrescricaoVet) -> dict[str, Any]:
    return {
        "id": prescricao.id,
        "data_emissao": _valor_data(prescricao.data_emissao),
        "tipo_receituario": prescricao.tipo_receituario,
        "itens": [
            {
                "medicamento": item.nome_medicamento,
                "concentracao": item.concentracao,
                "quantidade": item.quantidade,
                "posologia": item.posologia,
                "via": item.via_administracao,
                "duracao_dias": item.duracao_dias,
            }
            for item in (prescricao.itens or [])
        ],
    }


def montar_contexto_clinico_vet(
    db: Session,
    *,
    tenant_id,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> tuple[dict[str, Any], list[str]]:
    """Monta apenas dados do tenant e informa quais blocos foram consultados."""

    contexto: dict[str, Any] = {}
    fontes: list[str] = []

    if pet:
        contexto["paciente"] = {
            "id": pet.id,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "sexo": pet.sexo,
            "castrado": pet.castrado,
            "data_nascimento": _valor_data(pet.data_nascimento),
            "idade_aproximada_meses": pet.idade_aproximada,
            "peso_cadastrado_kg": pet.peso,
            "alergias": _lista_clinica(pet.alergias_lista, pet.alergias),
            "condicoes_cronicas": _lista_clinica(
                pet.condicoes_cronicas_lista, pet.doencas_cronicas
            ),
            "medicamentos_continuos": _lista_clinica(
                pet.medicamentos_continuos_lista, pet.medicamentos_continuos
            ),
            "restricoes_alimentares": _lista_clinica(pet.restricoes_alimentares_lista),
            "historico_clinico": pet.historico_clinico,
        }
        fontes.append("ficha_do_paciente")

    if consulta:
        contexto["consulta_selecionada"] = _resumir_consulta(consulta)
        fontes.append("consulta_selecionada")

        prescricoes = (
            db.query(PrescricaoVet)
            .options(joinedload(PrescricaoVet.itens))
            .filter(
                PrescricaoVet.tenant_id == tenant_id,
                PrescricaoVet.consulta_id == consulta.id,
            )
            .order_by(PrescricaoVet.data_emissao.desc(), PrescricaoVet.id.desc())
            .all()
        )
        if prescricoes:
            contexto["prescricoes_da_consulta"] = [
                _resumir_prescricao(item) for item in prescricoes
            ]
            fontes.append("prescricoes_da_consulta")

    if exame:
        contexto["exame_selecionado"] = _resumir_exame(exame)
        fontes.append("exame_selecionado")

    if pet:
        consultas_query = db.query(ConsultaVet).filter(
            ConsultaVet.tenant_id == tenant_id,
            ConsultaVet.pet_id == pet.id,
        )
        if consulta:
            consultas_query = consultas_query.filter(ConsultaVet.id != consulta.id)
        consultas_recentes = (
            consultas_query.order_by(ConsultaVet.created_at.desc()).limit(5).all()
        )
        if consultas_recentes:
            contexto["consultas_recentes"] = [
                _resumir_consulta(item) for item in consultas_recentes
            ]
            fontes.append("ultimas_5_consultas")

        exames_query = db.query(ExameVet).filter(
            ExameVet.tenant_id == tenant_id,
            ExameVet.pet_id == pet.id,
        )
        if exame:
            exames_query = exames_query.filter(ExameVet.id != exame.id)
        exames_recentes = (
            exames_query.order_by(
                ExameVet.data_resultado.desc().nullslast(),
                ExameVet.created_at.desc(),
            )
            .limit(5)
            .all()
        )
        if exames_recentes:
            contexto["exames_recentes"] = [
                _resumir_exame(item) for item in exames_recentes
            ]
            fontes.append("ultimos_5_exames")

        vacinas = (
            db.query(VacinaRegistro)
            .filter(
                VacinaRegistro.tenant_id == tenant_id,
                VacinaRegistro.pet_id == pet.id,
            )
            .order_by(VacinaRegistro.data_aplicacao.desc())
            .limit(5)
            .all()
        )
        if vacinas:
            contexto["vacinas_recentes"] = [
                {
                    "nome": item.nome_vacina,
                    "data_aplicacao": _valor_data(item.data_aplicacao),
                    "proxima_dose": _valor_data(item.data_proxima_dose),
                    "numero_dose": item.numero_dose,
                }
                for item in vacinas
            ]
            fontes.append("ultimas_5_vacinas")

    contexto["campos_ausentes_importantes"] = [
        nome
        for nome, ausente in (
            ("paciente", not pet),
            ("especie", not pet or not pet.especie),
            (
                "peso_atual",
                not consulta
                or not consulta.peso_consulta
                and (not pet or not pet.peso),
            ),
            (
                "alergias_revisadas",
                not pet or not _lista_clinica(pet.alergias_lista, pet.alergias),
            ),
        )
        if ausente
    ]
    return contexto, fontes
