from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_contas_pagar_tem_endpoint_de_edicao_geral():
    source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_manutencao_routes.py"
    ).read_text(encoding="utf-8")
    schemas_source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_schemas.py"
    ).read_text(encoding="utf-8")
    update_schema = schemas_source.split("class ContaPagarUpdate", 1)[1].split(
        "class ContaPagarRecorrenciaBulkDelete", 1
    )[0]

    assert '@router.patch("/{conta_id}")' in source
    assert "def atualizar_conta_pagar(" in source
    assert "fornecedor_id: Optional[int]" in update_schema
    assert "data_emissao: Optional[date]" in update_schema
    assert "documento: Optional[str]" in update_schema
    assert (
        "conta.valor_final = valor_original + valor_juros + valor_multa - valor_desconto"
        in source
    )


def test_busca_conta_pagar_respeita_tenant_na_consulta():
    source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_manutencao_routes.py"
    ).read_text(encoding="utf-8")
    buscar_conta = source.split("def buscar_conta_pagar(", 1)[1].split(
        "# ============================================================================\n# REGISTRAR PAGAMENTO",
        1,
    )[0]

    assert "ContaPagar.tenant_id == tenant_id" in buscar_conta
    assert "Cliente.tenant_id == tenant_id" in buscar_conta


def test_registrar_pagamento_normaliza_valores_antigos_e_respeita_tenant():
    source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_pagamento_routes.py"
    ).read_text(encoding="utf-8")
    registrar_pagamento = source.split("async def registrar_pagamento(", 1)[1].split(
        "# ============================================================================\n# DASHBOARD / RESUMO",
        1,
    )[0]

    assert "_decimal_monetario" in source
    assert "ContaPagar.tenant_id == tenant_id" in registrar_pagamento
    assert "ContaBancaria.tenant_id == tenant_id" in registrar_pagamento
    assert (
        "conta.valor_pago = _decimal_monetario(conta.valor_pago)" in registrar_pagamento
    )
    assert "_valor_reais_para_centavos" not in registrar_pagamento
    assert "valor_centavos" not in registrar_pagamento
    assert "valor=valor_total_pagamento" in registrar_pagamento
    assert "conta_bancaria.saldo_atual -= valor_total_pagamento" in registrar_pagamento


def test_registrar_pagamento_valida_forma_pagamento_do_tenant_antes_de_gravar():
    source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_pagamento_routes.py"
    ).read_text(encoding="utf-8")
    registrar_pagamento = source.split("async def registrar_pagamento(", 1)[1].split(
        "# ============================================================================\n# DASHBOARD / RESUMO",
        1,
    )[0]

    assert "forma_pagamento_validada_id" in registrar_pagamento
    assert "FormaPagamento.id == pagamento.forma_pagamento_id" in registrar_pagamento
    assert "FormaPagamento.tenant_id == tenant_id" in registrar_pagamento
    assert "Forma de pagamento selecionada nao foi encontrada" in registrar_pagamento
    assert "forma_pagamento_id=forma_pagamento_validada_id" in registrar_pagamento
