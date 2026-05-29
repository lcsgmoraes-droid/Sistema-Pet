from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_contas_pagar_tem_endpoint_delete_seguro_por_tenant():
    source = _source("app/contas_pagar_routes.py")

    assert '@router.delete("/{conta_id}")' in source

    delete_endpoint = source.split('@router.delete("/{conta_id}")', 1)[1].split(
        "def buscar_conta_pagar",
        1,
    )[0]

    assert "ContaPagar.tenant_id == tenant_id" in delete_endpoint
    assert "valor_pago" in delete_endpoint
    assert "status_code=400" in delete_endpoint
    assert "db.delete(conta)" in delete_endpoint


def test_contas_pagar_tem_estorno_de_pagamento_seguro_por_tenant():
    source = _source("app/contas_pagar_routes.py")

    assert '@router.post("/{conta_id}/estornar")' in source

    estorno_endpoint = source.split('@router.post("/{conta_id}/estornar")', 1)[1].split(
        '@router.post("/{conta_id}/cancelar")',
        1,
    )[0]

    assert "ContaPagar.tenant_id == tenant_id" in estorno_endpoint
    assert "MovimentacaoFinanceira.tenant_id == tenant_id" in estorno_endpoint
    assert "MovimentacaoFinanceira.origem_tipo == 'conta_pagar'" in estorno_endpoint
    assert "conta_bancaria.saldo_atual += movimentacao.valor" in estorno_endpoint
    assert "db.delete(pagamento)" in estorno_endpoint
    assert 'conta.valor_pago = Decimal("0.00")' in estorno_endpoint
    assert "conta.data_pagamento = None" in estorno_endpoint
    assert 'conta.status = "pendente"' in estorno_endpoint


def test_contas_pagar_tem_cancelamento_sem_apagar_historico():
    source = _source("app/contas_pagar_routes.py")

    assert '@router.post("/{conta_id}/cancelar")' in source

    cancelar_endpoint = source.split('@router.post("/{conta_id}/cancelar")', 1)[1].split(
        '@router.get("/{conta_id}")',
        1,
    )[0]

    assert "ContaPagar.tenant_id == tenant_id" in cancelar_endpoint
    assert "valor_pago > 0 or conta.pagamentos" in cancelar_endpoint
    assert "Estorne o pagamento antes de cancelar" in cancelar_endpoint
    assert 'conta.status = "cancelado"' in cancelar_endpoint
    assert "db.delete(conta)" not in cancelar_endpoint
