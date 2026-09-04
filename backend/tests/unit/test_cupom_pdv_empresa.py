import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.empresa_routes import (
    DadosCadastraisUpdate,
    atualizar_dados_cadastrais,
    buscar_dados_cupom,
)
from app.models import Tenant


class _FakeQuery:
    def __init__(self, tenant):
        self.tenant = tenant

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.tenant


class _FakeSession:
    def __init__(self, tenant):
        self.tenant = tenant
        self.commits = 0

    def query(self, *args, **kwargs):
        return _FakeQuery(self.tenant)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        return None


def _tenant(**overrides):
    defaults = {
        "id": str(uuid4()),
        "name": "Pet Shop Teste",
        "razao_social": "Pet Shop Teste Ltda",
        "cnpj": "12.345.678/0001-90",
        "endereco": "Rua Teste",
        "numero": "100",
        "complemento": None,
        "bairro": "Centro",
        "cidade": "Andradina",
        "uf": "SP",
        "cep": "16900-000",
        "telefone": "(18) 99999-0000",
        "email": "contato@teste.local",
        "inscricao_estadual": None,
        "inscricao_municipal": None,
        "cupom_cabecalho": "Amor em cada atendimento",
        "cupom_mensagem_final": "Obrigado pela preferência!",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _liberar_permissao(monkeypatch):
    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission",
        lambda *args, **kwargs: True,
    )


def test_dados_cupom_expoem_cadastro_e_textos_do_tenant(monkeypatch):
    _liberar_permissao(monkeypatch)
    tenant = _tenant()

    response = buscar_dados_cupom(
        user_and_tenant=(SimpleNamespace(id=42), tenant.id),
        db=_FakeSession(tenant),
    )

    assert response.nome_fantasia == "Pet Shop Teste"
    assert response.razao_social == "Pet Shop Teste Ltda"
    assert response.cnpj == "12.345.678/0001-90"
    assert response.endereco == "Rua Teste"
    assert response.telefone == "(18) 99999-0000"
    assert response.cupom_cabecalho == "Amor em cada atendimento"
    assert response.cupom_mensagem_final == "Obrigado pela preferência!"


def test_configuracao_da_empresa_salva_textos_opcionais_do_cupom(monkeypatch):
    _liberar_permissao(monkeypatch)
    tenant = _tenant(cupom_cabecalho=None, cupom_mensagem_final=None)
    db = _FakeSession(tenant)

    response = atualizar_dados_cadastrais(
        DadosCadastraisUpdate(
            cupom_cabecalho="Cabeçalho da loja",
            cupom_mensagem_final="Nota final personalizada",
        ),
        user_and_tenant=(SimpleNamespace(id=42), tenant.id),
        db=db,
    )

    assert db.commits == 1
    assert tenant.cupom_cabecalho == "Cabeçalho da loja"
    assert tenant.cupom_mensagem_final == "Nota final personalizada"
    assert response.cupom_cabecalho == "Cabeçalho da loja"
    assert response.cupom_mensagem_final == "Nota final personalizada"


def test_limites_dos_textos_do_cupom_sao_validados():
    with pytest.raises(ValidationError):
        DadosCadastraisUpdate(cupom_cabecalho="x" * 241)

    with pytest.raises(ValidationError):
        DadosCadastraisUpdate(cupom_mensagem_final="x" * 501)


def test_modelo_tenant_declara_colunas_da_configuracao_do_cupom():
    assert "cupom_cabecalho" in Tenant.__table__.columns
    assert "cupom_mensagem_final" in Tenant.__table__.columns
