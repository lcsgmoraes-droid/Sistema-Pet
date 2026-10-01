from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.produtos import estado_routes
from app.produtos_models import ProdutoHistoricoPreco


class FakeQuery:
    def __init__(self, produto):
        self.produto = produto

    def filter(self, *args):
        return self

    def with_for_update(self):
        return self

    def populate_existing(self):
        return self

    def first(self):
        return self.produto


class FakeDb:
    def __init__(self, produto):
        self.produto = produto
        self.adicionados = []
        self.commits = 0

    def query(self, model):
        return FakeQuery(self.produto)

    def add(self, valor):
        self.adicionados.append(valor)

    def commit(self):
        self.commits += 1


def montar_cenario(monkeypatch):
    tenant_id = uuid4()
    produto = SimpleNamespace(
        id=17,
        codigo="2024",
        e_granel=True,
        unidade="KG",
        deleted_at=None,
        ativo=True,
        situacao=True,
        preco_venda=24.77,
        preco_custo=16.2,
        preco_promocional=None,
        promocao_inicio=None,
        promocao_fim=None,
        updated_at=None,
    )
    db = FakeDb(produto)
    monkeypatch.setattr(
        estado_routes.EmpresaGrupoEstoqueCompartilhadoService,
        "resolver_produto_catalogo",
        lambda *_args: SimpleNamespace(tenant_origem_id=tenant_id),
    )
    monkeypatch.setattr(estado_routes, "set_current_tenant", lambda _tenant_id: None)
    usuario = SimpleNamespace(id=9)
    return db, produto, (usuario, tenant_id)


def corrigir(db, usuario_tenant, preco_esperado="24.77"):
    payload = estado_routes.PrecoEtiquetaBalancaUpdate(
        preco_kg_etiqueta="28.90",
        preco_kg_sistema_esperado=preco_esperado,
        codigo_etiqueta="2002024008961",
    )
    return estado_routes.atualizar_preco_etiqueta_balanca.__wrapped__(
        17, payload, db, usuario_tenant
    )


def test_corrige_preco_granel_e_registra_historico(monkeypatch):
    db, produto, usuario_tenant = montar_cenario(monkeypatch)

    resposta = corrigir(db, usuario_tenant)

    assert resposta == {"produto_id": 17, "preco_venda": 28.9}
    assert produto.preco_venda == 28.9
    assert db.commits == 1
    assert len(db.adicionados) == 1
    historico = db.adicionados[0]
    assert isinstance(historico, ProdutoHistoricoPreco)
    assert historico.preco_venda_anterior == 24.77
    assert historico.preco_venda_novo == 28.9
    assert historico.referencia == "2002024008961"
    assert historico.user_id == 9


def test_bloqueia_preco_alterado_depois_da_leitura(monkeypatch):
    db, produto, usuario_tenant = montar_cenario(monkeypatch)
    produto.preco_venda = 25.00

    with pytest.raises(HTTPException) as erro:
        corrigir(db, usuario_tenant)

    assert erro.value.status_code == 409
    assert db.commits == 0


def test_bloqueia_promocao_ativa_e_etiqueta_de_outro_produto(monkeypatch):
    db, produto, usuario_tenant = montar_cenario(monkeypatch)
    produto.preco_promocional = 20.00

    with pytest.raises(HTTPException) as erro:
        corrigir(db, usuario_tenant, preco_esperado="20.00")
    assert erro.value.status_code == 409
    assert "promocao" in erro.value.detail

    produto.preco_promocional = None
    produto.codigo = "2025"
    with pytest.raises(HTTPException) as erro:
        corrigir(db, usuario_tenant)
    assert erro.value.status_code == 409
    assert db.commits == 0


def test_bloqueia_codigo_de_etiqueta_invalido(monkeypatch):
    db, _produto, usuario_tenant = montar_cenario(monkeypatch)
    payload = estado_routes.PrecoEtiquetaBalancaUpdate(
        preco_kg_etiqueta="28.90",
        preco_kg_sistema_esperado="24.77",
        codigo_etiqueta="2002024008962",
    )

    with pytest.raises(HTTPException) as erro:
        estado_routes.atualizar_preco_etiqueta_balanca.__wrapped__(
            17, payload, db, usuario_tenant
        )

    assert erro.value.status_code == 422
    assert db.commits == 0
