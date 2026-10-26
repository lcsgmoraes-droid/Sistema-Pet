import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as estornoUtils from "../../utils/nfeEstorno.js";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const previa = {
  modelo: 55,
  tipo_operacao: "entrada",
  finalidade: "ajuste",
  ambiente_label: "Homologação",
  original: { chave: "1".repeat(44) },
};
const livre = { elegivel: true, bloqueios: [], previa, estorno: null };

function preparar({ timeout = false, anonimo = false, confirma = true } = {}) {
  const envios = [];
  const consultas = [];
  let estorno = null;
  let atualizacoes = 0;
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useNFSaidaEstorno.js", import.meta.url)),
    {
      mocks: new Map([
        ["../../utils/nfeEstorno", estornoUtils],
        ["../../services/corepetDialog", { confirmarCorePet: async () => confirma }],
        [
          "../../api",
          {
            __esModule: true,
            default: {
              get: async (url, options) => {
                consultas.push({ url, options });
                const impedido = anonimo && !options?.params?.destinatario_proprio_emitente;
                return {
                  data: {
                    ...livre,
                    elegivel: !impedido && !estorno,
                    previa: impedido ? null : previa,
                    bloqueios: impedido ? ["Identifique o destinatário"] : [],
                    estorno,
                    destinatario_anonimo: anonimo,
                  },
                };
              },
              post: async (url, payload) => {
                envios.push({ url, payload });
                if (url.endsWith("/consultar")) {
                  estorno = {
                    id: 7,
                    status: "autorizado",
                    xml_validado: true,
                    protocolo: "1".repeat(15),
                    pode_consultar: true,
                  };
                } else {
                  estorno = {
                    id: 7,
                    status: timeout ? "incerto" : "processando",
                    pode_consultar: !timeout,
                  };
                  if (timeout)
                    throw {
                      response: {
                        data: { detail: "Resultado ainda não confirmado. Não reenviar." },
                      },
                    };
                }
                return { data: { ...livre, elegivel: false, previa: null, estorno } };
              },
            },
          },
        ],
      ]),
      props: { vendaId: 2, onAtualizado: () => atualizacoes++ },
    },
  );
  return {
    harness,
    envios,
    consultas,
    get atualizacoes() {
      return atualizacoes;
    },
  };
}

async function preencher(harness) {
  await harness.act(() => harness.tree.setMotivo("Operação não realizada e mercadoria não saiu."));
  await harness.act(() => harness.tree.setDeclarado(true));
}

test("duplo clique em emitir transmite uma vez e consulta usa endpoint separado sem reemissão", async () => {
  const env = preparar();
  assert.equal(env.harness.tree.loading, true);
  await env.harness.settle();
  assert.equal(env.harness.tree.podeEmitir, false);
  await preencher(env.harness);
  assert.equal(env.harness.tree.podeEmitir, true);
  await env.harness.act(() => Promise.all([env.harness.tree.emitir(), env.harness.tree.emitir()]));
  assert.equal(env.envios.length, 1);
  assert.equal(env.envios[0].url, "/nfe/vendas/2/estorno");
  assert.equal(env.envios[0].payload.declaracao_operacao_nao_realizada, true);
  assert.equal(env.harness.tree.podeEmitir, false);
  assert.equal(env.harness.tree.dados.previa.original.chave, previa.original.chave);
  await env.harness.act(() => env.harness.tree.consultar());
  assert.equal(env.envios[1].url, "/nfe/vendas/2/estorno/consultar");
  assert.equal(env.envios[1].payload, undefined);
  assert.equal(env.harness.tree.dados.estorno.status, "autorizado");
});

test("timeout mantém tentativa bloqueada e nunca repete POST de emissão", async () => {
  const env = preparar({ timeout: true });
  await env.harness.settle();
  await preencher(env.harness);
  await env.harness.act(() => env.harness.tree.emitir());
  assert.match(env.harness.tree.erro, /Não reenviar/);
  assert.equal(env.harness.tree.dados.estorno.status, "incerto");
  assert.equal(env.harness.tree.podeEmitir, false);
  assert.equal(env.harness.tree.podeConsultar, false);
  await env.harness.act(() => env.harness.tree.emitir());
  assert.equal(env.envios.length, 1);
});

test("destinatário próprio exige escolha explícita e nova prévia antes da confirmação", async () => {
  const env = preparar({ anonimo: true });
  await env.harness.settle();
  assert.equal(env.harness.tree.destinatarioProprio, false);
  assert.equal(env.harness.tree.podeEmitir, false);
  assert.equal(env.consultas[0].options.params, undefined);
  await env.harness.act(() => env.harness.tree.setDestinatarioProprio(true));
  assert.equal(env.consultas.at(-1).options.params.destinatario_proprio_emitente, true);
  assert.equal(env.harness.tree.declarado, false);
  await preencher(env.harness);
  await env.harness.act(() => env.harness.tree.emitir());
  assert.equal(env.envios[0].payload.destinatario_proprio_emitente, true);
});

test("desistir da confirmação fiscal não envia nem trava uma tentativa inexistente", async () => {
  const env = preparar({ confirma: false });
  await env.harness.settle();
  await preencher(env.harness);
  await env.harness.act(() => env.harness.tree.emitir());
  assert.equal(env.envios.length, 0);
  assert.equal(env.harness.tree.envioIniciado, false);
});
