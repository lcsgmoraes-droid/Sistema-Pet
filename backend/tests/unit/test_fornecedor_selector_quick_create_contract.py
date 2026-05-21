from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_fornecedor_rapido_permite_pf_pj_e_envia_documento_correto():
    source = _read("frontend/src/components/fornecedores/FornecedorSelector.jsx")

    assert 'tipo_pessoa: "PJ"' not in source
    assert "tipo_pessoa: tipoPessoa" in source
    assert "Pessoa Física" in source
    assert "Pessoa Jurídica" in source
    assert 'cpf: tipoPessoa === "PF"' in source
    assert 'cnpj: tipoPessoa === "PJ"' in source
    assert "event.stopPropagation()" in source
    assert "createPortal(" in source


def test_fornecedor_rapido_salva_na_base_de_pessoas_como_fornecedor():
    frontend_api = _read("frontend/src/api/clientes.js")
    selector = _read("frontend/src/components/fornecedores/FornecedorSelector.jsx")
    clientes_routes = _read("backend/app/clientes_routes.py")

    assert "api.post('/clientes/', dados)" in frontend_api
    assert 'tipo_cadastro: "fornecedor"' in selector
    assert "novo_cliente = Cliente(" in clientes_routes
    assert "**dados_cliente" in clientes_routes


def test_mensagens_do_cadastro_rapido_nao_voltam_com_mojibake():
    selector = _read("frontend/src/components/fornecedores/FornecedorSelector.jsx")
    clientes_routes = _read("backend/app/clientes_routes.py")

    assert "Cadastro rápido para continuar o fluxo." in selector
    assert "CNPJ é obrigatório para Pessoa Jurídica" in clientes_routes
    assert "Já existe um {cliente_data.tipo_cadastro} cadastrado com este CPF" in clientes_routes
    assert "Já existe um {cliente_data.tipo_cadastro} cadastrado com este CNPJ" in clientes_routes
