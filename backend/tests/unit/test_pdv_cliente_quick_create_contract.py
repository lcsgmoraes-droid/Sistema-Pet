from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


# O cadastro rapido de cliente no PDV virou um wrapper fino em cima da modal unica
# de Pessoa (PessoaFormularioModal/PessoaFormulario) — ver AGENTS.md e
# .claude/skills/pessoas/SKILL.md. Estes testes verificam as mesmas garantias de
# negocio que a implementacao antiga tinha, só que nos arquivos onde elas moraram.


def test_modal_cadastro_cliente_pdv_delega_para_a_modal_unica_de_pessoa():
    source = _read("frontend/src/components/pdv/ModalCadastroCliente.jsx")

    assert 'from "../clientes/PessoaFormularioModal"' in source
    assert "api.post(" not in source
    assert "api.put(" not in source


def test_pessoa_formulario_usa_api_canonica_de_clientes_e_exibe_erro_real():
    source = _read("frontend/src/components/clientes/PessoaFormulario.jsx")

    assert 'await api.post("/clientes/", clienteData)' in source
    assert "await api.put(`/clientes/${pessoaAtual.id}`, clienteData)" in source
    assert "error.response?.data?.details" in source
    assert "detalhe.msg" in source


def test_modal_cadastro_cliente_pdv_infere_numero_buscado_como_celular():
    source = _read("frontend/src/components/pdv/ModalCadastroCliente.jsx")

    assert "return { ...base, celular: texto };" in source
