from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.vendas.service import _calcular_pagamentos_finalizacao


def test_calcular_pagamentos_finalizacao_permite_venda_ja_quitada_sem_novo_pagamento():
    existente = SimpleNamespace(valor=Decimal("90.00"))

    resultado = _calcular_pagamentos_finalizacao(
        total_venda=Decimal("90.00"),
        pagamentos_existentes=[existente],
        pagamentos_novos=[],
    )

    assert resultado["total_ja_pago"] == 90.0
    assert resultado["total_novos_pagamentos"] == 0.0
    assert resultado["total_pagamentos"] == 90.0
    assert resultado["valor_restante"] == 0.0


def test_calcular_pagamentos_finalizacao_exige_pagamento_quando_venda_nao_esta_quitada():
    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("90.00"),
            pagamentos_existentes=[],
            pagamentos_novos=[],
        )

    assert exc.value.status_code == 400
    assert "Informe pelo menos uma forma de pagamento" in exc.value.detail


def test_calcular_pagamentos_finalizacao_rejeita_novo_pagamento_em_venda_ja_quitada():
    existente = SimpleNamespace(valor=Decimal("90.00"))

    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("90.00"),
            pagamentos_existentes=[existente],
            pagamentos_novos=[{"forma_pagamento": "PIX", "valor": 10.0}],
        )

    assert exc.value.status_code == 400
    assert "totalmente paga" in exc.value.detail


@pytest.mark.parametrize("total_editado", [Decimal("20.00"), Decimal("0.00")])
def test_reducao_preserva_pagamentos_anteriores_e_permite_refinalizar(total_editado):
    resultado = _calcular_pagamentos_finalizacao(
        total_venda=total_editado,
        pagamentos_existentes=[SimpleNamespace(valor=Decimal("60.00"))],
        pagamentos_novos=[],
    )
    assert resultado == {
        "total_ja_pago": 60.0,
        "total_novos_pagamentos": 0.0,
        "total_pagamentos": 60.0,
        "valor_restante": 0.0,
    }


def test_reducao_nao_autoriza_receber_novo_pagamento():
    with pytest.raises(HTTPException) as exc:
        _calcular_pagamentos_finalizacao(
            total_venda=Decimal("20.00"),
            pagamentos_existentes=[SimpleNamespace(valor=Decimal("60.00"))],
            pagamentos_novos=[{"forma_pagamento": "PIX", "valor": 1}],
        )
    assert exc.value.status_code == 400
    assert "totalmente paga" in exc.value.detail
