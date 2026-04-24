from app.routes.ecommerce_cart import (
    STATUS_RESERVA_ATIVA,
    _quantidade_reservada_produto,
)


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
