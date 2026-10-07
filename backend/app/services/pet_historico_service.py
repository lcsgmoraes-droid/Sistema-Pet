"""Historico de alteracoes dos dados diretos de um pet.

Campos de saude (alergias, doencas, medicamentos, historico clinico) nao entram
aqui: pendencia de decisao, pois saude e por loja.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models_cadastros import PetHistoricoAlteracao

CAMPOS_RASTREADOS_PET = (
    "nome",
    "especie",
    "raca",
    "sexo",
    "castrado",
    "data_nascimento",
    "porte",
    "cor",
    "microchip",
    "peso",
    "pedigree_registro",
    "ativo",
)


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    return str(valor)


def registrar_alteracoes_pet(
    db: Session,
    *,
    pet_id: int,
    tenant_id: str,
    user_id: int | None,
    antes: dict[str, Any],
    depois: dict[str, Any],
) -> int:
    registros = 0
    for campo in CAMPOS_RASTREADOS_PET:
        if campo not in depois:
            continue
        valor_anterior = _texto(antes.get(campo))
        valor_novo = _texto(depois.get(campo))
        if valor_anterior == valor_novo:
            continue
        db.add(
            PetHistoricoAlteracao(
                tenant_id=tenant_id,
                pet_id=pet_id,
                user_id=user_id,
                campo=campo,
                valor_anterior=valor_anterior,
                valor_novo=valor_novo,
            )
        )
        registros += 1
    return registros
