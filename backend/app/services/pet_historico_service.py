"""Historico de alteracoes dos dados diretos de um pet.

Decisao de negocio (10/2026): dados do animal compartilhados pelo grupo sao
so identidade/cadastro - nome, especie, raca, porte, microchip etc. Peso e
historico clinico (texto) sao por loja (cada marcacao com sua propria
data/loja) e vivem em `PetRegistroClinico`/`pet_registros_clinicos_service.py`,
nao aqui. Alergias/doencas cronicas/medicamentos continuos/restricoes
alimentares/tipo sanguineo tambem sao diretos no Pet (compartilhados), mas
ainda nao entram neste rastreamento por serem campos JSON de lista, nao
texto simples - ver `models_cadastros.py::Pet` se for estender.
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
