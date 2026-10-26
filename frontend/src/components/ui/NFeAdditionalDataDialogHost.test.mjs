import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as additionalData from "../../utils/nfeAdditionalData.mjs";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function setup() {
  const requests = [],
    resultados = [];
  const api = Object.fromEntries(
    ["get", "put"].map((method) => [
      method,
      (path, body) => {
        const value = deferred();
        requests.push({ method, path, body, ...value });
        return value.promise;
      },
    ]),
  );
  const componentMocks = [
    "BotaoCancelar",
    "BotaoInteracao",
    "BotaoSalva",
    "InputCombobox",
    "InputCpfCnpj",
    "InputTexto",
    "InputTextoLongo",
  ].map((nome) => [`../v2/${nome}/${nome}`, nome]);
  const harness = createControllerHarness(
    fileURLToPath(new URL("./NFeAdditionalDataDialogHost.jsx", import.meta.url)),
    {
      exportName: "NFeAdditionalDataDialog",
      props: { dialogo: { id: 10, vendaId: 123 } },
      mocks: new Map([
        ["../../api", api],
        ["../../utils/nfeAdditionalData.mjs", additionalData],
        [
          "../../services/nfeAdditionalDataDialog",
          { resolverDadosAdicionaisNota: (id, resultado) => resultados.push({ id, resultado }) },
        ],
        [
          "../../utils/pdvFiscalStatus",
          { textoRespostaFiscal: (dados) => (typeof dados === "string" ? dados : dados.detail) },
        ],
        ["lucide-react", { FileText: "icone-nota", RefreshCw: "icone-recarregar" }],
        ...componentMocks,
      ]),
      globals: { window: { addEventListener() {}, removeEventListener() {} } },
    },
  );
  const field = (label) => elements(harness.tree).find((item) => item.props?.label === label);
  const button = (texto) =>
    elements(harness.tree).find(
      (item) => item.type?.startsWith?.("Botao") && elementText(item) === texto,
    );
  async function ready(dados = {}, pode_editar = true) {
    requests.at(-1).resolve({ data: { dados, pode_editar } });
    await harness.settle();
  }
  return { harness, requests, resultados, field, button, ready };
}

test("mostra um loading único até obter os dados finais da venda", async () => {
  const env = setup();
  assert.match(elementText(env.harness.tree), /Carregando os dados da nota/);
  assert.equal(env.field("Canal desta operação"), undefined);
  await env.ready({
    canal: "amazon",
    numero_pedido: "PEDIDO-QA-333",
    codigo_rastreamento: "R-QA-12",
  });
  assert.equal(env.field("Número do pedido da Amazon").props.value, "PEDIDO-QA-333");
  assert.equal(env.field("Código de rastreamento (opcional)").props.value, "R-QA-12");
  assert.doesNotMatch(elementText(env.harness.tree), /Carregando os dados da nota/);
});

test("salvar persiste os dados uma vez antes de liberar a revisão fiscal", async () => {
  const env = setup();
  await env.ready();
  await env.harness.act(() => env.field("Canal desta operação").props.onChange("amazon"));
  await env.harness.act(() =>
    env.field("Número do pedido da Amazon").props.onChange("PEDIDO-QA-333"),
  );
  await env.harness.act(() =>
    env.field("CNPJ do intermediador").props.onChange("11.222.333/0001-81"),
  );
  await env.harness.act(() =>
    env.field("Identificação da sua loja ou vendedor na Amazon").props.onChange("VENDEDOR-QA"),
  );
  await env.harness.act(() =>
    env.field("Informações complementares").props.onChange("Texto fiscal conferido"),
  );
  let saving;
  await env.harness.act(() => {
    saving = env.button("Salvar e revisar nota").props.onClick();
  });
  await env.harness.act(() => env.button("Salvar e revisar nota").props.onClick());
  const put = env.requests.at(-1);
  assert.equal(env.requests.filter((request) => request.method === "put").length, 1);
  assert.equal(put.path, "/nfe/vendas/123/dados-adicionais");
  assert.equal(put.body.dados.intermediador_identificacao, "VENDEDOR-QA");
  assert.equal(put.body.dados.numero_pedido, "PEDIDO-QA-333");
  assert.equal(put.body.dados.informacoes_complementares, "Texto fiscal conferido");
  assert.deepEqual(env.resultados, []);
  put.resolve({ data: { dados: put.body.dados, pode_editar: true } });
  await saving;
  await env.harness.settle();
  assert.deepEqual(env.resultados, [{ id: 10, resultado: true }]);
});

test("fechar cancela e nota já enviada nunca oferece salvar", async () => {
  const env = setup();
  await env.ready({ canal: "amazon", numero_pedido: "PEDIDO-ANTERIOR" }, false);
  assert.equal(env.field("Canal desta operação").props.disabled, true);
  assert.equal(env.button("Salvar e revisar nota"), undefined);
  await env.harness.act(() => env.button("Fechar").props.onClick());
  assert.deepEqual(env.resultados, [{ id: 10, resultado: false }]);
  assert.equal(
    env.requests.some((request) => request.method === "put"),
    false,
  );
});

test("falha de salvar mantém revisão aberta e não libera emissão", async () => {
  const env = setup();
  await env.ready();
  await env.harness.act(() =>
    env.field("Informações complementares").props.onChange("Não perder este texto"),
  );
  let saving;
  await env.harness.act(() => {
    saving = env.button("Salvar e revisar nota").props.onClick();
  });
  env.requests.at(-1).reject({
    response: { data: { detail: "O envio fiscal já começou; os dados estão protegidos." } },
  });
  await saving;
  await env.harness.settle();
  assert.match(elementText(env.harness.tree), /dados estão protegidos/);
  assert.equal(env.field("Informações complementares").props.value, "Não perder este texto");
  assert.deepEqual(env.resultados, []);
});

test("resposta de carregamento anterior não substitui a venda atual", async () => {
  const env = setup();
  const primeiro = env.requests[0];
  await env.harness.update({ dialogo: { id: 11, vendaId: 456 } });
  await env.ready({ informacoes_complementares: "Dados da venda atual" });
  primeiro.resolve({
    data: { dados: { informacoes_complementares: "Venda antiga" }, pode_editar: true },
  });
  await env.harness.settle();
  assert.equal(env.field("Informações complementares").props.value, "Dados da venda atual");
  assert.doesNotMatch(elementText(env.harness.tree), /Carregando os dados da nota/);
});

test("erro estruturado de validação mostra mensagem legível e mantém dados", async () => {
  const env = setup();
  await env.ready();
  let saving;
  await env.harness.act(() => {
    saving = env.button("Salvar e revisar nota").props.onClick();
  });
  env.requests.at(-1).reject({
    response: { data: { detail: [{ msg: "Value error, Confira o CNPJ do intermediador." }] } },
  });
  await saving;
  await env.harness.settle();
  assert.match(elementText(env.harness.tree), /Confira o CNPJ do intermediador/);
  assert.doesNotMatch(elementText(env.harness.tree), /Value error|object Object/);
  assert.deepEqual(env.resultados, []);
});
