from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_recorrencia_usa_janela_rolante_de_12_meses():
    source = _source("app/contas_pagar_routes.py")

    assert "RECORRENCIA_JANELA_MESES_PADRAO = 12" in source
    assert "calcular_limite_janela_recorrencia" in source
    assert "_gerar_contas_recorrentes_ate_janela(" in source
    assert "limite_recorrencia = calcular_limite_janela_recorrencia(hoje)" in source
    assert "ContaPagar.proxima_recorrencia <= limite_recorrencia" in source
    assert "while conta_origem.proxima_recorrencia and conta_origem.proxima_recorrencia <= limite_recorrencia:" in source


def test_recorrencia_gerada_preserva_classificacao_financeira_e_competencia():
    source = _source("app/contas_pagar_routes.py")

    assert "dre_subcategoria_id=conta_origem.dre_subcategoria_id" in source
    assert "canal=conta_origem.canal" in source
    assert "tipo_despesa_id=conta_origem.tipo_despesa_id" in source
    assert "tenant_id=tenant_id" in source
    assert "data_emissao=nova_data_vencimento" in source
    assert "data_lancamento=nova_conta.data_vencimento" in source
    assert "ContaPagar.data_vencimento == nova_data_vencimento" in source


def test_pagamento_de_recorrencia_reabastece_janela_de_12_meses():
    source = _source("app/contas_pagar_routes.py")

    assert "_garantir_janela_recorrencia_apos_pagamento(" in source

    registrar_pagamento = source.split("async def registrar_pagamento(", 1)[1].split(
        "# ============================================================================\n# DASHBOARD / RESUMO",
        1,
    )[0]

    assert "if conta.status == 'pago':" in registrar_pagamento
    assert "_garantir_janela_recorrencia_apos_pagamento(" in registrar_pagamento


def test_edicao_de_conta_pagar_pode_ativar_recorrencia():
    source = _source("app/contas_pagar_routes.py")

    update_model = source.split("class ContaPagarUpdate", 1)[1].split("class ContaPagarResponse", 1)[0]
    for field in [
        "eh_recorrente",
        "tipo_recorrencia",
        "intervalo_dias",
        "data_inicio_recorrencia",
        "data_fim_recorrencia",
        "numero_repeticoes",
    ]:
        assert field in update_model

    update_endpoint = source.split("def atualizar_conta_pagar", 1)[1].split(
        "def buscar_conta_pagar",
        1,
    )[0]

    assert "recorrencia_alterada" in update_endpoint
    assert "conta.proxima_recorrencia = calcular_proxima_recorrencia(" in update_endpoint
    assert "_gerar_contas_recorrentes_ate_janela(" in update_endpoint
    assert "conta.eh_recorrente = False" in update_endpoint
