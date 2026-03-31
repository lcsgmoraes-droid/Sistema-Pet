from types import SimpleNamespace

from app.estoque_routes import (
    _canal_pedido_integrado,
    _contexto_venda_pedido_integrado,
    _label_canal_movimentacao,
    _observacao_exibicao_movimentacao_bling,
    listar_movimentacoes_produto,
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


def test_contexto_venda_pedido_integrado_resolve_nf_pelo_cache_do_pedido(monkeypatch):
    class FakeQuery:
        def __init__(self, *, produto=None, cache=None):
            self.produto = produto
            self.cache = cache

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self.cache if self.cache is not None else self.produto

    class FakeDB:
        def __init__(self, produto, cache):
            self.produto = produto
            self.cache = cache

        def query(self, model):
            if getattr(model, "__name__", "") == "BlingNotaFiscalCache":
                return FakeQuery(cache=self.cache)
            return FakeQuery(produto=self.produto)

    produto = SimpleNamespace(id=6398, tenant_id="tenant-1", codigo="SKU-TESTE", codigo_barras=None)
    cache = SimpleNamespace(
        bling_id="25441572688",
        numero="011087",
        serie="2",
        status="Autorizada",
        modelo=55,
        detalhada_em=None,
        last_synced_at=None,
        id=1,
    )
    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        pedido_bling_id="25441515111",
        canal="bling",
        payload={
            "pedido": {
                "loja": {"id": 205367939},
                "itens": [
                    {
                        "codigo": "SKU-TESTE",
                        "descricao": "Produto de teste",
                        "quantidade": 1,
                        "valor": 68.93,
                        "total": 68.93,
                    }
                ],
            },
            "ultima_nf": {"id": "0"},
        },
    )

    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda db, produto: [6398],
    )

    contexto = _contexto_venda_pedido_integrado(FakeDB(produto, cache), pedido, 6398)

    assert contexto["canal"] == "shopee"
    assert contexto["nf_numero"] == "011087"


def test_contexto_venda_pedido_integrado_ignora_nf_cache_de_outro_pedido():
    class FakeQuery:
        def __init__(self, resultados):
            self.resultados = list(resultados)

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self.resultados.pop(0) if self.resultados else None

    class FakeDB:
        def __init__(self, consultas):
            self.consultas = consultas

        def query(self, model):
            nome = getattr(model, "__name__", "")
            if nome == "BlingNotaFiscalCache":
                return FakeQuery(self.consultas)
            raise AssertionError(f"Modelo inesperado: {nome}")

    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        pedido_bling_id="pedido-correto",
        canal="bling",
        payload={
            "pedido": {
                "numeroPedidoLoja": "LOJA-123",
            },
            "ultima_nf": {"id": "nf-errada", "numero": "011044"},
        },
    )
    cache_nf_errada = SimpleNamespace(
        bling_id="nf-errada",
        numero="011044",
        serie="2",
        status="Autorizada",
        modelo=55,
        pedido_bling_id_ref="pedido-de-outro",
        numero_pedido_loja="OUTRA-LOJA",
        detalhada_em=None,
        last_synced_at=None,
        id=1,
    )

    contexto = _contexto_venda_pedido_integrado(
        FakeDB([cache_nf_errada, None, None]),
        pedido,
        6359,
    )

    assert contexto["nf_numero"] is None
    assert contexto["nf_id"] is None
    assert contexto["preco_venda_unitario"] is None


def test_listar_movimentacoes_produto_nao_relabel_movimento_legado_com_nf_atual(monkeypatch):
    class FakeQuery:
        def __init__(self, *, first_result=None, all_result=None):
            self.first_result = first_result
            self.all_result = all_result or []

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return list(self.all_result)

        def first(self):
            return self.first_result

    class FakeDB:
        def __init__(self, produto, movimentacoes, pedidos):
            self.produto = produto
            self.movimentacoes = movimentacoes
            self.pedidos = pedidos

        def query(self, model):
            nome = getattr(model, "__name__", "")
            if nome == "Produto":
                return FakeQuery(first_result=self.produto)
            if nome == "EstoqueMovimentacao":
                return FakeQuery(all_result=self.movimentacoes)
            if nome == "PedidoIntegrado":
                return FakeQuery(all_result=self.pedidos)
            return FakeQuery()

    produto = SimpleNamespace(id=6359, tenant_id="tenant-1")
    movimento = SimpleNamespace(
        id=3015,
        tipo="saida",
        motivo="venda_bling",
        quantidade=1.0,
        quantidade_anterior=4.0,
        quantidade_nova=3.0,
        custo_unitario=22.31,
        valor_total=22.31,
        documento="11733",
        referencia_id=1225,
        referencia_tipo="pedido_integrado",
        observacao="Baixa automatica via webhook Bling (Atendido)",
        lote_id=None,
        lotes_consumidos=None,
        created_at=None,
        user_id=99,
    )
    pedido = SimpleNamespace(
        id=1225,
        tenant_id="tenant-1",
        pedido_bling_id="25441648396",
        pedido_bling_numero="11733",
        canal="bling",
        payload={
            "pedido": {
                "loja": {"id": 205367939},
                "itens": [{"codigo": "SKU-1", "quantidade": 1, "valor": 41.18, "total": 41.18}],
            },
            "ultima_nf": {"id": "25441651448", "numero": "011089", "valor_total": 41.18},
        },
    )

    monkeypatch.setattr(
        "app.services.bling_nf_service.produto_ids_estoque_afetados",
        lambda db, produto: [6359],
    )

    resultado = listar_movimentacoes_produto(
        produto_id=6359,
        db=FakeDB(produto, [movimento], [pedido]),
        user_and_tenant=(SimpleNamespace(id=1), "tenant-1"),
    )

    assert len(resultado) == 1
    assert resultado[0]["documento"] == "11733"
    assert resultado[0]["nf_numero"] is None
    assert resultado[0]["observacao_exibicao"] == "Baixa automatica via webhook Bling (Atendido)"
