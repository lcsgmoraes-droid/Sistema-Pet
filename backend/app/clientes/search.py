"""Busca e relevancia compartilhadas de pessoas (PDV, campanhas e listagens)."""

from sqlalchemy import case, func, or_
from app.models import Cliente, ClienteContato
from app.clientes.common import _somente_digitos_coluna


def _texto_normalizado(coluna, query):
    texto = func.coalesce(coluna, "")
    if query.session.get_bind().dialect.name == "postgresql":
        texto = func.unaccent(texto)
    return func.lower(texto)


def _aplicar_filtro_busca(query, search):
    termo_busca = (search or "").strip()
    if not termo_busca:
        return query

    telefone_digitos = _somente_digitos_coluna(Cliente.telefone)
    celular_digitos = _somente_digitos_coluna(Cliente.celular)
    for palavra in [p.strip() for p in termo_busca.split() if p.strip()]:
        like = f"%{palavra}%"
        filtros = [
            Cliente.codigo.ilike(like),
            _texto_normalizado(Cliente.nome, query).ilike(
                _texto_normalizado(like, query)
            ),
            _texto_normalizado(Cliente.nome_fantasia, query).ilike(
                _texto_normalizado(like, query)
            ),
            _texto_normalizado(Cliente.razao_social, query).ilike(
                _texto_normalizado(like, query)
            ),
            Cliente.cpf.ilike(like),
            Cliente.cnpj.ilike(like),
            Cliente.email.ilike(like),
            Cliente.telefone.ilike(like),
            Cliente.celular.ilike(like),
            Cliente.contatos_adicionais.any(
                (ClienteContato.tenant_id == Cliente.tenant_id)
                & (
                    ClienteContato.numero.ilike(like)
                    | ClienteContato.vinculo.ilike(like)
                )
            ),
        ]
        palavra_digitos = "".join(ch for ch in palavra if ch.isdigit())
        if palavra_digitos:
            like_digitos = f"%{palavra_digitos}%"
            if not any(ch.isalpha() for ch in palavra):
                filtros.extend(
                    [
                        _somente_digitos_coluna(Cliente.cpf).ilike(like_digitos),
                        _somente_digitos_coluna(Cliente.cnpj).ilike(like_digitos),
                    ]
                )
            filtros.extend(
                [
                    telefone_digitos.ilike(like_digitos),
                    celular_digitos.ilike(like_digitos),
                    Cliente.contatos_adicionais.any(
                        (ClienteContato.tenant_id == Cliente.tenant_id)
                        & ClienteContato.numero_digitos.ilike(like_digitos)
                    ),
                ]
            )
        query = query.filter(or_(*filtros))
    return query


def _aplicar_filtro_ativo(query, ativo):
    if ativo is None:
        ativo = True
    if ativo:
        return query.filter(or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)))
    return query.filter(Cliente.ativo.is_(False))


def _ordenar_query_listagem(query, search):
    termo_busca = (search or "").strip()
    if not termo_busca:
        return query.order_by(Cliente.nome)

    termo_lower = termo_busca.lower()
    termo_digitos = "".join(ch for ch in termo_busca if ch.isdigit())
    if termo_digitos and not any(ch.isalpha() for ch in termo_busca):
        return query.order_by(
            case(
                (func.lower(Cliente.codigo) == termo_lower, 1),
                (_somente_digitos_coluna(Cliente.telefone) == termo_digitos, 2),
                (_somente_digitos_coluna(Cliente.celular) == termo_digitos, 3),
                (
                    Cliente.contatos_adicionais.any(
                        (ClienteContato.tenant_id == Cliente.tenant_id)
                        & (ClienteContato.numero_digitos == termo_digitos)
                    ),
                    4,
                ),
                (Cliente.codigo.ilike(f"{termo_digitos}%"), 5),
                (
                    _somente_digitos_coluna(Cliente.telefone).ilike(
                        f"{termo_digitos}%"
                    ),
                    6,
                ),
                (
                    _somente_digitos_coluna(Cliente.celular).ilike(f"{termo_digitos}%"),
                    7,
                ),
                (
                    _texto_normalizado(Cliente.nome, query)
                    == _texto_normalizado(termo_busca, query),
                    8,
                ),
                (
                    _texto_normalizado(Cliente.nome, query).ilike(
                        _texto_normalizado(f"{termo_busca}%", query)
                    ),
                    9,
                ),
                (
                    _texto_normalizado(Cliente.nome_fantasia, query).ilike(
                        _texto_normalizado(f"{termo_busca}%", query)
                    ),
                    10,
                ),
                (
                    _texto_normalizado(Cliente.razao_social, query).ilike(
                        _texto_normalizado(f"{termo_busca}%", query)
                    ),
                    11,
                ),
                else_=12,
            ),
            Cliente.nome,
            Cliente.id,
        )

    return query.order_by(
        case(
            (func.lower(Cliente.codigo) == termo_lower, 1),
            (
                _texto_normalizado(Cliente.nome, query)
                == _texto_normalizado(termo_busca, query),
                2,
            ),
            (
                _texto_normalizado(Cliente.nome_fantasia, query)
                == _texto_normalizado(termo_busca, query),
                3,
            ),
            (
                _texto_normalizado(Cliente.razao_social, query)
                == _texto_normalizado(termo_busca, query),
                4,
            ),
            (Cliente.codigo.ilike(f"{termo_busca}%"), 5),
            (
                _texto_normalizado(Cliente.nome, query).ilike(
                    _texto_normalizado(f"{termo_busca}%", query)
                ),
                6,
            ),
            (
                _texto_normalizado(Cliente.nome_fantasia, query).ilike(
                    _texto_normalizado(f"{termo_busca}%", query)
                ),
                7,
            ),
            (
                _texto_normalizado(Cliente.razao_social, query).ilike(
                    _texto_normalizado(f"{termo_busca}%", query)
                ),
                8,
            ),
            else_=9,
        ),
        Cliente.nome,
        Cliente.id,
    )
