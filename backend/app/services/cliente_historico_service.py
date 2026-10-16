"""Historico de alteracoes de um cadastro de pessoa.

Cada campo alterado gera uma linha com data, usuario, loja de quem alterou,
valor anterior e valor novo. Campos fora da lista CAMPOS_RASTREADOS nao entram.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models_cadastros import ClienteHistoricoAlteracao

CAMPOS_RASTREADOS = (
    "nome",
    "nome_fantasia",
    "razao_social",
    "cpf",
    "cnpj",
    "email",
    "telefone",
    "celular",
    "data_nascimento",
    "cep",
    "endereco",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "estado",
    "is_cliente",
    "is_fornecedor",
    "is_veterinario",
    "is_funcionario",
    "ativo",
)


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    return str(valor)


def registrar_alteracoes_cliente(
    db: Session,
    *,
    cliente_id: int,
    tenant_id: str,
    user_id: int | None,
    antes: dict[str, Any],
    depois: dict[str, Any],
) -> int:
    registros = 0
    for campo in CAMPOS_RASTREADOS:
        if campo not in depois:
            continue
        valor_anterior = _texto(antes.get(campo))
        valor_novo = _texto(depois.get(campo))
        if valor_anterior == valor_novo:
            continue
        db.add(
            ClienteHistoricoAlteracao(
                tenant_id=tenant_id,
                cliente_id=cliente_id,
                user_id=user_id,
                campo=campo,
                valor_anterior=valor_anterior,
                valor_novo=valor_novo,
            )
        )
        registros += 1
    return registros
