from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_contas_pagar_tem_endpoint_de_edicao_geral():
    source = (REPO_ROOT / "backend/app/contas_pagar_routes.py").read_text(encoding="utf-8")

    assert '@router.patch("/{conta_id}")' in source
    assert "def atualizar_conta_pagar(" in source
    assert "fornecedor_id: Optional[int]" in source
    assert "data_emissao: Optional[date]" in source
    assert "documento: Optional[str]" in source
    assert "valor_final = (" in source
    assert "valor_original + valor_juros + valor_multa - valor_desconto" in source


def test_busca_conta_pagar_respeita_tenant_na_consulta():
    source = (REPO_ROOT / "backend/app/contas_pagar_routes.py").read_text(encoding="utf-8")
    buscar_conta = source.split("def buscar_conta_pagar(", 1)[1].split(
        "# ============================================================================\n# REGISTRAR PAGAMENTO",
        1,
    )[0]

    assert "ContaPagar.tenant_id == tenant_id" in buscar_conta
    assert "Cliente.tenant_id == tenant_id" in buscar_conta
