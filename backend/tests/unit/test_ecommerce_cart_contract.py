import inspect
from pathlib import Path

from app.routes.ecommerce_cart import (
    EcommerceIdentity,
    STATUS_RESERVA_ATIVA,
    _quantidade_reservada_produto,
    _restore_latest_expired_cart,
)
from app.routes.ecommerce_checkout_support import _expirar_reservas_automaticamente


ROOT = Path(__file__).resolve().parents[3]


def test_carrinho_e_pendente_nao_reservam_estoque():
    assert STATUS_RESERVA_ATIVA == ()


def test_carrinho_nao_expira_automaticamente_quando_cliente_fecha_o_app():
    function_source = inspect.getsource(_expirar_reservas_automaticamente)

    assert 'Pedido.status == "carrinho"' not in function_source
    assert 'Pedido.status == "pendente"' in function_source


def test_ultimo_carrinho_expirado_e_restaurado_para_o_mesmo_cliente():
    expired_cart = type("ExpiredCart", (), {"status": "expirado"})()

    class QueryStub:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def first(self):
            return expired_cart

    class DbStub:
        committed = False

        def query(self, *_args, **_kwargs):
            return QueryStub()

        def commit(self):
            self.committed = True

    db = DbStub()
    identity = EcommerceIdentity(
        user_id=42, tenant_id="00000000-0000-0000-0000-000000000042"
    )

    restored_cart = _restore_latest_expired_cart(db, identity, identity.tenant_id)

    assert restored_cart is expired_cart
    assert restored_cart.status == "carrinho"
    assert db.committed is True


def test_quantidade_reservada_sem_status_ativo_retorna_zero_sem_consultar_db():
    class DbQueFalhaSeConsultar:
        def query(self, *_args, **_kwargs):
            raise AssertionError("Carrinho nao deve consultar reservas de estoque")

    assert (
        _quantidade_reservada_produto(
            DbQueFalhaSeConsultar(),
            tenant_id="tenant-1",
            produto_id=123,
        )
        == 0.0
    )


def test_frontend_carrinho_atualiza_servidor_por_produto_id_e_nao_item_id():
    source = (ROOT / "frontend/src/pages/ecommerce/useEcommerceCart.js").read_text(
        encoding="utf-8"
    )

    assert "const produtoId = itemAtual?.produto_id" in source
    assert (
        "'/api/carrinho/atualizar'" in source or '"/api/carrinho/atualizar"' in source
    )
    assert "{ produto_id: produtoId, quantidade }" in source
    assert "`/api/carrinho/atualizar/${itemId}`" not in source
    assert "`/api/carrinho/remover/${itemId}`" not in source
