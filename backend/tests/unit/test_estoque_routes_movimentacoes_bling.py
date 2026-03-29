from types import SimpleNamespace

from app.estoque_routes import (
    _canal_pedido_integrado,
    _contexto_venda_pedido_integrado,
    _label_canal_movimentacao,
    _observacao_exibicao_movimentacao_bling,
)


def test_label_canal_movimentacao_traduz_shopee():
    assert _label_canal_movimentacao("shopee") == "Shopee"


def test_observacao_exibicao_movimentacao_bling_prioriza_canal_e_nf():
    assert (
        _observacao_exibicao_movimentacao_bling(
            canal="shopee",
            nf_numero="010983",
            observacao_original="Baixa automatica via NF Bling #25428517969",
        )
        == "Venda Shopee NF 010983"
    )


def test_observacao_exibicao_movimentacao_bling_faz_fallback_para_nf():
    assert (
        _observacao_exibicao_movimentacao_bling(
            canal=None,
            nf_numero="010983",
            observacao_original=None,
        )
        == "Venda NF 010983"
    )


def test_canal_pedido_integrado_recalcula_shopee_pelo_payload():
    class Pedido:
        canal = "bling"
        payload = {
            "pedido": {
                "loja": {"id": 205367939},
                "numeroPedidoLoja": "260329D3XB4GMW",
            }
        }

    assert _canal_pedido_integrado(Pedido()) == "shopee"


def test_contexto_venda_pedido_integrado_prioriza_total_da_nf_quando_ha_um_item(monkeypatch):
    class FakeQuery:
        def __init__(self, produto):
            self.produto = produto

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.produto

    class FakeDB:
        def __init__(self, produto):
            self.produto = produto

        def query(self, model):
            return FakeQuery(self.produto)

    produto = SimpleNamespace(id=6396, tenant_id="tenant-1", codigo="013264.1/1", codigo_barras=None)
    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        canal="bling",
        payload={
            "pedido": {
                "loja": {"id": 205367939},
                "numeroPedidoLoja": "260329D3XB4GMW",
                "itens": [
                    {
                        "codigo": "013264.1/1",
                        "descricao": "MGZ MIX COLEIROS 350GR",
                        "quantidade": 1,
                        "valor": 89.90,
                        "total": 89.90,
                    }
                ],
            },
            "ultima_nf": {
                "numero": "010983",
                "valor_total": 42.90,
            },
        },
    )

    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda db, produto: [6396],
    )

    contexto = _contexto_venda_pedido_integrado(FakeDB(produto), pedido, 6396)

    assert contexto["canal"] == "shopee"
    assert contexto["nf_numero"] == "010983"
    assert contexto["preco_venda_unitario"] == 42.90


def test_contexto_venda_pedido_integrado_ler_total_da_nota_embutida_no_payload(monkeypatch):
    class FakeQuery:
        def __init__(self, produto):
            self.produto = produto

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.produto

    class FakeDB:
        def __init__(self, produto):
            self.produto = produto

        def query(self, model):
            return FakeQuery(self.produto)

    produto = SimpleNamespace(id=6762, tenant_id="tenant-1", codigo="018366.1", codigo_barras=None)
    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        canal="bling",
        payload={
            "pedido": {
                "loja": {"id": 204647675},
                "itens": [
                    {
                        "codigo": "018366.1",
                        "descricao": "ND PUMPKIN FELINE ADULT TILAPIA 1,5KG",
                        "quantidade": 1,
                        "valor": 399.0,
                        "total": 399.0,
                    }
                ],
                "notaFiscal": {
                    "id": "25428517969",
                    "numero": "010984",
                    "valorTotalNf": 166.90,
                },
            },
            "ultima_nf": {
                "id": "25428517969",
                "numero": "010984",
            },
        },
    )

    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda db, produto: [6762],
    )

    contexto = _contexto_venda_pedido_integrado(FakeDB(produto), pedido, 6762)

    assert contexto["canal"] == "mercado_livre"
    assert contexto["nf_numero"] == "010984"
    assert contexto["preco_venda_unitario"] == 166.90


def test_contexto_venda_pedido_integrado_prioriza_item_da_nf_em_cache(monkeypatch):
    class FakeQuery:
        def __init__(self, produto):
            self.produto = produto

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.produto

    class FakeDB:
        def __init__(self, produto):
            self.produto = produto

        def query(self, model):
            return FakeQuery(self.produto)

    produto = SimpleNamespace(id=6762, tenant_id="tenant-1", codigo="018366.1", codigo_barras=None)
    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        canal="bling",
        payload={
            "pedido": {
                "loja": {"id": 204647675},
                "total": 399.0,
                "itens": [
                    {
                        "codigo": "018366.1",
                        "descricao": "ND PUMPKIN FELINE ADULT TILAPIA 1,5KG",
                        "quantidade": 1,
                        "valor": 399.0,
                        "total": 399.0,
                    }
                ],
            },
            "ultima_nf": {
                "id": "25428517969",
                "numero": "010984",
            },
        },
    )

    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda db, produto: [6762],
    )
    monkeypatch.setattr(
        "app.nfe_routes._obter_detalhe_nfe_cache",
        lambda tenant_id, nfe_id, modelo=None: {
            "id": "25428517969",
            "itens": [
                {
                    "codigo": "018366.1",
                    "quantidade": 1,
                    "valor": 166.90,
                    "total": 166.90,
                }
            ],
        },
    )

    contexto = _contexto_venda_pedido_integrado(FakeDB(produto), pedido, 6762)

    assert contexto["canal"] == "mercado_livre"
    assert contexto["nf_numero"] == "010984"
    assert contexto["preco_venda_unitario"] == 166.90


def test_contexto_venda_pedido_integrado_nao_faz_fallback_para_valor_do_pedido(monkeypatch):
    class FakeQuery:
        def __init__(self, produto):
            self.produto = produto

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.produto

    class FakeDB:
        def __init__(self, produto):
            self.produto = produto

        def query(self, model):
            return FakeQuery(self.produto)

    produto = SimpleNamespace(id=6762, tenant_id="tenant-1", codigo="018366.1", codigo_barras=None)
    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        canal="bling",
        payload={
            "pedido": {
                "loja": {"id": 204647675},
                "total": 399.0,
                "itens": [
                    {
                        "codigo": "018366.1",
                        "descricao": "ND PUMPKIN FELINE ADULT TILAPIA 1,5KG",
                        "quantidade": 1,
                        "valor": 399.0,
                        "total": 399.0,
                    }
                ],
            },
            "ultima_nf": {
                "id": "25428517969",
                "numero": "010984",
            },
        },
    )

    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda db, produto: [6762],
    )
    monkeypatch.setattr(
        "app.nfe_routes._obter_detalhe_nfe_cache",
        lambda tenant_id, nfe_id, modelo=None: None,
    )

    contexto = _contexto_venda_pedido_integrado(FakeDB(produto), pedido, 6762)

    assert contexto["canal"] == "mercado_livre"
    assert contexto["nf_numero"] == "010984"
    assert contexto["preco_venda_unitario"] is None


def test_contexto_venda_pedido_integrado_usa_itens_salvos_quando_payload_nao_tem_itens(monkeypatch):
    class FakeQuery:
        def __init__(self, *, produto=None, itens=None):
            self.produto = produto
            self.itens = itens or []

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self.produto

        def all(self):
            return self.itens

    class FakeDB:
        def __init__(self, produto, itens_salvos):
            self.produto = produto
            self.itens_salvos = itens_salvos

        def query(self, model):
            if getattr(model, "__name__", "") == "PedidoIntegradoItem":
                return FakeQuery(itens=self.itens_salvos)
            return FakeQuery(produto=self.produto)

    produto = SimpleNamespace(id=6762, tenant_id="tenant-1", codigo="018366.1", codigo_barras=None)
    itens_salvos = [
        SimpleNamespace(
            id=945,
            sku="018366.1",
            descricao="ND PUMPKIN FELINE ADULT TILAPIA 1,5KG",
            quantidade=1,
        )
    ]
    pedido = SimpleNamespace(
        id=1093,
        tenant_id="tenant-1",
        canal="mercado_livre",
        payload={
            "ultima_nf": {
                "id": "25429854609",
                "numero": "010984",
                "valor_total": "166.9",
            }
        },
    )

    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda db, produto: [6762],
    )

    contexto = _contexto_venda_pedido_integrado(FakeDB(produto, itens_salvos), pedido, 6762)

    assert contexto["canal"] == "mercado_livre"
    assert contexto["nf_numero"] == "010984"
    assert contexto["preco_venda_unitario"] == 166.90
