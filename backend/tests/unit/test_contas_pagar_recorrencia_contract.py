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
