import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const snapshot = (saldo = 100) => ({
  resumo: {
    caixa: { id: 1, numero_caixa: 16, usuario_nome: "Lucas", status: "aberto" },
    totais: { saldo_atual: saldo },
  },
  vendas: [],
  pagamentos: [],
  movimentacoes: [],
});

async function preparar({ saldo = 100 } = {}) {
  const operacoes = [];
  const fechamentos = [];
  const estadoHook = { inicial: false, atualizando: false, salvando: false };
  let dados = snapshot(saldo);
  let opcoes;
  let ler;
  const hook = (_, atuais) => {
    opcoes = atuais;
    return {
      ...estadoHook,
      atualizar: async () => {
        operacoes.push("atualizar");
        const atual = ler ? await ler() : dados;
        if (atual) opcoes.onResumo(atual.resumo);
        return atual;
      },
    };
  };
  const api = {
    validarCaixaAtual: async (id) => {
      operacoes.push("validar");
      return { id };
    },
    fecharCaixa: async (id, payload) => {
      operacoes.push("fechar");
      fechamentos.push({ id, payload });
      return { ...dados.resumo.caixa, status: "fechado" };
    },
    obterResumoCaixa: async () => {
      operacoes.push("resumo-fechado");
      return { ...dados.resumo, caixa: { ...dados.resumo.caixa, status: "fechado" } };
    },
    baixarPdfCaixa: async () => {},
  };
  const h = createControllerHarness(
    fileURLToPath(new URL("../ModalFecharCaixa.jsx", import.meta.url)),
    {
      props: { caixaId: 1, onClose() {}, onSuccess() {} },
      mocks: new Map([
        ["../api/caixa", api],
        ["lucide-react", { AlertCircle: "AlertCircle", X: "X" }],
        ["./caixa/useConferenciaFechamento", { __esModule: true, default: hook }],
        ["./caixa/ModalFecharCaixaContent", { __esModule: true, default: "ConteudoFechamento" }],
        ["./caixa/ImpressaoTermicaCaixa", { __esModule: true, default: "ImpressaoTermica" }],
      ]),
    },
  );
  await h.act(() => opcoes.onResumo(dados.resumo));
  return {
    h,
    operacoes,
    fechamentos,
    get conteudo() {
      return elements(h.tree).find((node) => node.type === "ConteudoFechamento")?.props;
    },
    get bloqueado() {
      return opcoes.bloqueado;
    },
    setLeitura(funcao) {
      ler = funcao;
    },
    async publicar(novo, flags = {}) {
      dados = novo;
      Object.assign(estadoHook, flags);
      await h.act(() => opcoes.onResumo(novo.resumo));
    },
    async prepararSaldo(novoSaldo) {
      dados = snapshot(novoSaldo);
      await h.update({});
    },
    async flags(novas) {
      Object.assign(estadoHook, novas);
      await h.update({});
    },
  };
}

test("refresh do resumo mantém contagem, cédulas, observações e o conteúdo montado", async () => {
  const env = await preparar();
  await env.h.act(() => {
    env.conteudo.setObservacoes("Conferir comprovantes de cartão.");
    env.conteudo.atualizarQuantidadeNota("n50", "2");
    env.conteudo.atualizarValorMoedas("3.25");
    env.conteudo.setMostrarContagem(true);
  });
  assert.equal(env.conteudo.calcularTotalNotas(), 103.25);
  await env.h.act(() => env.conteudo.aplicarContagem());
  const notas = env.conteudo.notas;
  const observacoes = env.conteudo.observacoes;
  assert.equal(env.conteudo.valorContado, 103.25);
  assert.match(observacoes, /Conferir comprovantes/);
  assert.match(observacoes, /\[Contagem de cedulas\]/);
  await env.h.act(() => env.conteudo.setMostrarContagem(true));
  await env.publicar(snapshot(120), { atualizando: true });
  assert.ok(env.conteudo, "refresh não deve substituir o conteúdo pelo loading inicial");
  assert.equal(env.conteudo.valorContado, 103.25);
  assert.equal(env.conteudo.notas, notas);
  assert.equal(env.conteudo.observacoes, observacoes);
  assert.equal(env.conteudo.mostrarContagem, true);
  assert.equal(env.conteudo.diferenca, -16.75);
  await env.flags({ atualizando: false });
  assert.equal(env.conteudo.valorContado, 103.25);
  assert.equal(env.conteudo.observacoes, observacoes);
  assert.deepEqual(env.fechamentos, []);
});

test("fechar lê saldo novo e exige nova confirmação se ele mudar durante a conferência", async () => {
  const env = await preparar();
  await env.h.act(() => {
    env.conteudo.setValorContado(100);
    env.conteudo.setObservacoes("Diferença conferida pelo operador.");
  });
  await env.prepararSaldo(120);
  await env.h.act(() => env.conteudo.handleFechar());
  assert.equal(env.conteudo.confirmandoDiferenca, true);
  assert.equal(env.conteudo.resumo.totais.saldo_atual, 120);
  assert.equal(env.conteudo.diferenca, -20);
  assert.deepEqual(env.fechamentos, []);
  await env.prepararSaldo(130);
  await env.h.act(() => env.conteudo.executarFechamento());
  assert.equal(env.conteudo.diferenca, -30);
  assert.deepEqual(env.fechamentos, [], "a confirmação anterior não autoriza a nova diferença");
  await env.h.act(() => env.conteudo.executarFechamento());
  assert.deepEqual(env.fechamentos, [
    {
      id: 1,
      payload: {
        valor_informado: 100,
        observacoes_fechamento: "Diferença conferida pelo operador.",
      },
    },
  ]);
  assert.deepEqual(env.operacoes, [
    "atualizar",
    "atualizar",
    "atualizar",
    "validar",
    "fechar",
    "resumo-fechado",
  ]);
  assert.equal(env.conteudo.sucesso, true);
  assert.equal(env.bloqueado, true);
  assert.equal(env.conteudo.valorContado, 100);
});

test("não fecha se a leitura atual falhar e conserva os dados digitados", async () => {
  const env = await preparar();
  await env.h.act(() => {
    env.conteudo.setValorContado(100);
    env.conteudo.setObservacoes("Contagem manual concluída.");
  });
  env.setLeitura(async () => null);
  await env.h.act(() => env.conteudo.handleFechar());
  assert.deepEqual(env.fechamentos, []);
  assert.deepEqual(env.operacoes, ["atualizar"]);
  assert.equal(env.conteudo.sucesso, false);
  assert.equal(env.conteudo.salvando, false);
  assert.equal(env.conteudo.valorContado, 100);
  assert.equal(env.conteudo.observacoes, "Contagem manual concluída.");
  assert.match(env.conteudo.erro, /atualizar o caixa antes do fechamento/);
});

test("não inicia fechamento enquanto uma marcação ou atualização está em andamento", async (t) => {
  for (const flag of ["salvando", "atualizando"]) {
    await t.test(flag, async () => {
      const env = await preparar();
      await env.h.act(() => env.conteudo.setValorContado(100));
      await env.flags({ [flag]: true });
      await env.h.act(() => env.conteudo.handleFechar());
      assert.deepEqual(env.operacoes, []);
      assert.deepEqual(env.fechamentos, []);
    });
  }
});

test("duplo clique no mesmo render faz apenas um fechamento", async () => {
  const env = await preparar();
  await env.h.act(() => env.conteudo.setValorContado(100));
  let liberar;
  const leitura = new Promise((resolve) => {
    liberar = resolve;
  });
  env.setLeitura(() => leitura);
  const fechar = env.conteudo.handleFechar;
  const primeira = fechar();
  const segunda = fechar();
  await env.h.settle();
  assert.equal(env.conteudo.salvando, true);
  liberar(snapshot(100));
  await Promise.all([primeira, segunda]);
  await env.h.settle();
  assert.equal(env.fechamentos.length, 1);
  assert.equal(env.conteudo.sucesso, true);
});
