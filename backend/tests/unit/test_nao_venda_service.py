from decimal import Decimal
from types import SimpleNamespace

from app.models import Cliente
from app.nao_venda_models import NaoVenda, NaoVendaItem
from app.nao_venda_schemas import NaoVendaCreate, NaoVendaItemCreate
from app.pendencia_estoque_models import PendenciaEstoque
from app.produtos_models import Produto
from app.services.nao_venda_service import registrar_nao_venda
from app.vendas_models import Venda  # noqa: F401 - registra relações do SQLAlchemy


class _Query:
    def __init__(self, *, first=None, all_items=None):
        self._first = first
        self._all = all_items or []

    def options(self, *_args):
        return self

    def filter(self, *_args):
        return self

    def first(self):
        return self._first

    def all(self):
        return self._all


class _FakeSession:
    def __init__(self, *, cliente=None, produtos=None, pendencia=None):
        self.cliente = cliente
        self.produtos = produtos or []
        self.pendencia = pendencia
        self.adicionados = []
        self.commits = 0
        self._proximo_id = 1000

    def query(self, modelo):
        if modelo is Cliente:
            return _Query(first=self.cliente)
        if modelo is Produto:
            return _Query(all_items=self.produtos)
        if modelo is PendenciaEstoque:
            return _Query(first=self.pendencia)
        return _Query()

    def add(self, objeto):
        if getattr(objeto, "id", None) is None:
            objeto.id = self._proximo_id
            self._proximo_id += 1
        self.adicionados.append(objeto)

    def flush(self):
        return None

    def commit(self):
        self.commits += 1

    def refresh(self, _objeto):
        return None


def test_registrar_nao_venda_livre_preserva_snapshots_e_valor_estimado():
    db = _FakeSession()
    dados = NaoVendaCreate(
        cliente_nome="Maria",
        cliente_telefone="11999990000",
        motivo="produto_nao_trabalhado",
        itens=[
            NaoVendaItemCreate(
                produto_nome="Ração de pato 15 kg",
                marca_nome="Marca nova",
                fornecedor_nome="Distribuidora sugerida",
                quantidade=Decimal("2"),
                valor_unitario_estimado=Decimal("125.50"),
            )
        ],
    )

    registro, adicionados, ignorados = registrar_nao_venda(
        db,
        tenant_id="00000000-0000-0000-0000-000000000001",
        usuario_id=7,
        dados=dados,
    )

    item = next(objeto for objeto in db.adicionados if isinstance(objeto, NaoVendaItem))
    assert isinstance(registro, NaoVenda)
    assert registro.cliente_nome == "Maria"
    assert registro.valor_estimado_total == Decimal("251.00")
    assert item.produto_id is None
    assert item.produto_nome == "Ração de pato 15 kg"
    assert item.marca_nome == "Marca nova"
    assert item.fornecedor_nome == "Distribuidora sugerida"
    assert adicionados == 0
    assert ignorados == 0
    assert db.commits == 1


def test_registrar_produto_cadastrado_pode_atualizar_lista_espera_existente():
    cliente = SimpleNamespace(
        id=20,
        nome="João",
        celular="11988887777",
        telefone=None,
    )
    produto = SimpleNamespace(
        id=30,
        nome="Special Dog Carne",
        codigo="SD-CARNE",
        marca=SimpleNamespace(id=40, nome="Special Dog"),
        fornecedor=SimpleNamespace(
            id=50,
            nome="Distribuidora Pet",
            nome_fantasia=None,
            razao_social=None,
        ),
        preco_venda=Decimal("99.90"),
        controlar_estoque=True,
    )
    pendencia = SimpleNamespace(quantidade_desejada=1.0)
    db = _FakeSession(cliente=cliente, produtos=[produto], pendencia=pendencia)
    dados = NaoVendaCreate(
        cliente_id=20,
        motivo="produto_sem_estoque",
        adicionar_lista_espera=True,
        itens=[NaoVendaItemCreate(produto_id=30, quantidade=Decimal("2"))],
    )

    registro, adicionados, ignorados = registrar_nao_venda(
        db,
        tenant_id="00000000-0000-0000-0000-000000000001",
        usuario_id=7,
        dados=dados,
    )

    item = next(objeto for objeto in db.adicionados if isinstance(objeto, NaoVendaItem))
    assert registro.cliente_nome == "João"
    assert registro.valor_estimado_total == Decimal("199.80")
    assert item.produto_nome == "Special Dog Carne"
    assert item.sku == "SD-CARNE"
    assert item.marca_nome == "Special Dog"
    assert item.fornecedor_nome == "Distribuidora Pet"
    assert item.adicionado_lista_espera is True
    assert pendencia.quantidade_desejada == 3.0
    assert adicionados == 1
    assert ignorados == 0
    assert db.commits == 1
