"""
Testes unitários da regra de custo automático para produtos compostos.
"""
from decimal import Decimal
from types import SimpleNamespace

from app.produtos_models import Produto, ProdutoKitComponente
from app.services.kit_custo_service import KitCustoService
from app.services.produto_service import ProdutoService


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.db.consume(self.model, 'first')

    def all(self):
        return self.db.consume(self.model, 'all')


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
            return [] if method == 'all' else None
        return fila.pop(0)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_count += 1
        for obj in self.added:
            if getattr(obj, 'id', None) is None:
                obj.id = self._next_id
                self._next_id += 1

    def commit(self):
        self.commit_count += 1

    def refresh(self, obj):
        return obj

    def rollback(self):
        self.rollback_count += 1


def test_calcular_custo_variacao_kit_por_componentes():
    kit = SimpleNamespace(id=10, nome='Kit', tipo_produto='VARIACAO', tipo_kit='VIRTUAL', preco_custo=999)
    comp_a = SimpleNamespace(id=1, nome='Comp A', tipo_produto='SIMPLES', preco_custo=10)
    comp_b = SimpleNamespace(id=2, nome='Comp B', tipo_produto='VARIACAO', preco_custo=5)
    componentes = [
        SimpleNamespace(produto_componente_id=1, quantidade=2),
        SimpleNamespace(produto_componente_id=2, quantidade=3),
    ]

    db = FakeDB(
        responses={
            (Produto, 'first'): [kit, comp_a, comp_b],
            (ProdutoKitComponente, 'all'): [componentes],
        }
    )

    custo = KitCustoService.calcular_custo_kit(10, db)

    assert custo == Decimal('35')


def test_produto_service_cria_kit_e_sincroniza_custo(monkeypatch):
    db = FakeDB()
    chamadas = []

    monkeypatch.setattr(
        'app.services.kit_estoque_service.KitEstoqueService.validar_componentes_kit',
        lambda db, kit_id, componentes: (True, None),
    )
    monkeypatch.setattr(
        'app.services.kit_custo_service.KitCustoService.sincronizar_custo_kit',
        lambda db, kit_id: chamadas.append(kit_id) or 35,
    )

    produto = ProdutoService.create_produto(
        dados={
            'codigo': 'KIT-001',
            'nome': 'Kit Manual',
            'tipo_produto': 'KIT',
            'tipo_kit': 'VIRTUAL',
            'preco_custo': 999,
            'preco_venda': 50,
            'user_id': 1,
            'composicao_kit': [
                {'produto_componente_id': 1, 'quantidade': 2},
                {'produto_componente_id': 2, 'quantidade': 3},
            ],
        },
        db=db,
        tenant_id='tenant-teste',
    )

    assert produto.id == 1
    assert chamadas == [1]
    assert db.commit_count == 1


def test_recalcular_kits_que_usam_produto_atualiza_dependentes(monkeypatch):
    kit = SimpleNamespace(id=20, nome='Kit Dependente', tipo_produto='KIT', tipo_kit='VIRTUAL', preco_custo=0)
    componente_relacao = SimpleNamespace(kit_id=20, produto_componente_id=5)
    db = FakeDB(
        responses={
            (ProdutoKitComponente, 'all'): [[componente_relacao]],
            (Produto, 'first'): [kit],
        }
    )

    monkeypatch.setattr(
        'app.services.kit_custo_service.KitCustoService.sincronizar_custo_kit',
        lambda db, kit_id: 14,
    )

    resultado = KitCustoService.recalcular_kits_que_usam_produto(db, 5)

    assert resultado == {20: 14}