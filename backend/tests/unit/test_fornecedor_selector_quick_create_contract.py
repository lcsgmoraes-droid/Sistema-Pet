from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


# O cadastro rapido de fornecedor no combobox de Compras/Produtos virou um wrapper
# fino em cima da modal unica de Pessoa (PessoaFormularioModal/PessoaFormulario) —
# ver AGENTS.md e .claude/skills/pessoas/SKILL.md. A escolha PF/PJ e o
# CPF/CNPJ condicional saíram do modal bespoke e passaram a morar no formulario
# compartilhado (ClientePessoaDadosGeraisTab.jsx), usado por qualquer ponto de
# entrada de Pessoa, nao só o de fornecedor.


def test_fornecedor_selector_delega_para_a_modal_unica_de_pessoa():
    selector = _read("frontend/src/components/fornecedores/FornecedorSelector.jsx")

    assert 'from "../clientes/PessoaFormularioModal"' in selector
    assert "is_fornecedor: true" in selector
    assert "api.post(" not in selector


def test_pessoa_formulario_permite_pf_pj_e_exige_documento_correto():
    dados_gerais = _read(
        "frontend/src/components/clientes/ClientePessoaDadosGeraisTab.jsx"
    )
    formulario = _read("frontend/src/components/clientes/PessoaFormulario.jsx")

    assert 'tipo_pessoa: "PJ"' not in dados_gerais
    assert "Pessoa Física" in dados_gerais
    assert "Pessoa Jurídica" in dados_gerais
    assert "InputCpfCnpj" in dados_gerais

    assert 'erros.cnpj = "Informe o CNPJ."' in formulario
    assert "erros.razao_social" in formulario


def test_fornecedor_rapido_salva_na_base_de_pessoas_como_fornecedor():
    frontend_api = _read("frontend/src/api/clientes.js")
    formulario = _read("frontend/src/components/clientes/PessoaFormulario.jsx")
    clientes_crud = _read("backend/app/clientes/crud_routes.py")

    assert 'api.post("/clientes/", dados)' in frontend_api
    assert 'await api.post("/clientes/", clienteData)' in formulario
    assert "novo_cliente = Cliente(" in clientes_crud
    assert "**dados_cliente" in clientes_crud


def test_mensagens_do_cadastro_rapido_nao_voltam_com_mojibake():
    clientes_crud = _read("backend/app/clientes/crud_routes.py")

    assert "CNPJ é obrigatório para Pessoa Jurídica" in clientes_crud
    assert (
        "Já existe um {' / '.join(tipos_cadastro_da_pessoa(cliente_data)) or 'cadastro'} com este CPF"
        in clientes_crud
    )
    assert (
        "Já existe um {' / '.join(tipos_cadastro_da_pessoa(cliente_data)) or 'cadastro'} com este CNPJ"
        in clientes_crud
    )
