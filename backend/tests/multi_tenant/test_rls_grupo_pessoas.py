"""RLS de pessoas no grupo comercial, testado com um papel sem bypass de RLS.

O usuario da aplicacao em desenvolvimento e superusuario (ignora RLS), por isso
o teste troca para um papel comum dentro de uma transacao revertida.
"""

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.models_cadastros import Cliente
from app.tenancy.context import clear_current_tenant, set_current_tenant

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not DATABASE_URL.startswith("postgresql"), reason="requer Postgres")

PAPEL = "petshop_rls_teste"


@pytest.fixture()
def conexao():
    engine = create_engine(DATABASE_URL)
    con = engine.connect()
    tx = con.begin()
    try:
        yield con
    finally:
        tx.rollback()
        con.close()
        engine.dispose()


def _preparar(con):
    con.execute(text(f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{PAPEL}') THEN CREATE ROLE {PAPEL} NOLOGIN NOBYPASSRLS; END IF; END $$"))
    for tabela in ("clientes", "pets", "grupo_comercial_membros", "grupos_comerciais", "vet_partner_link", "tenants"):
        con.execute(text(f"GRANT SELECT, UPDATE ON {tabela} TO {PAPEL}"))
    loja_a, loja_b, loja_fora = str(uuid4()), str(uuid4()), str(uuid4())
    for loja, nome in ((loja_a, "A"), (loja_b, "B"), (loja_fora, "Fora")):
        con.execute(text("INSERT INTO tenants (id, name, name_normalized, status) VALUES (:i, :n, :n, 'active')"), {"i": loja, "n": f"loja-{nome}-{loja[:6]}"})
    grupo = con.execute(text("INSERT INTO grupos_comerciais (nome, criado_por_empresa_id, criado_por_usuario_id, status) VALUES ('G', :a, 1, 'ativo') RETURNING id"), {"a": loja_a}).scalar()
    for loja in (loja_a, loja_b):
        con.execute(text("INSERT INTO grupo_comercial_membros (grupo_id, empresa_id, status) VALUES (:g, :l, 'ativo')"), {"g": grupo, "l": loja})
    usuario = con.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    set_current_tenant(loja_a)
    sessao = Session(bind=con)
    cliente = Cliente(tenant_id=UUID(loja_a), origem_tenant_id=UUID(loja_a), user_id=usuario, nome="Pessoa do grupo", is_cliente=True)
    sessao.add(cliente)
    sessao.flush()
    pessoa = cliente.id
    clear_current_tenant()
    return loja_a, loja_b, loja_fora, pessoa


def _como_loja(con, loja):
    con.execute(text(f"SET LOCAL ROLE {PAPEL}"))
    con.execute(text("SELECT set_config('app.tenant_id', :l, true)"), {"l": loja})


def test_loja_do_grupo_le_pessoa_de_outra_loja(conexao):
    loja_a, loja_b, _fora, pessoa = _preparar(conexao)
    _como_loja(conexao, loja_b)
    visiveis = conexao.execute(text("SELECT id FROM clientes WHERE id = :i"), {"i": pessoa}).scalars().all()
    assert visiveis == [pessoa]


def test_loja_de_fora_do_grupo_nao_le_a_pessoa(conexao):
    _loja_a, _loja_b, loja_fora, pessoa = _preparar(conexao)
    _como_loja(conexao, loja_fora)
    visiveis = conexao.execute(text("SELECT id FROM clientes WHERE id = :i"), {"i": pessoa}).scalars().all()
    assert visiveis == []


def test_loja_do_grupo_altera_pessoa_de_outra_loja(conexao):
    loja_a, loja_b, _fora, pessoa = _preparar(conexao)
    _como_loja(conexao, loja_b)
    alteradas = conexao.execute(text("UPDATE clientes SET nome = 'Nome novo' WHERE id = :i"), {"i": pessoa}).rowcount
    assert alteradas == 1


def test_loja_de_fora_nao_altera_pessoa(conexao):
    _loja_a, _loja_b, loja_fora, pessoa = _preparar(conexao)
    _como_loja(conexao, loja_fora)
    alteradas = conexao.execute(text("UPDATE clientes SET nome = 'Invasao' WHERE id = :i"), {"i": pessoa}).rowcount
    assert alteradas == 0
