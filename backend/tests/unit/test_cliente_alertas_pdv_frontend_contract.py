from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_cadastro_cliente_expõe_editor_de_alertas_pdv():
    source = _read("frontend/src/components/clientes/ClientesNovoComplementaresStep.jsx")

    assert "Alertas do PDV" in source
    assert "Adicionar alerta" in source
    assert "Ativo no PDV" in source
    assert "buildEmptyClienteAlertaPdv" in source
    assert "alertas_pdv" in source


def test_formulario_cliente_normaliza_alertas_pdv_antes_de_salvar():
    source = _read("frontend/src/hooks/useClientesNovoCadastro.js")

    assert "normalizeClienteAlertasPdv" in source
    assert "alertas_pdv: []" in source
    assert "alertas_pdv: normalizeClienteAlertasPdv(cliente.alertas_pdv)" in source
    assert "clienteData.alertas_pdv = normalizeClienteAlertasPdv(clienteData.alertas_pdv)" in source


def test_pdv_exibe_alertas_ativos_do_cliente_selecionado():
    source = _read("frontend/src/components/pdv/PDVClienteCard.jsx")

    assert "getClienteAlertasPdvAtivos" in source
    assert "function ClienteAlertasPdv" in source
    assert "<ClienteAlertasPdv cliente={cliente} />" in source
    assert "whitespace-pre-wrap break-words" in source


def test_widget_info_cliente_exibe_secao_de_alertas_do_cliente():
    source = _read("frontend/src/components/ClienteInfoWidget.jsx")

    assert "getClienteAlertasPdvAtivos" in source
    assert "alertasCliente: true" in source
    assert 'titulo="Alertas do Cliente"' in source
    assert "badge={alertasCliente.length}" in source
