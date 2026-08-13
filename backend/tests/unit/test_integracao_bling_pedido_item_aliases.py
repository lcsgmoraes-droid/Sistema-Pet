from types import SimpleNamespace

from app.integracao_bling_pedido_routes import _sincronizar_itens_pedido_integrado


class _ConsultaItens:
    def __init__(self, itens):
        self.itens = itens

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.itens


class _DbItens:
    def __init__(self, itens):
        self.itens = itens
        self.adicionados = []

    def query(self, model):
        return _ConsultaItens(self.itens)

    def add(self, item):
        self.adicionados.append(item)


def test_sincronizar_itens_nao_duplica_reserva_quando_sku_e_alias_do_mesmo_produto(
    monkeypatch,
):
    pedido = SimpleNamespace(
        id=7391,
        tenant_id="tenant-1",
        status="aberto",
    )
    item_existente = SimpleNamespace(
        sku="PET5136",
        quantidade=1,
    )
    produto = SimpleNamespace(id=4467)
    db = _DbItens([item_existente])

    monkeypatch.setattr(
        "app.services.produto_sku_service.buscar_produto_por_sku",
        lambda db, tenant_id, sku: (
            produto if str(sku).casefold() in {"pet5136", "5136"} else None
        ),
    )

    criados = _sincronizar_itens_pedido_integrado(
        db,
        pedido=pedido,
        itens_bling=[
            {
                "codigo": "5136",
                "descricao": "Areia Pipicat Classic 20kg",
                "quantidade": 1,
            }
        ],
    )

    assert criados == 0
    assert db.adicionados == []
