"""Serializadores e hashes de contratos veterinarios."""

import hashlib

from .veterinario_core import _serializar_datetime_vet


def _consulta_to_dict(c) -> dict:
    return {
        "id": c.id,
        "pet_id": c.pet_id,
        "cliente_id": c.cliente_id,
        "veterinario_id": c.veterinario_id,
        "tipo": c.tipo,
        "status": c.status,
        "queixa_principal": c.queixa_principal,
        "historia_clinica": c.historia_clinica,
        "peso_consulta": c.peso_consulta,
        "temperatura": c.temperatura,
        "frequencia_cardiaca": c.frequencia_cardiaca,
        "frequencia_respiratoria": c.frequencia_respiratoria,
        "tpc": c.tpc,
        "mucosas": c.mucosas,
        "hidratacao": c.hidratacao,
        "nivel_dor": c.nivel_dor,
        "saturacao_o2": c.saturacao_o2,
        "pressao_sistolica": c.pressao_sistolica,
        "pressao_diastolica": c.pressao_diastolica,
        "glicemia": c.glicemia,
        "exame_fisico": c.exame_fisico,
        "hipotese_diagnostica": c.hipotese_diagnostica,
        "diagnostico": c.diagnostico,
        "diagnostico_simples": c.diagnostico_simples,
        "conduta": c.conduta,
        "retorno_em_dias": c.retorno_em_dias,
        "data_retorno": c.data_retorno,
        "asa_score": c.asa_score,
        "asa_justificativa": c.asa_justificativa,
        "observacoes_internas": c.observacoes_internas,
        "observacoes_tutor": c.observacoes_tutor,
        "hash_prontuario": c.hash_prontuario,
        "finalizado_em": _serializar_datetime_vet(c.finalizado_em),
        "inicio_atendimento": _serializar_datetime_vet(c.inicio_atendimento),
        "fim_atendimento": _serializar_datetime_vet(c.fim_atendimento),
        "pet_nome": c.pet.nome if c.pet else None,
        "cliente_nome": c.cliente.nome if c.cliente else None,
        "veterinario_nome": c.veterinario.nome if c.veterinario else None,
        "created_at": _serializar_datetime_vet(c.created_at),
    }


def _hash_prontuario_consulta(c) -> str:
    conteudo = f"{c.id}|{c.pet_id}|{c.diagnostico}|{c.conduta}|{c.finalizado_em}"
    return hashlib.sha256(conteudo.encode()).hexdigest()


def _prescricao_to_dict(p) -> dict:
    return {
        "id": p.id,
        "consulta_id": p.consulta_id,
        "pet_id": p.pet_id,
        "veterinario_id": p.veterinario_id,
        "numero": p.numero,
        "data_emissao": p.data_emissao,
        "tipo_receituario": p.tipo_receituario,
        "observacoes": p.observacoes,
        "hash_receita": p.hash_receita,
        "created_at": p.created_at,
        "itens": [
            {
                "id": it.id,
                "nome_medicamento": it.nome_medicamento,
                "concentracao": it.concentracao,
                "forma_farmaceutica": it.forma_farmaceutica,
                "quantidade": it.quantidade,
                "posologia": it.posologia,
                "via_administracao": it.via_administracao,
                "duracao_dias": it.duracao_dias,
                "medicamento_catalogo_id": it.medicamento_catalogo_id,
            }
            for it in p.itens
        ],
    }
