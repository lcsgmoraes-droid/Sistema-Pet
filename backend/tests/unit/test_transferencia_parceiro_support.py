from datetime import date, datetime, timezone
from types import SimpleNamespace

import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque.transferencia_parceiro_support import (
    _detectar_modo_baixa_transferencia,
    _listar_baixas_transferencia,
    _origem_conta_pagar_compensacao,
)


def test_origem_conta_pagar_compensacao_identifica_entradas_e_acertos():
    assert _origem_conta_pagar_compensacao(
        SimpleNamespace(canal="transferencia_parceiro_entrada")
    ) == ("entrada_parceiro", "Entrada do parceiro")
    assert _origem_conta_pagar_compensacao(
        SimpleNamespace(canal="transferencia_parceiro")
    ) == ("acerto_direto", "Acerto direto")
    assert _origem_conta_pagar_compensacao(SimpleNamespace(canal="compras")) == (
        "financeiro",
        "Financeiro",
    )


def test_detectar_modo_baixa_identifica_produto_devolvido_sem_recebimento():
    assert _detectar_modo_baixa_transferencia(
        None,
        observacoes_conta="Produto devolvido 01/07/2026: R$ 100.00",
    ) == ("produto_devolvido", "Produto devolvido")


def test_listar_baixas_retorna_todos_recebimentos_em_ordem_com_horario_utc():
    conta = SimpleNamespace(
        observacoes="",
        recebimentos=[
            SimpleNamespace(
                id=1,
                valor_recebido=20,
                data_recebimento=date(2026, 7, 10),
                created_at=datetime(2026, 7, 10, 15, 0),
                forma_pagamento_id=3,
                forma_pagamento=SimpleNamespace(nome="Pix"),
                observacoes="Recebimento normal",
            ),
            SimpleNamespace(
                id=2,
                valor_recebido=30,
                data_recebimento=date(2026, 7, 20),
                created_at=datetime(2026, 7, 20, 18, 30),
                forma_pagamento_id=4,
                forma_pagamento=SimpleNamespace(nome="Dinheiro"),
                observacoes="Recebimento normal",
            ),
        ],
    )

    baixas = _listar_baixas_transferencia(conta)

    assert [item.recebimento_id for item in baixas] == [2, 1]
    assert [item.valor_recebido for item in baixas] == [30.0, 20.0]
    assert baixas[0].forma_pagamento_nome == "Dinheiro"
    assert baixas[0].registrado_em.tzinfo == timezone.utc
