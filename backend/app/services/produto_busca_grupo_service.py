# -*- coding: utf-8 -*-
"""Busca (somente leitura) de produtos em outras lojas do mesmo grupo comercial.

Resolve o caso relatado: a loja A nunca cadastrou um item que a loja B (mesmo
grupo) ja vende — ate aqui, a listagem de produtos de A nunca vai achar esse
item, porque ela sempre buscou so dentro do proprio tenant. Esta busca e
deliberadamente **separada** da query principal de listagem
(`app/produtos/listagem.py::_montar_query_listagem_produtos`): roda so quando
ha termo de busca, nao entra na paginacao/contagem principal, e ignora filtros
que so fazem sentido dentro de uma loja (categoria_id/marca_id/departamento_id
sao IDs locais — aplicar o filtro de uma loja na outra daria resultado errado).

Preco/estoque retornados aqui sao os da loja de origem, so pra referencia —
esta busca nunca autoriza compra/venda. Quem quiser vender precisa do
compartilhamento de estoque (GrupoComercialEstoqueCompartilhado, continua
igual) ou cadastrar o produto na propria loja (endpoint de pre-cadastro,
produtos/cadastro_routes.py::pre_cadastro_produto_grupo).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..grupo_comercial_contexto import listar_empresas_do_grupo

LIMITE_PADRAO = 20


def buscar_produtos_outras_lojas_grupo(
    db: Session,
    tenant_id,
    termo_busca: str,
    *,
    limite: int = LIMITE_PADRAO,
) -> list[dict]:
    termo_busca = (termo_busca or "").strip()
    if not termo_busca:
        return []

    tenants_do_grupo = listar_empresas_do_grupo(db, tenant_id)
    outros_tenants = [t for t in tenants_do_grupo if str(t) != str(tenant_id)]
    if not outros_tenants:
        return []

    termo_like = f"%{termo_busca}%"
    linhas = db.execute(
        text(
            """
            SELECT p.id, p.tenant_id::text AS tenant_id, t.name AS loja_nome,
                   p.nome, p.codigo, p.codigo_barras, p.imagem_principal,
                   p.preco_venda, p.estoque_atual, p.produto_identidade_id
            FROM produtos p
            JOIN tenants t ON t.id = p.tenant_id
            WHERE p.tenant_id::text = ANY(:tenants)
              AND p.ativo IS TRUE
              AND p.deleted_at IS NULL
              AND p.tipo <> 'servico'
              AND (
                p.nome ILIKE :termo
                OR p.codigo ILIKE :termo
                OR p.codigo_barras ILIKE :termo
                OR p.gtin_ean ILIKE :termo
              )
            ORDER BY p.nome
            LIMIT :limite
            """
        ),
        {"tenants": outros_tenants, "termo": termo_like, "limite": limite},
    ).mappings().all()
    return [dict(linha) for linha in linhas]
