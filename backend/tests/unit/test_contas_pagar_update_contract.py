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
    ).read_text(encoding="utf-8") + (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_pagamento_service.py"
    ).read_text(encoding="utf-8")

    assert "_decimal_monetario" in source
    assert "ContaPagar.tenant_id == tenant_id" in source
    assert "ContaBancaria.tenant_id == tenant_id" in source
    assert "conta.valor_pago = _decimal_monetario(conta.valor_pago)" in source
    assert "_valor_reais_para_centavos" not in source
    assert "valor_centavos" not in source
    assert "valor=valor_total_pagamento" in source
    assert "conta_bancaria.saldo_atual -= valor_total_pagamento" in source


def test_registrar_pagamento_valida_forma_pagamento_do_tenant_antes_de_gravar():
    source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_pagamento_routes.py"
    ).read_text(encoding="utf-8") + (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_pagamento_service.py"
    ).read_text(encoding="utf-8")

    assert "forma_pagamento_validada_id" in source
    assert "FormaPagamento.id == forma_pagamento_id" in source
    assert "FormaPagamento.tenant_id == tenant_id" in source
    assert "Forma de pagamento selecionada nao foi encontrada" in source
    assert "forma_pagamento_id=forma_pagamento_validada_id" in source


def test_registrar_pagamento_em_lote_usa_mesma_baixa_segura_do_pagamento_individual():
    source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_pagamento_routes.py"
    ).read_text(encoding="utf-8") + (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_pagamento_service.py"
    ).read_text(encoding="utf-8")
    schemas_source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_schemas.py"
    ).read_text(encoding="utf-8")

    assert "class PagamentoLoteCreate" in schemas_source
    assert "conta_ids: List[int]" in schemas_source
    assert '@router.post("/pagar-lote")' in source
    assert "async def registrar_pagamento_lote(" in source
    assert "aplicar_pagamento_conta_pagar(" in source
    assert "ContaPagar.tenant_id == tenant_id" in source
    assert "ContaPagar.id.in_(payload.conta_ids)" in source
    assert "conta.valor_final - conta.valor_pago" in source
    assert "pagamentos_registrados" in source
    assert "valor_total_pago" in source
    assert "conta_bancaria.saldo_atual -= valor_total_pagamento" in source


def test_listagem_contas_pagar_filtra_taxas_de_cartao():
    source = (
        REPO_ROOT / "backend/app/financeiro/contas_pagar_consulta_routes.py"
    ).read_text(encoding="utf-8")

    assert "ocultar_taxas_cartao: bool = Query(False)" in source
    assert "apenas_taxas_cartao: bool = Query(False)" in source
    assert "taxa_cartao_condition" in source
    assert "taxa credito" in source
    assert "taxa debito" in source
    assert "taxa cartao" in source
