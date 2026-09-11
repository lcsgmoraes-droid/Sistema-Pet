from decimal import Decimal

from app.routes.ecommerce_entregador import rota_entregador_permite_reordenar
from app.schemas.rota_entrega import PagamentoEntregaResponse


def test_rota_entregador_permite_reordenar_rotas_ativas():
    assert rota_entregador_permite_reordenar("pendente")
    assert rota_entregador_permite_reordenar("em_rota")
    assert rota_entregador_permite_reordenar("em_andamento")


def test_rota_entregador_nao_permite_reordenar_rotas_encerradas():
    assert not rota_entregador_permite_reordenar("concluida")
    assert not rota_entregador_permite_reordenar("cancelada")


def test_pagamento_da_rota_expoe_instrucao_de_troco_ao_app():
    pagamento = PagamentoEntregaResponse.model_validate(
        {
            "forma_pagamento": "Dinheiro",
            "valor": Decimal("45.00"),
            "valor_recebido": Decimal("50.00"),
            "troco": Decimal("5.00"),
            "numero_parcelas": 1,
        }
    )

    assert pagamento.forma_pagamento == "Dinheiro"
    assert pagamento.valor_recebido == Decimal("50.00")
    assert pagamento.troco == Decimal("5.00")
