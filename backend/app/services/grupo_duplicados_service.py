"""Deteccao (somente leitura) de cadastros duplicados entre lojas de um grupo.

Pessoas: mesmo CPF/CNPJ. Produtos: mesmo codigo de barras ou GTIN.
A fusao nao acontece aqui: a operacao confirma cada par.
"""

from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.grupo_comercial_models import GrupoComercialMembro


def _tenants_do_grupo(db: Session, grupo_id: int) -> list[str]:
    return [
        str(empresa_id)
        for (empresa_id,) in db.query(GrupoComercialMembro.empresa_id).filter(
            GrupoComercialMembro.grupo_id == grupo_id,
            GrupoComercialMembro.status == "ativo",
        )
    ]


def pessoas_duplicadas(db: Session, grupo_id: int) -> list[dict]:
    ids = _tenants_do_grupo(db, grupo_id)
    if len(ids) < 2:
        return []
    linhas = db.execute(
        text(
            """
            SELECT regexp_replace(COALESCE(cnpj, cpf), '\D', '', 'g') AS documento,
                   id, nome, codigo, tenant_id::text AS loja_id, ativo
            FROM clientes
            WHERE tenant_id::text = ANY(:ids)
              AND regexp_replace(COALESCE(cnpj, cpf, ''), '\D', '', 'g') <> ''
            """
        ),
        {"ids": ids},
    ).mappings().all()
    grupos = defaultdict(list)
    for linha in linhas:
        grupos[linha["documento"]].append(dict(linha))
    return [
        {"chave": documento, "registros": registros}
        for documento, registros in grupos.items()
        if len({r["loja_id"] for r in registros}) > 1
    ]


def produtos_duplicados(db: Session, grupo_id: int) -> list[dict]:
    ids = _tenants_do_grupo(db, grupo_id)
    if len(ids) < 2:
        return []
    linhas = db.execute(
        text(
            """
            SELECT COALESCE(NULLIF(trim(codigo_barras), ''), NULLIF(trim(gtin_ean), '')) AS codigo,
                   id, nome, codigo AS sku, tenant_id::text AS loja_id
            FROM produtos
            WHERE tenant_id::text = ANY(:ids)
              AND COALESCE(NULLIF(trim(codigo_barras), ''), NULLIF(trim(gtin_ean), '')) IS NOT NULL
            """
        ),
        {"ids": ids},
    ).mappings().all()
    grupos = defaultdict(list)
    for linha in linhas:
        grupos[linha["codigo"]].append(dict(linha))
    return [
        {"chave": codigo, "registros": registros}
        for codigo, registros in grupos.items()
        if len({r["loja_id"] for r in registros}) > 1
    ]
