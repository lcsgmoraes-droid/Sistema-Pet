from pathlib import Path

from app.routes.ecommerce_cart import (
    STATUS_RESERVA_ATIVA,
    _quantidade_reservada_produto,
)


ROOT = Path(__file__).resolve().parents[3]


def test_carrinho_e_pendente_nao_reservam_estoque():
    assert STATUS_RESERVA_ATIVA == ()


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
    source = (ROOT / "frontend/src/pages/ecommerce/useEcommerceCart.js").read_text(encoding="utf-8")

    assert "const produtoId = itemAtual?.produto_id" in source
    assert "'/api/carrinho/atualizar'" in source
    assert "{ produto_id: produtoId, quantidade }" in source
    assert "`/api/carrinho/atualizar/${itemId}`" not in source
    assert "`/api/carrinho/remover/${itemId}`" not in source
