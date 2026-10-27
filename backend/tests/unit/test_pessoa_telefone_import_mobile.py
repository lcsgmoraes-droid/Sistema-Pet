"""Telefone duplicado nos pontos de escrita fora do CRUD de Pessoas."""

import asyncio
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import importacao_pessoas as planilha
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra os relacionamentos
from app.models import Cliente, ClienteContato
from app.routes.app_mobile_funcionario_pdv import clientes as mobile
from app.routes.app_mobile_funcionario_pdv.schemas import (
    FuncionarioPdvClienteRapidoRequest,
)
from app.services.pessoa_telefone import (
    PessoaTelefoneDuplicado,
    validar_telefones_pessoa,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant


TENANT = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def caso(monkeypatch):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def configurar_transacoes(connection, _record):
        connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def iniciar_transacao(connection):
        connection.exec_driver_sql("BEGIN")

    Base.metadata.create_all(
        engine, tables=[Cliente.__table__, ClienteContato.__table__]
    )
    set_current_tenant(TENANT)
    usuario = SimpleNamespace(id=7)
    # A regra de identidade e o trigger PostgreSQL possuem suites proprias.
    # Aqui exercitamos os limites HTTP/importacao e os savepoints reais.
    monkeypatch.setattr(mobile, "validar_telefones_pessoa", lambda *_a, **_k: None)
    monkeypatch.setattr(planilha, "validar_telefones_pessoa", lambda *_a, **_k: None)
    monkeypatch.setattr(
        mobile, "_get_funcionario_operacional_or_403", lambda *_: (None, TENANT)
    )
    monkeypatch.setattr(mobile, "gerar_codigo_cliente", lambda *_: "MOBILE-1")
    monkeypatch.setattr(mobile, "log_create", lambda *_: None)
    monkeypatch.setattr(mobile, "registrar_uso_funcionalidade", lambda *_: None)
    monkeypatch.setattr(
        mobile,
        "_serialize_funcionario_pdv_cliente",
        lambda pessoa: {"id": pessoa.id, "codigo": pessoa.codigo},
    )
    with Session(engine) as db:
        pessoa = Cliente(
            tenant_id=TENANT,
            user_id=usuario.id,
            codigo="BASE",
            nome="Pessoa original",
            cpf="11111111111",
            telefone="11999990001",
            is_cliente=True,
            ativo=True,
        )
        db.add(pessoa)
        db.commit()
        try:
            yield SimpleNamespace(db=db, usuario=usuario, pessoa_id=pessoa.id)
        finally:
            clear_current_tenant()
    engine.dispose()


def erro_constraint_telefone():
    original = SimpleNamespace(
        sqlstate="23505",
        pgcode="23505",
        diag=SimpleNamespace(constraint_name="uq_pessoa_telefone_escopo"),
    )
    return IntegrityError(
        "INSERT com dado privado", {"telefone": "dado privado"}, original
    )


def importar(caso, linhas):
    workbook = Workbook()
    for numero, dados in enumerate(linhas, start=3):
        valores = {"A": "cliente", "B": "PF", **dados}
        for coluna, valor in valores.items():
            workbook.active[f"{coluna}{numero}"] = valor
    arquivo = BytesIO()
    workbook.save(arquivo)
    arquivo.seek(0)
    return asyncio.run(
        planilha.importar_pessoas(
            UploadFile(filename="pessoas.xlsx", file=arquivo),
            caso.db,
            (caso.usuario, TENANT),
        )
    )


def test_mobile_precheck_antes_de_criar_preserva_pessoa_existente(caso, monkeypatch):
    def verificar(db, tenant_id, *, telefone):
        assert db is caso.db
        assert tenant_id == TENANT
        assert telefone == "11999990001"
        assert not db.new
        raise PessoaTelefoneDuplicado()

    monkeypatch.setattr(mobile, "validar_telefones_pessoa", verificar)
    with pytest.raises(PessoaTelefoneDuplicado) as erro:
        mobile.criar_cliente_rapido_funcionario_pdv(
            FuncionarioPdvClienteRapidoRequest(
                nome="Outra pessoa", telefone="(11) 99999-0001"
            ),
            caso.usuario,
            caso.db,
        )
    assert erro.value.status_code == 409
    assert caso.db.query(Cliente).count() == 1


@pytest.mark.parametrize("origem", ["telefone", "celular", "adicional"])
def test_mobile_guard_real_bloqueia_numero_em_qualquer_contato(
    caso, monkeypatch, origem
):
    pessoa = caso.db.get(Cliente, caso.pessoa_id)
    if origem == "celular":
        pessoa.telefone = None
        pessoa.celular = "(11) 99999-0001"
    elif origem == "adicional":
        pessoa.telefone = None
        caso.db.add(
            ClienteContato(
                tenant_id=TENANT,
                cliente_id=pessoa.id,
                numero="(11) 99999-0001",
                numero_digitos="11999990001",
                vinculo="Contato QA",
            )
        )
    caso.db.commit()
    monkeypatch.setattr(mobile, "validar_telefones_pessoa", validar_telefones_pessoa)

    with pytest.raises(PessoaTelefoneDuplicado):
        mobile.criar_cliente_rapido_funcionario_pdv(
            FuncionarioPdvClienteRapidoRequest(telefone="+55 (11) 99999-0001"),
            caso.usuario,
            caso.db,
        )
    assert caso.db.query(Cliente).count() == 1


def test_mobile_constraint_concorrente_vira_conflito_seguro(caso, monkeypatch):
    commit_original = caso.db.commit

    def concorrer():
        raise erro_constraint_telefone()

    monkeypatch.setattr(caso.db, "commit", concorrer)
    with pytest.raises(PessoaTelefoneDuplicado) as erro:
        mobile.criar_cliente_rapido_funcionario_pdv(
            FuncionarioPdvClienteRapidoRequest(telefone="11999990002"),
            caso.usuario,
            caso.db,
        )
    assert "privado" not in str(erro.value.detail)
    assert caso.db.query(Cliente).count() == 1
    assert not caso.db.new

    monkeypatch.setattr(caso.db, "commit", commit_original)
    resposta = mobile.criar_cliente_rapido_funcionario_pdv(
        FuncionarioPdvClienteRapidoRequest(nome="Pessoa livre", telefone="11999990003"),
        caso.usuario,
        caso.db,
    )
    assert resposta["codigo"] == "MOBILE-1"
    assert caso.db.query(Cliente).count() == 2


def test_mobile_outra_constraint_preserva_mensagem_de_codigo(caso, monkeypatch):
    monkeypatch.setattr(mobile, "gerar_codigo_cliente", lambda *_: "BASE")
    with pytest.raises(HTTPException) as erro:
        mobile.criar_cliente_rapido_funcionario_pdv(
            FuncionarioPdvClienteRapidoRequest(telefone="11999990004"),
            caso.usuario,
            caso.db,
        )
    assert erro.value.status_code == 409
    assert "codigo" in erro.value.detail
    assert not isinstance(erro.value, PessoaTelefoneDuplicado)
    assert caso.db.query(Cliente).count() == 1


def test_excel_precheck_nao_altera_cadastro_e_continua_linha_valida(caso, monkeypatch):
    def verificar(db, tenant_id, *, telefone, celular, pessoa_atual):
        assert tenant_id == TENANT
        if pessoa_atual is not None:
            assert pessoa_atual.nome == "Pessoa original"
            assert pessoa_atual.telefone == "11999990001"
            assert not pessoa_atual.is_fornecedor
            raise PessoaTelefoneDuplicado(campo="telefone")

    monkeypatch.setattr(planilha, "validar_telefones_pessoa", verificar)
    resposta = importar(
        caso,
        [
            {
                "A": "fornecedor",
                "D": "Nome que nao deve persistir",
                "E": "11111111111",
                "K": "11999990009",
            },
            {"C": "OK-1", "D": "Pessoa valida", "E": "22222222222", "K": "11999990002"},
        ],
    )
    assert resposta["sucesso"] is True
    assert len(resposta["criados"]) == 1
    assert resposta["atualizados"] == []
    assert resposta["erros"][0]["error_code"] == "pessoa_telefone_duplicado"
    original = caso.db.get(Cliente, caso.pessoa_id)
    assert original.nome == "Pessoa original"
    assert original.telefone == "11999990001"
    assert not original.is_fornecedor
    novo = caso.db.query(Cliente).filter(Cliente.codigo == "OK-1").one()
    assert novo.user_id == caso.usuario.id
    assert novo.tenant_id == TENANT


def test_excel_conflito_no_flush_desfaz_toda_linha_e_permite_proxima(caso):
    @event.listens_for(caso.db, "before_flush")
    def concorrencia(_session, _context, _instances):
        for pessoa in caso.db.dirty:
            if isinstance(pessoa, Cliente) and pessoa.telefone == "11999990009":
                raise erro_constraint_telefone()

    resposta = importar(
        caso,
        [
            {
                "D": "Nome invalido",
                "E": "11111111111",
                "K": "11999990009",
            },
            {
                "C": "OK-2",
                "D": "Pessoa seguinte",
                "E": "22222222222",
                "K": "11999990002",
            },
        ],
    )
    assert resposta["sucesso"] is True
    assert len(resposta["criados"]) == 1
    assert resposta["atualizados"] == []
    assert resposta["total_processados"] == 2
    assert resposta["erros"][0]["error_code"] == "pessoa_telefone_duplicado"
    assert "privado" not in resposta["erros"][0]["erro"]
    original = caso.db.get(Cliente, caso.pessoa_id)
    assert original.nome == "Pessoa original"
    assert original.telefone == "11999990001"
    assert caso.db.query(Cliente).count() == 2


def test_excel_erro_sql_entre_linhas_validas_nao_vaza_sql_nem_aborta_lote(caso):
    resposta = importar(
        caso,
        [
            {
                "C": "OK-3",
                "D": "Valida anterior",
                "E": "22222222222",
                "K": "11999990002",
            },
            {
                "C": "BASE",
                "D": "Colisao de codigo",
                "E": "33333333333",
                "K": "11999990003",
            },
            {
                "C": "OK-4",
                "D": "Valida posterior",
                "E": "44444444444",
                "K": "11999990004",
            },
        ],
    )
    assert resposta["sucesso"] is True
    assert len(resposta["criados"]) == 2
    assert resposta["total_erros"] == 1
    assert resposta["total_processados"] == 3
    assert resposta["erros"][0]["linha"] == 4
    assert "INSERT" not in resposta["erros"][0]["erro"]
    assert "UNIQUE" not in resposta["erros"][0]["erro"]
    assert "error_code" not in resposta["erros"][0]
    assert caso.db.query(Cliente).count() == 3


def test_excel_guard_real_recusa_duplicata_dentro_do_arquivo(caso, monkeypatch):
    monkeypatch.setattr(planilha, "validar_telefones_pessoa", validar_telefones_pessoa)
    resposta = importar(
        caso,
        [
            {
                "C": "UNICO-1",
                "D": "Primeira pessoa",
                "E": "22222222222",
                "K": "(11) 99999-0002",
            },
            {
                "C": "DUPLICADO",
                "D": "Outra pessoa mesmo numero",
                "E": "33333333333",
                "L": "+55 (11) 99999-0002",
            },
            {
                "C": "UNICO-2",
                "D": "Pessoa seguinte",
                "E": "44444444444",
                "K": "11999990004",
            },
        ],
    )
    assert resposta["sucesso"] is True
    assert len(resposta["criados"]) == 2
    assert resposta["total_erros"] == 1
    assert resposta["erros"][0]["linha"] == 4
    assert resposta["erros"][0]["error_code"] == "pessoa_telefone_duplicado"
    assert caso.db.query(Cliente).filter(Cliente.codigo == "DUPLICADO").count() == 0
    assert caso.db.query(Cliente).count() == 3


def test_excel_falha_commit_global_desfaz_linhas_sem_expor_dados(caso, monkeypatch):
    def falhar():
        raise erro_constraint_telefone()

    monkeypatch.setattr(caso.db, "commit", falhar)
    resposta = importar(
        caso,
        [
            {
                "C": "OK-5",
                "D": "Linha provisoria",
                "E": "22222222222",
                "K": "11999990002",
            }
        ],
    )
    assert resposta["sucesso"] is False
    assert resposta["error_code"] == "pessoa_telefone_duplicado"
    assert "privado" not in resposta["erro"]
    assert caso.db.query(Cliente).count() == 1
