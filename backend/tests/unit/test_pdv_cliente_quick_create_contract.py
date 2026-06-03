from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_modal_cadastro_cliente_pdv_usa_api_canonica_de_clientes():
    source = _read("frontend/src/components/pdv/ModalCadastroCliente.jsx")

    assert 'from "../../api/clientes"' in source
    assert "criarCliente(" in source
    assert 'api.post("/clientes"' not in source
    assert "api.post('/clientes'" not in source


def test_modal_cadastro_cliente_pdv_exibe_detalhe_do_erro_da_api():
    source = _read("frontend/src/components/pdv/ModalCadastroCliente.jsx")

    assert "error?.response?.data?.detail" in source
    assert "setErro(mensagemErro" in source
