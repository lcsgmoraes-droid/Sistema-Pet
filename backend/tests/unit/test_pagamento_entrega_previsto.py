from fastapi import HTTPException
import pytest

from app.vendas.pagamento_entrega_previsto import (
    normalizar_pagamento_entrega_previsto,
    validar_valor_para_troco,
)


def test_plano_de_pix_nao_e_pagamento_recebido():
    assert normalizar_pagamento_entrega_previsto(
        {"forma": "pix"}, tem_entrega=True
    ) == {"forma": "pix"}
    assert normalizar_pagamento_entrega_previsto(
        {"forma": "pix"}, tem_entrega=False
    ) is None


def test_valor_de_troco_precisa_cobrir_a_venda():
    plano = normalizar_pagamento_entrega_previsto(
        {"forma": "dinheiro", "valor_para_troco": 100}, tem_entrega=True
    )
    validar_valor_para_troco(plano, saldo=90)
    with pytest.raises(HTTPException):
        validar_valor_para_troco(plano, saldo=110)
