import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const MENSAGEM = "Este telefone já pertence a outra pessoa. Localize o cadastro existente.";
const DADOS = {
  nome: "Pessoa de teste",
  tipo_pessoa: "PF",
  is_cliente: true,
  celular: "11999990001",
  telefone: "1133330001",
  contatos_adicionais: [{ numero: "11999990002", vinculo: "irmã" }],
};

function preparar(resposta, pessoa) {
  const avisos = [];
  const chamadas = [];
  const salvos = [];
  const enderecos = [];
  const setEnderecosAdicionais = () => {};
  const falhar = async (metodo, url, dados) => {
    chamadas.push({ metodo, url, dados });
    throw { response: resposta };
  };
  const mocks = new Map([
    ["lucide-react", {}],
    ["react-router-dom", { useNavigate: () => () => {} }],
    [
      "react-hot-toast",
      { __esModule: true, default: { error: (mensagem) => avisos.push(mensagem), success() {} } },
    ],
    ["../../contexts/ModulosContext", { useModulos: () => ({ moduloAtivo: () => false }) }],
    [
      "../../api",
      {
        __esModule: true,
        default: {
          get: async () => ({ data: {} }),
          post: (url, dados) => falhar("post", url, dados),
          put: (url, dados) => falhar("put", url, dados),
        },
      },
    ],
    [
      "../../hooks/useClientesNovoEnderecos",
      {
        useClientesNovoEnderecos: () => ({
          enderecosAdicionais: enderecos,
          setEnderecosAdicionais,
          enderecoAtual: null,
        }),
      },
    ],
  ]);
  for (const caminho of [
    "../v2/AbasNavegacao/AbasNavegacao",
    "../ModalAdicionarCredito",
    "../ModalRemoverCredito",
    "./ClientePessoaAlertasPdvSection",
    "./ClientePessoaComplementaresTab",
    "./ClientePessoaContatosTab",
    "./ClientePessoaDadosGeraisTab",
    "./ClientePessoaEnderecoModal",
    "./ClientePessoaEnderecoTab",
    "./ClientePessoaFinanceiroTab",
    "./ClientePessoaHistoricoPanel",
  ]) {
    mocks.set(caminho, { __esModule: true, default: caminho.split("/").at(-1) });
  }
  const harness = createControllerHarness(
    fileURLToPath(new URL("./PessoaFormulario.jsx", import.meta.url)),
    { props: { prefill: DADOS, pessoa, onSalvo: (valor) => salvos.push(valor) }, mocks },
  );
  return { harness, avisos, chamadas, salvos };
}

function componente(harness, tipo) {
  return elements(harness.tree).find((elemento) => elemento.type === tipo);
}

async function salvar(harness) {
  await harness.settle();
  await harness.act(() => componente(harness, "form").props.onSubmit({ preventDefault() {} }));
}

function conflito(loc) {
  return {
    status: 409,
    data: {
      detail: MENSAGEM,
      error: "pessoa_telefone_duplicado",
      details: [{ loc: ["body", ...loc], msg: MENSAGEM, type: "value_error" }],
    },
  };
}

function renderizarContatos(props) {
  const mocks = new Map([["lucide-react", {}]]);
  for (const caminho of [
    "../v2/BotaoInteracao/BotaoInteracao",
    "../ui/IconActionButton",
    "../v2/InputTelefone/InputTelefone",
    "../v2/InputTexto/InputTexto",
    "../v2/InputTextoLongo/InputTextoLongo",
  ]) {
    mocks.set(caminho, { __esModule: true, default: caminho.split("/").at(-1) });
  }
  return createControllerHarness(
    fileURLToPath(new URL("./ClientePessoaContatosTab.jsx", import.meta.url)),
    { props, mocks },
  );
}

for (const operacao of ["criação", "edição"]) {
  test(`409 de telefone na ${operacao} destaca campo, abre Contatos e preserva o formulário`, async () => {
    const pessoa = operacao === "edição" ? { ...DADOS, id: 901, codigo: "42" } : undefined;
    const { harness, avisos, chamadas, salvos } = preparar(conflito(["telefone"]), pessoa);
    await salvar(harness);
    const abas = componente(harness, "AbasNavegacao").props;
    assert.equal(abas.ativa, "contatos");
    assert.equal(abas.abas.find((aba) => aba.id === "contatos").invalida, true);
    const props = componente(harness, "ClientePessoaContatosTab").props;
    assert.equal(props.erros.telefone, MENSAGEM);
    assert.equal(props.formData.telefone, DADOS.telefone);
    assert.equal(props.formData.nome, DADOS.nome);
    assert.equal(chamadas.length, 1);
    assert.equal(chamadas[0].metodo, pessoa ? "put" : "post");
    assert.equal(chamadas[0].url, pessoa ? "/clientes/901" : "/clientes/");
    assert.deepEqual(salvos, []);
    assert.deepEqual(avisos, [MENSAGEM]);

    const tocados = [];
    const contatos = renderizarContatos({ ...props, onBlurCampo: (campo) => tocados.push(campo) });
    const telefone = elements(contatos.tree).find((campo) => campo.props?.id === "pessoa-telefone");
    assert.equal(telefone.props.error, MENSAGEM);
    await contatos.act(() => telefone.props.onBlur());
    assert.deepEqual(tocados, ["telefone"]);
    contatos.unmount();
    harness.unmount();
  });
}

test("409 de contato adicional destaca o número correspondente sem exibir objeto", async () => {
  const { harness, avisos } = preparar(conflito(["contatos_adicionais", 0, "numero"]));
  await salvar(harness);
  assert.equal(componente(harness, "AbasNavegacao").props.ativa, "contatos");
  const contatos = renderizarContatos(componente(harness, "ClientePessoaContatosTab").props);
  const numero = elements(contatos.tree).find(
    (campo) => campo.props?.id === "pessoa-contato-adicional-numero-0",
  );
  assert.equal(numero.props.error, MENSAGEM);
  assert.deepEqual(avisos, [MENSAGEM]);
  assert.doesNotMatch(elementText(contatos.tree), /\[object Object\]/);
  contatos.unmount();
  harness.unmount();
});

test("409 na lista de contatos adicionais mantém mensagem geral visível na seção", async () => {
  const { harness, avisos } = preparar(conflito(["contatos_adicionais"]));
  await salvar(harness);
  const contatos = renderizarContatos(componente(harness, "ClientePessoaContatosTab").props);
  const alerta = elements(contatos.tree).find((elemento) => elemento.props?.role === "alert");
  assert.equal(elementText(alerta), MENSAGEM);
  assert.deepEqual(avisos, [MENSAGEM]);
  contatos.unmount();
  harness.unmount();
});

test("422 mantém mapeamento por campo e abre a aba original do validador", async () => {
  const mensagem = "Informe um CRMV válido.";
  const { harness, avisos } = preparar({
    status: 422,
    data: {
      error: "validation_error",
      details: [{ loc: ["body", "crmv"], msg: mensagem, type: "value_error" }],
    },
  });
  await salvar(harness);
  assert.equal(componente(harness, "AbasNavegacao").props.ativa, "dados-gerais");
  assert.equal(componente(harness, "ClientePessoaDadosGeraisTab").props.erros.crmv, mensagem);
  assert.deepEqual(avisos, [mensagem]);
  harness.unmount();
});

test("outro 409 não é tratado como conflito de telefone e detail objeto nunca vira toast", async () => {
  const resposta = conflito(["telefone"]);
  resposta.data.error = "outro_conflito";
  resposta.data.detail = { mensagem: "Detalhe inesperado" };
  const { harness, avisos } = preparar(resposta);
  await salvar(harness);
  assert.equal(componente(harness, "AbasNavegacao").props.ativa, "dados-gerais");
  assert.deepEqual(avisos, ["Não foi possível salvar as alterações."]);
  assert.equal(
    avisos.every((mensagem) => typeof mensagem === "string"),
    true,
  );
  harness.unmount();
});

test("409 sem detalhes de campo conserva mensagem textual e abre Contatos", async () => {
  const resposta = conflito(["telefone"]);
  delete resposta.data.details;
  const { harness, avisos } = preparar(resposta);
  await salvar(harness);
  assert.equal(componente(harness, "AbasNavegacao").props.ativa, "contatos");
  assert.deepEqual(avisos, [MENSAGEM]);
  harness.unmount();
});
