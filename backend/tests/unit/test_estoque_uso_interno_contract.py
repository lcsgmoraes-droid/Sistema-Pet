from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def _backend_source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def _repo_source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_saida_uso_interno_pode_gerar_conta_pagar_sem_desembolso():
    source = _backend_source("app/estoque_saida_manual_routes.py")

    assert "gerar_despesa_uso_interno" in source
    assert "ContaPagar(" in source
    assert 'saida.motivo == "uso_interno"' in source
    assert 'status="pago"' in source
    assert "valor_pago=valor_total_despesa" in source
    assert "sem desembolso financeiro" in source
    assert "dre_subcategoria_id=saida.dre_subcategoria_id" in source


def test_modal_estoque_expoe_saida_por_uso_interno():
    source = _repo_source("frontend/src/components/estoque/EstoqueLancamentoModal.jsx")

    assert "motivo_saida" in source
    assert "Uso interno" in source
    assert "Lancar custo no financeiro/DRE" in source
    assert "gerar_despesa_uso_interno" in source
    assert "descricao_despesa" in source
    assert "data_competencia" in source


def test_movimentacao_produto_envia_motivo_real_da_saida():
    source = _repo_source("frontend/src/components/MovimentacoesProduto.jsx")

    assert "payload.motivo = formData.motivo_saida" in source
    assert "payload.gerar_despesa_uso_interno" in source
    assert "payload.descricao_despesa" in source
    assert "payload.data_competencia" in source
    assert "payload.motivo = 'saida_manual'" not in source
