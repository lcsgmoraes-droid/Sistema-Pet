"""Identidade de telefone no PostgreSQL efêmero: isolamento, legado e concorrência.

Opt-in exige URL local de teste e schema migrado. Nunca aceita petshop_dev.
As poucas operações concorrentes com commit usam tenants fictícios e limpeza
explícita; todas as outras operações terminam em rollback.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import os
from threading import Event
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app import financeiro_models, produto_identidade_models  # noqa: F401
from app.grupo_comercial_models import GrupoComercial, GrupoComercialMembro
from app.models import Cliente, ClienteContato, Tenant, User
from app.services import pessoa_merge_service
from app.services.pessoa_telefone import (
    normalizar_telefone_pessoa,
    validar_telefones_pessoa,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas_models import Venda


@pytest.fixture(scope="module")
def engine():
    raw = os.getenv("PESSOA_TELEFONE_TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Informe PESSOA_TELEFONE_TEST_POSTGRES_URL de banco efêmero local")
    url = make_url(raw)
    assert os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}
    assert url.get_backend_name() == "postgresql"
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    banco = str(url.database)
    assert banco != "petshop_dev"
    assert banco.endswith(("_test", "_ci")) or banco.startswith(
        "petshop_migration_smoke_"
    )
    db_engine = create_engine(raw, pool_size=5, max_overflow=3)
    try:
        with db_engine.connect() as conn:
            assert conn.scalar(text("SELECT current_database()")) == banco
            assert conn.scalar(
                text(
                    "SELECT to_regprocedure('public.pessoa_telefone_em_uso(uuid,integer,text,integer)') IS NOT NULL"
                )
            ), "Aplique a migração de telefone no banco efêmero"
        yield db_engine
    finally:
        db_engine.dispose()


def _contexto(conn, tenant):
    conn.execute(
        text("SELECT set_config('app.tenant_id', :tenant, true)"),
        {"tenant": str(tenant) if tenant else ""},
    )
    conn.execute(text("SET LOCAL statement_timeout='12s'"))
    conn.execute(text("SET LOCAL lock_timeout='10s'"))


@pytest.fixture
def caso(engine):
    token = uuid4().hex[:12]
    empresas = [uuid4() for _ in range(4)]
    conn = engine.connect()
    usuarios = []
    grupos = []
    try:
        for indice, empresa in enumerate(empresas):
            conn.execute(
                Tenant.__table__.insert().values(
                    id=str(empresa),
                    name=f"QA telefone {token} {indice}",
                    name_normalized=f"qa telefone {token} {indice}",
                )
            )
            usuarios.append(
                conn.execute(
                    User.__table__.insert().values(
                        tenant_id=empresa,
                        username=f"qa-phone-{token}-{indice}",
                        nome="Operador fictício telefone",
                        is_active=True,
                    )
                ).inserted_primary_key[0]
            )
        _contexto(conn, empresas[0])
        yield SimpleNamespace(
            engine=engine,
            conn=conn,
            empresas=empresas,
            usuarios=usuarios,
            grupos=grupos,
            token=token,
        )
    finally:
        conn.rollback()
        conn.close()
        clear_current_tenant()
        # Só alcança massa que foi confirmada pelos testes de duas conexões.
        with engine.begin() as limpeza:
            assert (
                limpeza.scalar(
                    text("SELECT count(*) FROM pg_roles WHERE rolname=:role"),
                    {"role": f"qa_phone_{token}"},
                )
                == 0
            )
            _contexto(limpeza, empresas[0])
            valores = {"lojas": [str(item) for item in empresas]}
            for tabela in (
                "pessoa_merge_logs",
                "app_access_profiles",
                "audit_logs",
                "vendas",
                "cliente_contatos",
                "clientes",
            ):
                limpeza.execute(
                    text(
                        f"DELETE FROM public.{tabela} WHERE tenant_id::text = ANY(:lojas)"
                    ),
                    valores,
                )
            if grupos:
                limpeza.execute(
                    text(
                        "DELETE FROM grupo_comercial_membros WHERE grupo_id = ANY(:grupos)"
                    ),
                    {"grupos": grupos},
                )
                limpeza.execute(
                    text("DELETE FROM grupos_comerciais WHERE id = ANY(:grupos)"),
                    {"grupos": grupos},
                )
            limpeza.execute(
                text("DELETE FROM users WHERE tenant_id::text = ANY(:lojas)"), valores
            )
            limpeza.execute(
                text("DELETE FROM tenants WHERE id::text = ANY(:lojas)"), valores
            )


def _grupo(c, indices=(0, 1), *, status="ativo"):
    grupo = c.conn.execute(
        GrupoComercial.__table__.insert().values(
            nome=f"QA telefone {c.token}-{len(c.grupos)}",
            criado_por_empresa_id=str(c.empresas[0]),
            criado_por_usuario_id=c.usuarios[0],
            status=status,
        )
    ).inserted_primary_key[0]
    c.grupos.append(grupo)
    for indice in indices:
        _membro(c.conn, c, grupo, indice)
    return grupo


def _membro(conn, c, grupo, indice, *, status="ativo"):
    return conn.execute(
        GrupoComercialMembro.__table__.insert().values(
            grupo_id=grupo,
            empresa_id=str(c.empresas[indice]),
            status=status,
        )
    ).inserted_primary_key[0]


def _pessoa(conn, c, indice=0, *, telefone=None, celular=None, **extras):
    _contexto(conn, c.empresas[indice])
    return conn.execute(
        Cliente.__table__.insert().values(
            tenant_id=c.empresas[indice],
            origem_tenant_id=c.empresas[indice],
            user_id=c.usuarios[indice],
            codigo=f"QA-{uuid4().hex[:16]}",
            nome="Pessoa fictícia telefone",
            telefone=telefone,
            celular=celular,
            is_cliente=True,
            ativo=True,
            **extras,
        )
    ).inserted_primary_key[0]


def _contato(conn, c, pessoa, numero, *, indice=0):
    _contexto(conn, c.empresas[indice])
    return conn.execute(
        ClienteContato.__table__.insert().values(
            tenant_id=c.empresas[indice],
            cliente_id=pessoa,
            numero=numero,
            numero_digitos=normalizar_telefone_pessoa(numero),
            vinculo="Contato QA",
        )
    ).inserted_primary_key[0]


def _sqlstate(erro):
    return getattr(erro.orig, "sqlstate", None) or getattr(erro.orig, "pgcode", None)


def _rejeitar(conn, operacao, codigo="23505"):
    with pytest.raises(DBAPIError) as capturado:
        with conn.begin_nested():
            operacao()
    assert _sqlstate(capturado.value) == codigo
    if codigo == "23505":
        assert capturado.value.orig.diag.constraint_name == "uq_pessoa_telefone_escopo"


def test_normalizacao_python_sql_concorda_sem_inferir_numeros(engine):
    valores = (
        None,
        "",
        "   ",
        "abc",
        "123",
        "(11) 3333-4444",
        "+55 (11) 3333-4444",
        "0055 11 3333 4444",
        "(11) 99999-0001",
        "+55 (11) 99999-0001",
        "0055 11 99999 0001",
        "+1 (212) 555-1234",
        "55",
        "５５１１９９９９９０００１",
    )
    with engine.connect() as conn:
        for valor in valores:
            assert conn.scalar(
                text("SELECT public.normalizar_telefone_pessoa(:valor)"),
                {"valor": valor},
            ) == normalizar_telefone_pessoa(valor)


def test_principal_adicional_ddi_grupo_e_loja_independente(caso):
    c = caso
    _grupo(c)
    titular = _pessoa(c.conn, c, telefone="(11) 3333-4444")
    _contato(c.conn, c, titular, "(11) 99999-0001")
    _rejeitar(c.conn, lambda: _pessoa(c.conn, c, 1, celular="+55 (11) 3333-4444"))
    _rejeitar(c.conn, lambda: _pessoa(c.conn, c, 1, telefone="0055 11 99999 0001"))
    outra = _pessoa(c.conn, c, 1)
    _rejeitar(c.conn, lambda: _contato(c.conn, c, outra, "+55 11 3333-4444", indice=1))
    livre = _pessoa(c.conn, c, 3, telefone="+55 (11) 3333-4444")
    assert livre != titular
    # Repetir a chave na própria pessoa não cria outra titularidade.
    _contato(c.conn, c, titular, "+55 11 3333-4444")


def test_insert_multilinha_enxerga_linha_anterior_e_aborta_statement(caso):
    c = caso
    _contexto(c.conn, c.empresas[0])
    codigos = [f"MULTI-{c.token}-1", f"MULTI-{c.token}-2"]
    linhas = [
        dict(
            tenant_id=c.empresas[0],
            user_id=c.usuarios[0],
            codigo=codigos[0],
            nome="Primeira QA",
            telefone="11999990001",
            celular=None,
        ),
        dict(
            tenant_id=c.empresas[0],
            user_id=c.usuarios[0],
            codigo=codigos[1],
            nome="Segunda QA",
            telefone=None,
            celular="+55 11 99999-0001",
        ),
    ]
    _rejeitar(c.conn, lambda: c.conn.execute(Cliente.__table__.insert().values(linhas)))
    assert (
        c.conn.scalar(
            text("SELECT count(*) FROM clientes WHERE codigo = ANY(:codigos)"),
            {"codigos": codigos},
        )
        == 0
    )


def test_legado_nao_e_reescrito_e_nova_atribuicao_e_bloqueada(caso):
    c = caso
    # DDL transacional: até uma falha do teste restaura o trigger no rollback.
    with c.conn.begin_nested():
        c.conn.execute(
            text("ALTER TABLE clientes DISABLE TRIGGER pessoa_telefone_guard")
        )
        a = _pessoa(c.conn, c, telefone="11999990001")
        b = _pessoa(c.conn, c, celular="+55 11 99999-0001")
        c.conn.execute(
            text("ALTER TABLE clientes ENABLE TRIGGER pessoa_telefone_guard")
        )
    c.conn.execute(
        text("UPDATE clientes SET nome='Nome legado atualizado' WHERE id=:id"),
        {"id": a},
    )
    c.conn.execute(text("UPDATE clientes SET telefone=NULL WHERE id=:id"), {"id": a})
    _rejeitar(c.conn, lambda: _pessoa(c.conn, c, telefone="11999990001"))
    c.conn.execute(text("UPDATE clientes SET celular=NULL WHERE id=:id"), {"id": b})
    _pessoa(c.conn, c, telefone="11999990001")
    assert (
        c.conn.scalar(text("SELECT nome FROM clientes WHERE id=:id"), {"id": a})
        == "Nome legado atualizado"
    )


def test_alias_nao_reserva_mas_inativo_reserva_numero(caso):
    c = caso
    inativo = _pessoa(c.conn, c, telefone="11999990001")
    c.conn.execute(
        text("UPDATE clientes SET ativo=false WHERE id=:id"), {"id": inativo}
    )
    _rejeitar(c.conn, lambda: _pessoa(c.conn, c, celular="11999990001"))
    alias = _pessoa(c.conn, c, telefone="11999990002", merged_into_id=inativo)
    nova = _pessoa(c.conn, c, celular="+55 11 99999-0002")
    assert alias != nova
    assert (
        c.conn.scalar(text("SELECT telefone FROM clientes WHERE id=:id"), {"id": alias})
        == "11999990002"
    )


def test_contexto_ausente_ou_empresa_nao_compartilhada_falha_fechado(caso):
    c = caso
    pessoa = _pessoa(c.conn, c)
    _contexto(c.conn, None)
    _rejeitar(
        c.conn,
        lambda: c.conn.execute(
            text("UPDATE clientes SET telefone='11999990001' WHERE id=:id"),
            {"id": pessoa},
        ),
        "42501",
    )
    _contexto(c.conn, c.empresas[1])
    _rejeitar(
        c.conn,
        lambda: c.conn.execute(
            text("UPDATE clientes SET telefone='11999990001' WHERE id=:id"),
            {"id": pessoa},
        ),
        "42501",
    )


def test_ator_b_editando_dona_a_considera_outro_grupo_de_a(caso):
    c = caso
    _grupo(c, (0, 1))
    _grupo(c, (0, 2))
    _pessoa(c.conn, c, 2, telefone="11999990001")
    alvo = _pessoa(c.conn, c, 0)
    _contexto(c.conn, c.empresas[1])
    _rejeitar(
        c.conn,
        lambda: c.conn.execute(
            text("UPDATE clientes SET telefone='11999990001' WHERE id=:id"),
            {"id": alvo},
        ),
    )


def test_repeatable_read_nao_atribui_numero_com_snapshot_antigo(caso):
    c = caso
    c.conn.commit()
    with c.engine.connect().execution_options(
        isolation_level="REPEATABLE READ"
    ) as conn:
        _contexto(conn, c.empresas[0])
        _rejeitar(conn, lambda: _pessoa(conn, c, telefone="11999990001"), "40001")


def _sinal():
    return SimpleNamespace(iniciada=Event(), concluida=Event(), pid=None)


def _concorrente(c, sinal, operacao):
    try:
        with c.engine.begin() as conn:
            _contexto(conn, c.empresas[0])
            sinal.pid = conn.scalar(text("SELECT pg_backend_pid()"))
            sinal.iniciada.set()
            operacao(conn)
        return None
    except DBAPIError as erro:
        return (_sqlstate(erro), getattr(erro.orig.diag, "constraint_name", None))
    finally:
        sinal.concluida.set()


def _aguardar_lock(engine, sinal):
    assert sinal.iniciada.wait(4)
    limite = time.monotonic() + 4
    with engine.connect() as observador:
        while time.monotonic() < limite:
            if observador.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=:pid AND locktype='advisory' AND NOT granted)"
                ),
                {"pid": sinal.pid},
            ):
                return
            if sinal.concluida.is_set():
                break
            time.sleep(0.01)
    pytest.fail("A segunda operação não aguardou o advisory lock esperado")


@pytest.mark.parametrize("confirmar", [True, False])
def test_concorrencia_numero_aguarda_commit_ou_rollback_e_libera_outra_loja(
    caso, confirmar
):
    c = caso
    _grupo(c)
    c.conn.commit()
    _pessoa(c.conn, c, telefone="11999990001")
    sinal = _sinal()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futuro = pool.submit(
            _concorrente,
            c,
            sinal,
            lambda conn: _pessoa(conn, c, 1, celular="+55 11 99999-0001"),
        )
        try:
            _aguardar_lock(c.engine, sinal)
            livre = pool.submit(
                _concorrente,
                c,
                _sinal(),
                lambda conn: _pessoa(conn, c, 3, telefone="11999990001"),
            )
            assert livre.result(timeout=4) is None
            c.conn.commit() if confirmar else c.conn.rollback()
            assert futuro.result(timeout=6) == (
                ("23505", "uq_pessoa_telefone_escopo") if confirmar else None
            )
        finally:
            c.conn.rollback()


def test_edicao_legada_nome_e_contato_pretrava_antes_da_tupla(caso):
    c = caso
    pessoa_id = _pessoa(c.conn, c, telefone="11999990001")
    c.conn.commit()
    _contexto(c.conn, c.empresas[0])
    set_current_tenant(c.empresas[0])
    with Session(bind=c.conn) as db:
        pessoa = db.get(Cliente, pessoa_id)
        validar_telefones_pessoa(db, c.empresas[0], pessoa_atual=pessoa)
        pessoa.nome = "Nome atualizado antes do contato"
        db.flush()
        sinal = _sinal()
        with ThreadPoolExecutor(max_workers=1) as pool:
            futuro = pool.submit(
                _concorrente,
                c,
                sinal,
                lambda conn: conn.execute(
                    text("UPDATE clientes SET telefone='11999990003' WHERE id=:id"),
                    {"id": pessoa_id},
                ),
            )
            try:
                _aguardar_lock(c.engine, sinal)
                _contato(c.conn, c, pessoa_id, "11999990002")
                c.conn.commit()
                assert futuro.result(timeout=6) is None
            finally:
                c.conn.rollback()
    assert (
        c.conn.scalar(
            text("SELECT telefone FROM clientes WHERE id=:id"), {"id": pessoa_id}
        )
        == "11999990003"
    )


@pytest.mark.parametrize("mudanca", ["unir", "grupo", "membro"])
def test_topologia_recusa_uniao_ou_reativacao_com_colisao(caso, mudanca):
    c = caso
    grupo = _grupo(
        c,
        (0, 1) if mudanca == "grupo" else (0,),
        status="inativo" if mudanca == "grupo" else "ativo",
    )
    if mudanca == "membro":
        membro = _membro(c.conn, c, grupo, 1, status="removido")
    _pessoa(c.conn, c, telefone="11999990001")
    _pessoa(c.conn, c, 1, celular="+55 11 99999-0001")
    if mudanca == "grupo":
        _rejeitar(
            c.conn,
            lambda: c.conn.execute(
                text("UPDATE grupos_comerciais SET status='ativo' WHERE id=:id"),
                {"id": grupo},
            ),
        )
    elif mudanca == "membro":
        _rejeitar(
            c.conn,
            lambda: c.conn.execute(
                text("UPDATE grupo_comercial_membros SET status='ativo' WHERE id=:id"),
                {"id": membro},
            ),
        )
    else:
        _rejeitar(c.conn, lambda: _membro(c.conn, c, grupo, 1))


@pytest.mark.parametrize("confirmar", [True, False])
def test_topologia_concorrente_aguarda_phone_e_revalida(caso, confirmar):
    c = caso
    grupo = _grupo(c, (0,))
    _pessoa(c.conn, c, 1, telefone="11999990001")
    c.conn.commit()
    _pessoa(c.conn, c, telefone="11999990001")
    sinal = _sinal()
    with ThreadPoolExecutor(max_workers=1) as pool:
        futuro = pool.submit(
            _concorrente, c, sinal, lambda conn: _membro(conn, c, grupo, 1)
        )
        try:
            _aguardar_lock(c.engine, sinal)
            c.conn.commit() if confirmar else c.conn.rollback()
            assert futuro.result(timeout=6) == (
                ("23505", "uq_pessoa_telefone_escopo") if confirmar else None
            )
        finally:
            c.conn.rollback()


def test_boolean_security_definer_ve_colisao_sem_abrir_select_outra_loja(caso):
    c = caso
    _grupo(c, (0, 1))
    _grupo(c, (0, 2))
    pessoa_c = _pessoa(c.conn, c, 2)
    _contato(c.conn, c, pessoa_c, "11999990001", indice=2)
    role = f"qa_phone_{c.token}"
    # O nome vem exclusivamente de uuid.hex; CREATE ROLE e grants têm rollback.
    c.conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
    c.conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
    c.conn.execute(
        text(
            f"GRANT SELECT ON clientes, cliente_contatos, vet_partner_link, "
            f"grupos_comerciais, grupo_comercial_membros TO {role}"
        )
    )
    try:
        with c.conn.begin_nested():
            c.conn.execute(text(f"SET LOCAL ROLE {role}"))
            _contexto(c.conn, c.empresas[1])
            assert (
                c.conn.scalar(
                    text("SELECT count(*) FROM clientes WHERE tenant_id=:tenant"),
                    {"tenant": c.empresas[2]},
                )
                == 0
            )
            assert (
                c.conn.scalar(
                    text(
                        "SELECT count(*) FROM cliente_contatos WHERE tenant_id=:tenant"
                    ),
                    {"tenant": c.empresas[2]},
                )
                == 0
            )
            assert (
                c.conn.scalar(
                    text(
                        "SELECT public.pessoa_telefone_em_uso(:dona, NULL, '11999990001')"
                    ),
                    {"dona": c.empresas[0]},
                )
                is True
            )
            assert (
                c.conn.scalar(
                    text(
                        "SELECT has_function_privilege(current_user, 'public._pessoa_telefone_lojas(uuid)', 'EXECUTE')"
                    )
                )
                is False
            )
            _rejeitar(
                c.conn,
                lambda: c.conn.scalar(
                    text(
                        "SELECT public.pessoa_telefone_em_uso(:dona, NULL, '11999990001')"
                    ),
                    {"dona": c.empresas[3]},
                ),
                "42501",
            )
    finally:
        c.conn.execute(text("RESET ROLE"))


def test_fusao_atomica_preserva_numero_contato_venda_e_log(caso, monkeypatch):
    c = caso
    principal = _pessoa(c.conn, c)
    duplicado = _pessoa(c.conn, c, telefone="11999990001")
    contato = _contato(c.conn, c, duplicado, "11999990002")
    venda = c.conn.execute(
        Venda.__table__.insert().values(
            tenant_id=c.empresas[0],
            user_id=c.usuarios[0],
            vendedor_id=c.usuarios[0],
            cliente_id=duplicado,
            numero_venda=f"QP-{c.token}",
            subtotal=Decimal("37.25"),
            total=Decimal("37.25"),
            status="finalizada",
        )
    ).inserted_primary_key[0]
    set_current_tenant(c.empresas[0])
    with Session(bind=c.conn) as db:
        parametros = dict(
            tenant_id=c.empresas[0],
            principal_id=principal,
            duplicado_id=duplicado,
            decisoes_campos={},
            user_id=c.usuarios[0],
            commit=False,
        )

        def falhar(*_a, **_k):
            raise RuntimeError("Falha QA antes de concluir a fusão")

        with monkeypatch.context() as patch:
            patch.setattr(pessoa_merge_service, "transferir_referencias_pessoa", falhar)
            with pytest.raises(RuntimeError):
                with db.begin_nested():
                    pessoa_merge_service.executar_fusao_pessoas(db, **parametros)
        db.expire_all()
        assert db.get(Cliente, duplicado).merged_into_id is None
        assert db.get(Cliente, principal).telefone is None
        assert db.get(Venda, venda).cliente_id == duplicado
        resultado = pessoa_merge_service.executar_fusao_pessoas(db, **parametros)
        db.flush()
        db.expire_all()
        original = db.get(Venda, venda)
        assert (
            original.id,
            original.numero_venda,
            original.status,
            original.total,
        ) == (venda, f"QP-{c.token}", "finalizada", Decimal("37.25"))
        assert original.cliente_id == principal
        assert db.get(Cliente, duplicado).merged_into_id == principal
        assert db.get(Cliente, duplicado).telefone == "11999990001"
        assert db.get(ClienteContato, contato).cliente_id == principal
        assert resultado["merge_log_id"]
