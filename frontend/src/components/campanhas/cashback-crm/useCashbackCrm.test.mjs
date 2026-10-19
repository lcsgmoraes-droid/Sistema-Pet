import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../../scripts/helpers/reactControllerHarness.mjs";

const componentPath = fileURLToPath(new URL("./useCashbackCrm.js", import.meta.url));
const BASE = "/campanhas/cashback/clientes";
const clienteInicial = {
  cliente_id: 4,
  nome: "Cliente de Teste",
  codigo: "TESTE",
  saldo_cashback: 25,
  telefone: "5518999998888",
  status: "sem_contato",
  whatsapp_disponivel: true,
  proximo_contato_em: null,
};

function respostaLista(cliente) {
  return {
    data: {
      clientes: [cliente],
      resumo: { total_clientes: 1, saldo_total: cliente.saldo_cashback },
      paginacao: { pagina: 1, paginas: 1, total: 1 },
    },
  };
}

function promessaPendente() {
  let resolver;
  const promise = new Promise((resolve) => {
    resolver = resolve;
  });
  return { promise, resolver };
}

function preparar({
  popupBloqueado = false,
  falharPrimeiroPost = false,
  somenteLeitura = false,
  buscar,
} = {}) {
  const chamadas = [];
  const abas = [];
  const avisos = [];
  let clienteAtual = { ...clienteInicial };
  let totalPosts = 0;
  const api = {
    get: async (url, options) => {
      chamadas.push({ metodo: "get", url, options });
      if (buscar) return buscar(url, options);
      return url === BASE
        ? respostaLista({ ...clienteAtual })
        : { data: { contatos: [], paginacao: { pagina: 1, paginas: 1, total: 0 } } };
    },
    post: async (url, payload) => {
      chamadas.push({ metodo: "post", url, payload });
      totalPosts += 1;
      if (falharPrimeiroPost && totalPosts === 1) {
        throw { response: { data: { detail: "Resposta perdida" } } };
      }
      const status = url.endsWith("/whatsapp") ? "conversa_aberta" : payload.status;
      clienteAtual = {
        ...clienteAtual,
        status,
        proximo_contato_em: payload.proximo_contato_em || null,
      };
      return {
        data: {
          contato: {
            id: totalPosts,
            status,
            proximo_contato_em: clienteAtual.proximo_contato_em,
          },
          cliente: { ...clienteAtual },
          whatsapp_url: "https://wa.me/5518999998888?text=Teste",
        },
      };
    },
  };
  const janela = {
    setTimeout: () => 1,
    clearTimeout: () => {},
    open: () => {
      if (popupBloqueado) return null;
      const aba = {
        opener: {},
        location: {
          replace: (url) => {
            aba.url = url;
          },
        },
        close: () => {
          aba.fechada = true;
        },
      };
      abas.push(aba);
      return aba;
    },
  };
  const harness = createControllerHarness(componentPath, {
    props: {},
    globals: { window: janela, crypto: { randomUUID } },
    mocks: new Map([
      ["../../../api", { __esModule: true, default: api }],
      [
        "react-hot-toast",
        {
          __esModule: true,
          default: {
            success: (mensagem) => avisos.push({ tipo: "sucesso", mensagem }),
            error: (mensagem) => avisos.push({ tipo: "erro", mensagem }),
          },
        },
      ],
      [
        "../../../contexts/AuthContext",
        {
          useAuth: () => ({
            user: {
              role: "atendente",
              permissions: somenteLeitura ? [] : ["clientes.editar"],
            },
          }),
        },
      ],
    ]),
  });
  return {
    harness,
    chamadas,
    abas,
    avisos,
    posts: () => chamadas.filter((chamada) => chamada.metodo === "post"),
  };
}

async function selecionarCliente(harness) {
  await harness.settle();
  await harness.act(() => harness.tree.abrirCliente(clienteInicial));
}

test("mantém loading inicial e ignora resposta antiga depois de trocar o filtro", async () => {
  const primeira = promessaPendente();
  const segunda = promessaPendente();
  const { harness, chamadas } = preparar({
    buscar: (_url, options) =>
      options.params.status === "interessado" ? segunda.promise : primeira.promise,
  });
  assert.equal(harness.tree.loading, true);
  assert.deepEqual(harness.tree.clientes, []);
  await harness.act(() => harness.tree.mudarStatus("interessado"));
  assert.equal(chamadas[0].options.signal.aborted, true);
  segunda.resolver(respostaLista({ ...clienteInicial, nome: "Resposta atual" }));
  await harness.settle();
  assert.equal(harness.tree.loading, false);
  assert.equal(harness.tree.clientes[0].nome, "Resposta atual");
  primeira.resolver(respostaLista({ ...clienteInicial, nome: "Resposta antiga" }));
  await harness.settle();
  assert.equal(harness.tree.clientes[0].nome, "Resposta atual");
  assert.equal(harness.tree.loading, false);
});

test("popup bloqueado não grava contato nem anuncia sucesso", async () => {
  const { harness, posts, abas, avisos } = preparar({ popupBloqueado: true });
  await selecionarCliente(harness);
  await harness.act(() => harness.tree.abrirWhatsApp());
  assert.equal(posts().length, 0);
  assert.equal(abas.length, 0);
  assert.equal(avisos.at(-1).tipo, "erro");
  assert.match(avisos.at(-1).mensagem, /bloqueou/);
});

test("duas aberturas no mesmo instante geram apenas um POST e uma aba", async () => {
  const { harness, posts, abas, avisos } = preparar();
  await selecionarCliente(harness);
  await harness.act(() => {
    const abrir = harness.tree.abrirWhatsApp;
    return Promise.all([abrir(), abrir()]);
  });
  assert.equal(posts().length, 1);
  assert.equal(posts()[0].url, `${BASE}/4/contatos/whatsapp`);
  assert.equal(abas.length, 1);
  assert.equal(abas[0].opener, null);
  assert.match(abas[0].url, /^https:\/\/wa.me\//);
  assert.equal(avisos.filter((aviso) => aviso.tipo === "sucesso").length, 1);
});

test("falha fecha a aba, preserva texto e reutiliza a chave ao tentar novamente", async () => {
  const { harness, posts, abas, avisos } = preparar({ falharPrimeiroPost: true });
  await selecionarCliente(harness);
  await harness.act(() => harness.tree.setMensagem("Mensagem editada 🐾"));
  await harness.act(() => harness.tree.abrirWhatsApp());
  assert.equal(abas[0].fechada, true);
  assert.equal(abas[0].url, undefined);
  assert.equal(harness.tree.mensagem, "Mensagem editada 🐾");
  assert.deepEqual(
    avisos.map((aviso) => aviso.tipo),
    ["erro"],
  );
  await harness.act(() => harness.tree.abrirWhatsApp());
  assert.equal(posts().length, 2);
  assert.equal(posts()[0].payload.chave_cliente, posts()[1].payload.chave_cliente);
  assert.equal(posts()[1].payload.mensagem, "Mensagem editada 🐾");
  assert.equal(harness.tree.selecionado.status, "conversa_aberta");
  assert.match(abas[1].url, /^https:\/\/wa.me\//);
});

test("editar a mensagem depois de uma falha cria uma nova tentativa", async () => {
  const { harness, posts } = preparar({ falharPrimeiroPost: true });
  await selecionarCliente(harness);
  await harness.act(() => harness.tree.abrirWhatsApp());
  await harness.act(() => harness.tree.setMensagem("Outra mensagem"));
  await harness.act(() => harness.tree.abrirWhatsApp());
  assert.equal(posts().length, 2);
  assert.notEqual(posts()[0].payload.chave_cliente, posts()[1].payload.chave_cliente);
  assert.equal(posts()[1].payload.mensagem, "Outra mensagem");
});

test("dois salvamentos no mesmo instante geram apenas um acompanhamento", async () => {
  const { harness, posts, abas } = preparar();
  await selecionarCliente(harness);
  await harness.act(() =>
    harness.tree.setForm({
      status: "interessado",
      observacao: "  Quer retornar  ",
      proximo_contato_em: "",
    }),
  );
  await harness.act(() => {
    const salvar = harness.tree.salvarAcompanhamento;
    return Promise.all([salvar(), salvar()]);
  });
  assert.equal(posts().length, 1);
  assert.equal(posts()[0].url, `${BASE}/4/acompanhamento`);
  assert.equal(posts()[0].payload.observacao, "Quer retornar");
  assert.equal(posts()[0].payload.proximo_contato_em, null);
  assert.equal(harness.tree.form.status, "interessado");
  assert.equal(harness.tree.form.observacao, "");
  assert.equal(abas.length, 0);
});

test("sem clientes.editar os handlers não abrem abas nem gravam contatos", async () => {
  const { harness, posts, abas } = preparar({ somenteLeitura: true });
  await selecionarCliente(harness);
  assert.equal(harness.tree.podeEditar, false);
  await harness.act(() =>
    Promise.all([harness.tree.abrirWhatsApp(), harness.tree.salvarAcompanhamento()]),
  );
  assert.equal(posts().length, 0);
  assert.equal(abas.length, 0);
});

test("retornar depois exige uma data antes de gravar o acompanhamento", async () => {
  const { harness, posts, avisos } = preparar();
  await selecionarCliente(harness);
  await harness.act(() =>
    harness.tree.setForm({
      status: "retornar_depois",
      observacao: "Contato na próxima semana",
      proximo_contato_em: "",
    }),
  );
  await harness.act(() => harness.tree.salvarAcompanhamento());
  assert.equal(posts().length, 0);
  assert.equal(avisos.at(-1).tipo, "erro");
  assert.match(avisos.at(-1).mensagem, /data/);
  assert.equal(harness.tree.form.observacao, "Contato na próxima semana");
});
