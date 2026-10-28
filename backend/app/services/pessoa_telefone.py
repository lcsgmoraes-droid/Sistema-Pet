"""Identidade de telefone da pessoa, sem inferir números nem alterar o histórico."""

import re
import sqlite3
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import String, and_, event, func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import FunctionElement

from app.models import Cliente, ClienteContato

CONSTRAINT_TELEFONE = "uq_pessoa_telefone_escopo"
MENSAGEM_TELEFONE_DUPLICADO = (
    "Este telefone já está vinculado a outra pessoa. "
    "Selecione o cadastro existente ou revise o número informado."
)
_NAO_INFORMADO = object()


def normalizar_telefone_pessoa(valor):
    """Chave ASCII completa; só remove DDI explícito pelo comprimento conhecido."""
    digitos = re.sub(r"[^0-9]", "", str(valor) if valor is not None else "")
    if digitos.startswith("0055") and len(digitos) in (14, 15):
        digitos = digitos[4:]
    elif digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    return digitos or None


@event.listens_for(Engine, "connect")
def _registrar_normalizador_sqlite(conexao, _registro):
    if isinstance(conexao, sqlite3.Connection):
        conexao.create_function(
            "normalizar_telefone_pessoa",
            1,
            normalizar_telefone_pessoa,
            deterministic=True,
        )


class _TelefonePessoaSQL(FunctionElement):
    type = String()
    inherit_cache = True


@compiles(_TelefonePessoaSQL)
def _compilar_telefone_sql(elemento, compilador, **kwargs):
    argumento = compilador.process(list(elemento.clauses)[0], **kwargs)
    return f"public.normalizar_telefone_pessoa({argumento})"


@compiles(_TelefonePessoaSQL, "sqlite")
def _compilar_telefone_sqlite(elemento, compilador, **kwargs):
    argumento = compilador.process(list(elemento.clauses)[0], **kwargs)
    return f"normalizar_telefone_pessoa({argumento})"


def telefone_pessoa_sql(coluna):
    return _TelefonePessoaSQL(coluna)


class PessoaTelefoneDuplicado(HTTPException):
    error_code = "pessoa_telefone_duplicado"

    def __init__(self, campo="telefone"):
        self.campo = campo
        self.loc = ["body", campo]
        super().__init__(status_code=409, detail=MENSAGEM_TELEFONE_DUPLICADO)


def erro_telefone_duplicado(erro):
    origem = getattr(erro, "orig", erro)
    codigo = getattr(origem, "sqlstate", None) or getattr(origem, "pgcode", None)
    diagnostico = getattr(origem, "diag", None)
    return (
        codigo == "23505"
        and getattr(diagnostico, "constraint_name", None) == CONSTRAINT_TELEFONE
    )


def resolver_escopo_telefone_pessoa(db, tenant_id):
    """Todas as lojas de grupos ativos comuns, sem incluir parceiros veterinários."""
    from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
    from app.grupo_comercial_sql import empresa_id_sql

    empresa = str(UUID(str(tenant_id)))
    if db.get_bind().dialect.name == "sqlite":
        from sqlalchemy import inspect

        if not inspect(db.connection()).has_table("grupo_comercial_membros"):
            return [empresa]
    origem = aliased(GrupoComercialMembro)
    destino = aliased(GrupoComercialMembro)
    empresas = (
        db.query(destino.empresa_id)
        .join(GrupoComercial, GrupoComercial.id == destino.grupo_id)
        .join(origem, origem.grupo_id == destino.grupo_id)
        .filter(
            empresa_id_sql(origem.empresa_id) == empresa_id_sql(empresa),
            origem.status == "ativo",
            destino.status == "ativo",
            GrupoComercial.status == "ativo",
        )
        .all()
    )
    return sorted({empresa, *(str(UUID(str(row[0]))) for row in empresas)})


def _numeros_pessoa(pessoa):
    if pessoa is None:
        return set()
    return {
        chave
        for valor in (
            getattr(pessoa, "telefone", None),
            getattr(pessoa, "celular", None),
            *(contato.numero for contato in getattr(pessoa, "contatos_adicionais", ())),
        )
        if (chave := normalizar_telefone_pessoa(valor))
    }


def telefone_em_uso(db, tenant_id, chave, pessoa_id=None):
    if db.get_bind().dialect.name == "postgresql":
        return bool(
            db.scalar(
                select(
                    func.public.pessoa_telefone_em_uso(
                        UUID(str(tenant_id)), pessoa_id, chave
                    )
                )
            )
        )
    return buscar_pessoa_telefone(db, tenant_id, chave, pessoa_id) is not None


def buscar_pessoa_telefone(db, tenant_id, chave, pessoa_id=None):
    escopo = [UUID(item) for item in resolver_escopo_telefone_pessoa(db, tenant_id)]
    pessoas = Cliente.__table__
    contatos = ClienteContato.__table__
    query = select(pessoas).where(
        pessoas.c.tenant_id.in_(escopo),
        pessoas.c.merged_into_id.is_(None),
        or_(
            telefone_pessoa_sql(pessoas.c.telefone) == chave,
            telefone_pessoa_sql(pessoas.c.celular) == chave,
            select(contatos.c.id)
            .where(
                and_(
                    contatos.c.cliente_id == pessoas.c.id,
                    contatos.c.tenant_id == pessoas.c.tenant_id,
                    telefone_pessoa_sql(contatos.c.numero) == chave,
                )
            )
            .exists(),
        ),
    )
    if pessoa_id is not None:
        query = query.where(pessoas.c.id != pessoa_id)
    return db.execute(query.limit(1)).first()


def bloquear_escopo_telefone_pessoa(db, tenant_id):
    if db.get_bind().dialect.name == "postgresql":
        with db.no_autoflush:
            db.execute(
                select(
                    func.public.pessoa_telefone_bloquear_escopo(UUID(str(tenant_id)))
                )
            )


def validar_telefones_pessoa(
    db,
    tenant_id,
    *,
    telefone=_NAO_INFORMADO,
    celular=_NAO_INFORMADO,
    contatos_adicionais=_NAO_INFORMADO,
    pessoa_atual=None,
):
    with db.no_autoflush:
        owner = pessoa_atual.tenant_id if pessoa_atual is not None else tenant_id
        pessoa_id = pessoa_atual.id if pessoa_atual is not None else None
        bloquear_escopo_telefone_pessoa(db, owner)
        if (
            pessoa_atual is not None
            and getattr(pessoa_atual, "merged_into_id", None) is not None
        ):
            return
        anteriores = _numeros_pessoa(pessoa_atual)
        novos = {}
        for campo, valor in (("telefone", telefone), ("celular", celular)):
            if valor is _NAO_INFORMADO:
                valor = getattr(pessoa_atual, campo, None)
            if chave := normalizar_telefone_pessoa(valor):
                novos[chave] = campo
        contatos = contatos_adicionais
        if contatos is _NAO_INFORMADO or contatos is None:
            contatos = getattr(pessoa_atual, "contatos_adicionais", ())
        for contato in contatos:
            valor = (
                contato.get("numero") if isinstance(contato, dict) else contato.numero
            )
            if chave := normalizar_telefone_pessoa(valor):
                novos[chave] = "contatos_adicionais"
        adicionados = set(novos) - anteriores
        if not adicionados:
            return
        for chave in sorted(adicionados):
            if telefone_em_uso(db, owner, chave, pessoa_id):
                raise PessoaTelefoneDuplicado(novos[chave])
