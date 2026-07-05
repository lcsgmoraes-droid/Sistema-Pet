from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_contas_bancarias_operam_saldos_e_movimentacoes_em_reais():
    source = _source("app/contas_bancarias_routes.py")

    assert "conta.saldo_inicial = float(conta.saldo_inicial) / 100" not in source
    assert "conta.saldo_atual = float(conta.saldo_atual) / 100" not in source
    assert "mov.valor = float(mov.valor) / 100" not in source
    assert "saldo_reais = float(conta.saldo_atual) / 100" not in source
    assert "novo_saldo_centavos" not in source
    assert "ajuste.novo_saldo * 100" not in source


def test_contas_bancarias_filtram_movimentacoes_por_tenant_e_registram_usuario():
    source = _source("app/contas_bancarias_routes.py")
    listar_movimentacoes = source.split(
        "def listar_movimentacoes(",
        1,
    )[1].split('@router.get("/resumo/saldos")', 1)[0]
    ajustar_saldo = source.split("def ajustar_saldo(", 1)[1].split(
        '@router.get("/{conta_id}/movimentacoes"',
        1,
    )[0]
    criar_conta = source.split("def criar_conta(", 1)[1].split(
        '@router.put("/{conta_id}"',
        1,
    )[0]

    assert "MovimentacaoFinanceira.tenant_id == tenant_id" in listar_movimentacoes
    assert "user_id=user_id" in criar_conta
    assert "user_id=current_user.id" in ajustar_saldo
    assert "tenant_id=tenant_id" in ajustar_saldo


def test_pagamento_comissao_filtra_conta_bancaria_por_tenant_e_usa_reais():
    source = _source("app/comissoes_avancadas/pagamento_routes.py")
    registrar = source.split("async def fechar_com_pagamento_parcial(", 1)[1]

    assert "ContaBancaria.tenant_id == tenant_id" in registrar
    assert "valor_centavos" not in registrar
    assert "valor_liquido_decimal = Decimal(str(valor_liquido))" in registrar
    assert "valor=valor_liquido_decimal" in registrar
    assert "conta_bancaria.saldo_atual -= valor_liquido_decimal" in registrar
    assert "tenant_id=tenant_id" in registrar
