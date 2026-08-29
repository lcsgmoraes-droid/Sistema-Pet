"""
Testes unitários da regra de custo automático para produtos compostos.
"""

from decimal import Decimal
from types import SimpleNamespace

from app.produtos import cadastro_routes
from app.produtos.schemas import ProdutoUpdate
from app import dre_plano_contas_models  # noqa: F401
from app import financeiro_models  # noqa: F401
from app.ia import aba7_extrato_models  # noqa: F401
from app.produtos_models import Produto, ProdutoKitComponente
from app.services.kit_custo_service import KitCustoService
from app.services.kit_preco_venda_service import KitPrecoVendaService
from app.services.produto_service import ProdutoService


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.db.consume(self.model, "first")

    def all(self):
        return self.db.consume(self.model, "all")


class FakeDB:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.added = []
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self._next_id = 1

    def query(self, model):
        return FakeQuery(self, model)

    def consume(self, model, method):
        key = (model, method)
        fila = self.responses.get(key, [])
        if not fila:
            return [] if method == "all" else None
        return fila.pop(0)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_count += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1

    def commit(self):
        self.commit_count += 1

    def refresh(self, obj):
        return obj

    def rollback(self):
        self.rollback_count += 1


def test_calcular_custo_variacao_kit_por_componentes():
    kit = SimpleNamespace(
        id=10, nome="Kit", tipo_produto="VARIACAO", tipo_kit="VIRTUAL", preco_custo=999
    )
    comp_a = SimpleNamespace(
        id=1, nome="Comp A", tipo_produto="SIMPLES", preco_custo=10
    )
    comp_b = SimpleNamespace(
        id=2, nome="Comp B", tipo_produto="VARIACAO", preco_custo=5
    )
    componentes = [
        SimpleNamespace(produto_componente_id=1, quantidade=2),
        SimpleNamespace(produto_componente_id=2, quantidade=3),
    ]

    db = FakeDB(
        responses={
            (Produto, "first"): [kit, comp_a, comp_b],
            (ProdutoKitComponente, "all"): [componentes],
        }
    )

    custo = KitCustoService.calcular_custo_kit(10, db)

    assert custo == Decimal("35")


def test_produto_service_cria_kit_e_sincroniza_custo(monkeypatch):
    db = FakeDB()
    chamadas = []

    monkeypatch.setattr(
        "app.services.kit_estoque_service.KitEstoqueService.validar_componentes_kit",
        lambda db, kit_id, componentes: (True, None),
    )
    monkeypatch.setattr(
        "app.services.kit_custo_service.KitCustoService.sincronizar_custo_kit",
        lambda db, kit_id: chamadas.append(kit_id) or 35,
    )

    produto = ProdutoService.create_produto(
        dados={
            "codigo": "KIT-001",
            "nome": "Kit Manual",
            "tipo_produto": "KIT",
            "tipo_kit": "VIRTUAL",
            "preco_custo": 999,
            "preco_venda": 50,
            "user_id": 1,
            "composicao_kit": [
                {"produto_componente_id": 1, "quantidade": 2},
                {"produto_componente_id": 2, "quantidade": 3},
            ],
        },
        db=db,
        tenant_id="tenant-teste",
    )

    assert produto.id == 1
    assert chamadas == [1]
    assert db.commit_count == 1


def test_produto_service_nao_transforma_variacao_comum_em_variacao_kit():
    db = FakeDB()

    produto = ProdutoService.create_produto(
        dados={
            "codigo": "VAR-001",
            "nome": "Variacao simples",
            "tipo_produto": "VARIACAO",
            "produto_pai_id": 10,
            "preco_custo": 5,
            "preco_venda": 20,
            "user_id": 1,
            "e_kit_fisico": False,
        },
        db=db,
        tenant_id="tenant-teste",
    )

    assert produto.id == 1
    assert produto.tipo_kit is None
    assert db.commit_count == 1


def test_produto_service_permita_criar_variacao_kit_sem_componentes_para_configurar_depois():
    db = FakeDB()

    produto = ProdutoService.create_produto(
        dados={
            "codigo": "VAR-KIT-001",
            "nome": "Variacao kit",
            "tipo_produto": "VARIACAO",
            "produto_pai_id": 10,
            "tipo_kit": "VIRTUAL",
            "e_kit_fisico": False,
            "preco_custo": 5,
            "preco_venda": 20,
            "user_id": 1,
        },
        db=db,
        tenant_id="tenant-teste",
    )

    assert produto.id == 1
    assert produto.tipo_kit == "VIRTUAL"
    assert db.commit_count == 1


def test_recalcular_kits_que_usam_produto_atualiza_dependentes(monkeypatch):
    db = FakeDB()
    chamadas = []

    monkeypatch.setattr(
        "app.services.kit_custo_service.KitCustoService.recalcular_kits_que_usam_produtos",
        lambda db, produto_ids: chamadas.append((db, produto_ids))
        or {20: Decimal("14")},
    )

    resultado = KitCustoService.recalcular_kits_que_usam_produto(db, 5)

    assert resultado == {20: Decimal("14")}
    assert chamadas == [(db, [5])]


def test_sugerir_preco_venda_composto_aplica_impacto_da_quantidade():
    componente = SimpleNamespace(id=5, preco_venda=10)
    caixa = SimpleNamespace(
        id=20,
        codigo="NEXGARD-CX3",
        nome="NexGard caixa 3 unidades",
        ativo=True,
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        preco_venda=30,
    )
    relacao = SimpleNamespace(kit_id=20, produto_componente_id=5, quantidade=3)
    db = FakeDB(
        responses={
            (ProdutoKitComponente, "all"): [[relacao]],
            (Produto, "first"): [caixa],
        }
    )

    sugestoes = KitPrecoVendaService.listar_sugestoes(
        db, componente, novo_preco_venda=11, tenant_id="tenant-teste"
    )

    assert sugestoes == [
        {
            "produto_id": 20,
            "sku": "NEXGARD-CX3",
            "nome": "NexGard caixa 3 unidades",
            "ativo": True,
            "quantidade_componente": 3.0,
            "preco_venda_atual": 30.0,
            "preco_venda_sugerido": 33.0,
        }
    ]
    assert caixa.preco_venda == 30
    assert db.commit_count == 0


def test_aplicar_preco_venda_altera_somente_composto_selecionado():
    componente = SimpleNamespace(id=5, preco_venda=10)
    caixa_selecionada = SimpleNamespace(
        id=20,
        codigo="CX-3",
        nome="Caixa com 3",
        ativo=True,
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        preco_venda=30,
        updated_at=None,
    )
    caixa_desmarcada = SimpleNamespace(
        id=21,
        codigo="CX-5",
        nome="Caixa com 5",
        ativo=True,
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        preco_venda=50,
        updated_at=None,
    )
    relacoes = [
        SimpleNamespace(kit_id=20, produto_componente_id=5, quantidade=3),
        SimpleNamespace(kit_id=21, produto_componente_id=5, quantidade=5),
    ]
    db = FakeDB(
        responses={
            (ProdutoKitComponente, "all"): [relacoes],
            (Produto, "first"): [caixa_selecionada, caixa_desmarcada],
        }
    )

    atualizados = KitPrecoVendaService.aplicar_sugestoes(
        db,
        componente,
        novo_preco_venda=11,
        produtos_compostos_ids=[20],
        tenant_id="tenant-teste",
    )

    assert atualizados == {20: Decimal("33.00")}
    assert caixa_selecionada.preco_venda == 33
    assert caixa_desmarcada.preco_venda == 50
    assert db.commit_count == 0


def test_atualizar_produto_com_preco_custo_usa_servicos_globais_de_kit(monkeypatch):
    produto = SimpleNamespace(
        id=13995,
        tenant_id="tenant-teste",
        codigo="SKU-001",
        codigo_barras=None,
        is_parent=False,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        e_granel=False,
        nome="Racao Teste",
        ativo=True,
        situacao=True,
        anunciar_ecommerce=True,
        anunciar_app=True,
        updated_at=None,
    )
    db = FakeDB(responses={(Produto, "first"): [produto]})

    monkeypatch.setattr(
        "app.services.kit_custo_service.KitCustoService.produto_usa_custo_por_componentes",
        lambda produto: False,
    )
    monkeypatch.setattr(
        "app.services.kit_custo_service.KitCustoService.recalcular_kits_que_usam_produto",
        lambda db, produto_id: {},
    )
    monkeypatch.setattr(
        cadastro_routes, "obter_produto", lambda produto_id, db, user: produto
    )

    resultado = cadastro_routes.atualizar_produto.__wrapped__(
        13995,
        ProdutoUpdate(preco_custo=42.9),
        db=db,
        user_and_tenant=(SimpleNamespace(id=2), "tenant-teste"),
    )

    assert resultado.preco_custo == 42.9
    assert db.commit_count == 1


def test_atualizar_produto_aplica_preco_de_venda_composto_autorizado(monkeypatch):
    produto = SimpleNamespace(
        id=5,
        tenant_id="tenant-teste",
        codigo="NEXGARD-UN",
        codigo_barras=None,
        is_parent=False,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        e_granel=False,
        nome="NexGard unitario",
        preco_venda=10,
        ativo=True,
        situacao=True,
        anunciar_ecommerce=True,
        anunciar_app=True,
        updated_at=None,
    )
    caixa = SimpleNamespace(
        id=20,
        codigo="NEXGARD-CX3",
        nome="NexGard caixa 3 unidades",
        ativo=True,
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        preco_venda=30,
        updated_at=None,
    )
    relacao = SimpleNamespace(kit_id=20, produto_componente_id=5, quantidade=3)
    db = FakeDB(
        responses={
            (Produto, "first"): [produto, caixa],
            (ProdutoKitComponente, "all"): [[relacao]],
        }
    )

    monkeypatch.setattr(
        cadastro_routes, "obter_produto", lambda produto_id, db, user: produto
    )

    resultado = cadastro_routes.atualizar_produto.__wrapped__(
        5,
        ProdutoUpdate(
            preco_venda=11,
            produtos_compostos_preco_venda_ids=[20],
        ),
        db=db,
        user_and_tenant=(SimpleNamespace(id=2), "tenant-teste"),
    )

    assert resultado.preco_venda == 11
    assert caixa.preco_venda == 33
    assert db.commit_count == 1
