import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
const preparado = () => ({
  origem: { numero: 1648 },
  dados: {
    serie: 1,
    produtos: [{ quantidade: 1, valorUnitario: 145, valorTotal: 145 }],
    pagamentos: [{ valor: 145 }],
  },
});

function setup() {
  const requests = [];
  const api = Object.fromEntries(
    ["get", "post", "put"].map((method) => [
      method,
      (path, body) => {
        if (path === "/nfe/clones" && method === "get")
          return Promise.resolve({ data: { rascunhos: [] } });
        const pending = deferred();
        requests.push({ method, path, body, ...pending });
        return pending.promise;
      },
    ]),
  );
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useClonagemNota.js", import.meta.url)),
    {
      props: { nota: { id: 44, provedor: "bling", numero: 1648, modelo: 55 } },
      invoke: (hook, props) =>
        hook(
          props.nota,
          () => {},
          () => {},
        ),
      mocks: new Map([
        ["../../api", api],
        [
          "../../utils/pdvFiscalStatus",
          {
            textoRespostaFiscal: (valor) =>
              typeof valor === "string" ? valor : valor?.detail || "Falha temporária",
          },
        ],
        [
          "../../utils/nfeCancelamentoFeedback",
          { resumirCancelamentoNota: () => ({ mensagem: "Pendente" }) },
        ],
      ]),
      globals: { structuredClone, Blob },
    },
  );
  async function ready() {
    requests[0].resolve({ data: preparado() });
    await harness.settle();
  }
  return { harness, requests, ready };
}

test("abrir cópia só prepara dados; clique duplo em salvar cria um rascunho", async () => {
  const env = setup();
  await env.harness.settle();
  assert.equal(env.harness.tree.carregando, true);
  assert.equal(env.requests[0].path, "/nfe/clones/preparar");
  await env.ready();
  await env.harness.act(() => env.harness.tree.alterar("produtos.0.valorUnitario", 120));
  let saving;
  await env.harness.act(() => {
    saving = env.harness.tree.salvar();
  });
  await env.harness.act(() => env.harness.tree.salvar());
  assert.equal(env.requests.filter((req) => req.path === "/nfe/clones").length, 1);
  const request = env.requests.at(-1);
  assert.equal(request.body.dados.produtos[0].valorTotal, 120);
  request.resolve({ data: { ...request.body, id: "clone-1", status: "rascunho" } });
  await saving;
  await env.harness.settle();
  assert.equal(env.harness.tree.registro.id, "clone-1");
  assert.equal(
    env.requests.some((req) => req.path.endsWith("/emitir")),
    false,
  );
});

test("falha incerta de emissão exige consultar situação antes de novo envio", async () => {
  const env = setup();
  await env.ready();
  let emitting;
  await env.harness.act(() => {
    emitting = env.harness.tree.emitir();
  });
  const create = env.requests.at(-1);
  create.resolve({ data: { ...create.body, id: "clone-1", status: "rascunho" } });
  await env.harness.settle();
  env.requests.at(-1).reject(new Error("Falha temporária"));
  await env.harness.settle();
  assert.equal(env.requests.at(-1).path, "/nfe/clones/clone-1");
  env.requests.at(-1).reject(new Error("Falha de consulta"));
  await emitting;
  await env.harness.settle();
  assert.equal(env.harness.tree.registro.status, "inconclusiva");
  await env.harness.act(() => env.harness.tree.emitir());
  assert.equal(env.requests.filter((req) => req.path.endsWith("/emitir")).length, 1);
});

test("resposta antiga de preparação não troca a nota mais recente", async () => {
  const env = setup();
  const antiga = env.requests[0];
  await env.harness.update({ nota: { id: 55, provedor: "bling", modelo: 55 } });
  const nova = env.requests.at(-1);
  nova.resolve({ data: { ...preparado(), origem: { numero: 1700 } } });
  await env.harness.settle();
  antiga.resolve({ data: preparado() });
  await env.harness.settle();
  assert.equal(env.harness.tree.registro.origem.numero, 1700);
  assert.equal(env.harness.tree.carregando, false);
});

test("download fiscal apresenta o detalhe do erro JSON recebido como Blob", async () => {
  const env = setup();
  await env.ready();
  let opening;
  await env.harness.act(() => {
    opening = env.harness.tree.abrirSalvo(5);
  });
  env.requests.at(-1).resolve({ data: { ...preparado(), id: 5, status: "autorizada" } });
  await opening;
  await env.harness.settle();
  let downloading;
  await env.harness.act(() => {
    downloading = env.harness.tree.baixarDocumento("xml");
  });
  env.requests.at(-1).reject({
    response: {
      data: new Blob([JSON.stringify({ detail: "O XML ainda não está disponível." })]),
    },
  });
  await downloading;
  await env.harness.settle();
  assert.equal(env.harness.tree.erro, "O XML ainda não está disponível.");
  assert.equal(env.harness.tree.registro.status, "autorizada");
});
