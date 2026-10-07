"""Historico de alteracoes do cadastro base de um produto.

Campos de preco e fiscal nao entram aqui: esses dados continuam por loja.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.produtos_catalogo_models import ProdutoHistoricoAlteracao

CAMPOS_RASTREADOS_PRODUTO = (
    "nome",
    "codigo",
    "codigo_barras",
    "gtin_ean",
    "descricao_curta",
    "descricao_completa",
    "marca_id",
    "unidade",
    "peso_liquido",
    "peso_bruto",
    "largura",
    "altura",
    "ativo",
)


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    return str(valor)


def registrar_alteracoes_produto(
    db: Session,
    *,
    produto_id: int,
    tenant_id: str,
    user_id: int | None,
    antes: dict[str, Any],
    depois: dict[str, Any],
) -> int:
    registros = 0
    for campo in CAMPOS_RASTREADOS_PRODUTO:
        if campo not in depois:
            continue
        valor_anterior = _texto(antes.get(campo))
        valor_novo = _texto(depois.get(campo))
        if valor_anterior == valor_novo:
            continue
        db.add(
            ProdutoHistoricoAlteracao(
                tenant_id=tenant_id,
                produto_id=produto_id,
                user_id=user_id,
                campo=campo,
                valor_anterior=valor_anterior,
                valor_novo=valor_novo,
            )
        )
        registros += 1
    return registros
