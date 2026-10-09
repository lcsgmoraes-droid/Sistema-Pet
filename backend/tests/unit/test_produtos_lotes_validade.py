from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import column

from app.produtos import lotes_validade_routes as routes
from app.estoque.service import EstoqueService
from app.estoque_validade_service import EstoqueValidadeService
from app.estoque.fracionamento_clinico import _lotes_origem_para_consumo
from app.produtos.lotes_routes import listar_lotes
from app.services.ofertas_estudio_service import produto_publicavel
from app.veterinario_financeiro import _consumir_lotes_insumo


class LoteFake(SimpleNamespace):
    produto_id = column("produto_id")
    tenant_id = column("tenant_id")
    status = column("status")

    def __init__(self, **kwargs):
        super().__init__(
            id=kwargs.pop("id", 123),
            created_at=datetime(2026, 10, 9),
            **kwargs,
        )


class QueryFake:
    def __init__(self, produto=None, lotes=None):
        self.produto, self.lotes = produto, lotes

    def filter(self, *args):
        return self

    def with_for_update(self):
        return self

    def join(self, *args):
        return self

    def order_by(self, *args):
        return self

    def get(self, _id):
        return self.produto

    def first(self):
        return self.produto

    def all(self):
        return self.lotes


class DBFake:
    def __init__(self, produto, lotes):
        self.produto, self.lotes = produto, lotes
        self.added, self.commits = [], 0

    def query(self, model):
        return (
            QueryFake(produto=self.produto)
            if model is routes.Produto
            else QueryFake(lotes=self.lotes)
        )

    def add(self, obj):
        obj.id = 123 + len(self.added)
        self.added.append(obj)
        if isinstance(obj, LoteFake):
            self.lotes.append(obj)

    def flush(self):
        pass

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        pass


@pytest.fixture
def setup_rota(monkeypatch):
    produto = SimpleNamespace(
        id=10,
        nome="Produto teste",
        estoque_atual=10,
        preco_custo=7,
        controle_lote=False,
        controlar_estoque=True,
        is_parent=False,
        tipo_produto="SIMPLES",
        tipo_kit=None,
    )
    db = DBFake(produto, [])
    acessos = []

    def resolver(db, solicitante, produto_id):
        acessos.append((solicitante, produto_id))
        return "tenant-catalogo", None

    monkeypatch.setattr(routes, "_resolver_tenant_produto_catalogo", resolver)
    monkeypatch.setattr(routes, "ProdutoLote", LoteFake)
    return produto, db, acessos


def informar(db, **kwargs):
    payload = dict(nome_lote="LOTE-X", quantidade=4, data_validade=date(2026, 12, 1))
    payload.update(kwargs)
    return routes.informar_lote_validade(
        10,
        routes.LoteValidadeRequest(**payload),
        db=db,
        user_and_tenant=(SimpleNamespace(id=1), "tenant-loja"),
    )


def test_identifica_estoque_existente_sem_movimentacao_ou_alterar_custo(setup_rota):
    produto, db, acessos = setup_rota
    lote = informar(db)
    assert produto.estoque_atual == 10
    assert produto.preco_custo == 7
    assert lote.quantidade_disponivel == 4
    assert lote.tenant_id == "tenant-catalogo"
    assert lote.data_validade == datetime(2026, 12, 1)
    assert lote.apenas_identificacao is True
    assert lote.custo_unitario is None
    assert produto.controle_lote is False
    assert db.added == [lote]  # Nenhuma movimentação de entrada, saída ou balanço.
    assert acessos == [("tenant-loja", 10)]


def test_reenviar_mesmo_lote_e_quantidade_nao_duplica_registro_ou_saldo(setup_rota):
    produto, db, _ = setup_rota
    lote = informar(db)
    repetido = informar(db)
    assert repetido is lote
    assert len(db.lotes) == 1
    assert lote.quantidade_inicial == 4
    assert lote.quantidade_disponivel == 4
    assert produto.estoque_atual == 10


def test_corrigir_quantidade_preserva_consumo_anterior_e_saldo(setup_rota):
    produto, db, _ = setup_rota
    lote = informar(db)
    lote.quantidade_disponivel = 2  # Duas unidades já consumidas pela venda.
    informar(db, lote_id=lote.id, quantidade=3)
    assert lote.quantidade_inicial == 5
    assert lote.quantidade_disponivel == 3
    assert produto.estoque_atual == 10
    informar(db, lote_id=lote.id, quantidade=0)
    assert lote.quantidade_inicial == 2
    assert lote.status == "esgotado"
    assert produto.estoque_atual == 10


def test_soma_identificada_nao_pode_exceder_estoque(setup_rota):
    produto, db, _ = setup_rota
    informar(db, quantidade=7)
    with pytest.raises(HTTPException) as erro:
        informar(db, nome_lote="OUTRO", quantidade=4)
    assert erro.value.status_code == 400
    assert len(db.lotes) == 1
    assert db.commits == 1
    assert produto.estoque_atual == 10


def test_permite_corrigir_para_baixo_divergencia_antiga(setup_rota):
    produto, db, _ = setup_rota
    lote = informar(db, quantidade=10)
    produto.estoque_atual = 5
    informar(db, lote_id=lote.id, quantidade=8)
    assert produto.estoque_atual == 5
    assert lote.quantidade_disponivel == 8
    with pytest.raises(HTTPException):
        informar(db, lote_id=lote.id, quantidade=9)


def test_lote_bloqueado_nao_e_liberado_por_correcao(setup_rota):
    _, db, _ = setup_rota
    lote = informar(db)
    lote.status = "bloqueado"
    informar(db, lote_id=lote.id, quantidade=3)
    assert lote.status == "bloqueado"


def test_lote_identificado_vencido_nao_baixa_estoque_na_rotina_automatica(setup_rota):
    produto, db, _ = setup_rota
    lote = informar(db, data_validade=date(2026, 10, 1))
    resultado = EstoqueValidadeService.processar_lotes_em_risco(
        db=db,
        tenant=SimpleNamespace(
            id="tenant-catalogo", protecao_validade_ativa=True, dias_alerta_validade=15
        ),
        user_id=1,
        agora=datetime(2026, 10, 9),
    )
    assert resultado == {"processados": 0, "bloqueios": []}
    assert produto.estoque_atual == 10
    assert lote.quantidade_disponivel == 4
    assert lote.status == "ativo"
    assert db.added == [lote]  # Nenhum bloqueio, movimento de estoque ou despesa.


def test_nao_e_possivel_bloquear_lote_de_identificacao_diretamente(setup_rota):
    produto, db, _ = setup_rota
    lote = informar(db)
    with pytest.raises(ValueError, match="identificação"):
        EstoqueValidadeService.bloquear_lote(
            db=db,
            tenant_id="tenant-catalogo",
            user_id=1,
            produto=produto,
            lote=lote,
        )
    assert produto.estoque_atual == 10
    assert db.added == [lote]


def test_fifo_permite_venda_com_identificacao_parcial_e_usa_custo_atual(
    monkeypatch, setup_rota
):
    produto, db, _ = setup_rota
    lote = informar(db, quantidade=2)
    produto.preco_custo = 15  # A indicação da validade não congela custo de entrada.
    monkeypatch.setattr(
        EstoqueService, "_validar_ou_registrar_estoque_negativo", lambda **kwargs: None
    )
    monkeypatch.setattr(
        EstoqueService, "_ajustar_estoque_canal_online", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        EstoqueService, "_resolver_user_id_operacao", lambda **kwargs: kwargs["user_id"]
    )
    resultado = EstoqueService.baixar_estoque(
        produto_id=10,
        quantidade=5,
        motivo="venda",
        referencia_id=20,
        referencia_tipo="venda",
        user_id=1,
        db=db,
        tenant_id="tenant-catalogo",
        sincronizar=False,
    )
    assert resultado["estoque_novo"] == 5
    assert resultado["custo_unitario"] == 15
    assert resultado["valor_total"] == 75
    assert lote.quantidade_disponivel == 0
    assert resultado["lotes_consumidos"][0]["quantidade"] == 2


def test_correcao_de_lote_de_entrada_preserva_origem_e_custo(setup_rota):
    _, db, _ = setup_rota
    lote = informar(db)
    lote.apenas_identificacao = False
    lote.custo_unitario = 23
    informar(db, lote_id=lote.id, quantidade=3)
    assert lote.apenas_identificacao is False
    assert lote.custo_unitario == 23


@pytest.mark.parametrize("controle_anterior", [False, True])
def test_informar_lote_preserva_configuracao_anterior_de_controle(
    setup_rota, controle_anterior
):
    produto, db, _ = setup_rota
    produto.controle_lote = controle_anterior
    informar(db)
    assert produto.controle_lote is controle_anterior


def test_identificacao_parcial_nao_limita_fracionamento_consumo_clinico_ou_publicacao(
    monkeypatch, setup_rota
):
    produto, db, _ = setup_rota
    produto.estoque_atual = 30
    produto.ativo = True
    produto.situacao = True
    produto.is_sellable = True
    produto.data_validade = None
    lote = informar(db, quantidade=5, data_validade=date(2030, 10, 9))
    produto.lotes = [lote]
    assert produto.controle_lote is False
    assert produto.estoque_atual == 30
    assert produto_publicavel(produto, datetime(2026, 10, 9)) is True

    # O consumo clínico usa o saldo do produto, sem exigir os 30 em lotes.
    assert (
        _consumir_lotes_insumo(
            db, tenant_id="tenant-catalogo", produto=produto, quantidade=8
        )
        == []
    )
    # O fracionamento pode abrir oito unidades, incluindo três ainda sem identificação.
    consumidos, custo_total = _lotes_origem_para_consumo(
        db,
        tenant_id="tenant-catalogo",
        produto=produto,
        quantidade=8,
        lote_origem_id=None,
    )
    assert consumidos[0]["quantidade"] == 5
    assert custo_total == 8 * produto.preco_custo
    assert produto.controle_lote is False
    # Depois de consumir a identificação, as outras unidades seguem publicáveis.
    assert produto_publicavel(produto, datetime(2026, 10, 9)) is True

    monkeypatch.setattr(
        "app.produtos.lotes_routes._resolver_tenant_produto_catalogo",
        lambda *args: ("tenant-catalogo", None),
    )
    listado = listar_lotes(
        10, db=db, user_and_tenant=(SimpleNamespace(id=1), "tenant-loja")
    )
    assert listado == [lote]  # O modal consegue listar mesmo com controle_lote=false.


def test_nao_permite_reduzir_abaixo_da_reserva(setup_rota):
    _, db, _ = setup_rota
    lote = informar(db)
    lote.quantidade_reservada = 3
    with pytest.raises(HTTPException):
        informar(db, lote_id=lote.id, quantidade=2)
    assert lote.quantidade_disponivel == 4


def test_nao_aceita_lote_de_outro_produto(setup_rota):
    _, db, _ = setup_rota
    with pytest.raises(HTTPException) as erro:
        informar(db, lote_id=999)
    assert erro.value.status_code == 404
    assert not db.added


def test_acesso_ao_catalogo_negado_nao_altera_lotes(monkeypatch, setup_rota):
    produto, db, _ = setup_rota

    def negar_acesso(*args):
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    monkeypatch.setattr(routes, "_resolver_tenant_produto_catalogo", negar_acesso)
    with pytest.raises(HTTPException) as erro:
        informar(db)
    assert erro.value.status_code == 404
    assert not db.added
    assert db.commits == 0
    assert produto.estoque_atual == 10


def test_fabricacao_posterior_a_validade_nao_grava(setup_rota):
    _, db, _ = setup_rota
    with pytest.raises(HTTPException):
        informar(db, data_fabricacao=date(2026, 12, 2))
    assert not db.added


def test_correcao_nao_pode_renomear_para_outro_lote(setup_rota):
    _, db, _ = setup_rota
    lote = informar(db)
    informar(db, nome_lote="OUTRO", quantidade=2)
    with pytest.raises(HTTPException):
        informar(db, lote_id=lote.id, nome_lote="OUTRO")
    assert lote.nome_lote == "LOTE-X"


@pytest.mark.parametrize(
    "atributos",
    [
        dict(controlar_estoque=False),
        dict(is_parent=True),
        dict(tipo_produto="KIT", tipo_kit="VIRTUAL"),
    ],
)
def test_rejeita_cadastros_sem_estoque_proprio(setup_rota, atributos):
    produto, db, _ = setup_rota
    for chave, valor in atributos.items():
        setattr(produto, chave, valor)
    with pytest.raises(HTTPException):
        informar(db)
    assert not db.added


@pytest.mark.parametrize("quantidade", [-1, float("nan"), float("inf")])
def test_schema_rejeita_quantidades_invalidas(quantidade):
    with pytest.raises(ValidationError):
        routes.LoteValidadeRequest(
            nome_lote="X", quantidade=quantidade, data_validade="2026-12-01"
        )


def test_endpoint_serializa_lote_e_datas(setup_rota):
    produto, db, _ = setup_rota
    app = FastAPI()
    app.include_router(routes.router, prefix="/produtos")
    app.dependency_overrides[routes.get_session] = lambda: db
    app.dependency_overrides[routes.get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1),
        "tenant-loja",
    )
    response = TestClient(app).put(
        "/produtos/10/lotes-validade",
        json={
            "nome_lote": "X",
            "quantidade": 5,
            "data_validade": "2026-12-01",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["quantidade_disponivel"] == 5
    assert response.json()["data_validade"] == "2026-12-01T00:00:00"
    assert produto.estoque_atual == 10
