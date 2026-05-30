from app.routes.ecommerce_entregador import rota_entregador_permite_reordenar


def test_rota_entregador_permite_reordenar_rotas_ativas():
    assert rota_entregador_permite_reordenar("pendente")
    assert rota_entregador_permite_reordenar("em_rota")
    assert rota_entregador_permite_reordenar("em_andamento")


def test_rota_entregador_nao_permite_reordenar_rotas_encerradas():
    assert not rota_entregador_permite_reordenar("concluida")
    assert not rota_entregador_permite_reordenar("cancelada")
