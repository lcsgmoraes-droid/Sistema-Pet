import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const instante = (minuto) => `2026-10-20T19:${String(minuto).padStart(2, "0")}:00.000Z`;
const custos = (extra = {}) => ({
  commission_merchant_percent: 12,
  commission_ifood_percent: 23,
  payment_fee_percent: 3,
  tax_percent: 4,
  additional_unit_cost: 1,
  target_margin_percent: 20,
  ...extra,
});
const oferta = (preco = 150, minuto = 0, extra = {}) => ({
  product_id: 2,
  evaluated_at: instante(minuto),
  next_price_change_at: null,
  saved_specific_price: 150,
  regular_price: preco,
  effective_price: preco,
  promotion_active: false,
  pending: [],
  simulation_costs: custos(),
  simulation_costs_active: false,
  ...extra,
});

function pendente() {
  let resolver;
  let rejeitar;
  const promise = new Promise((resolve, reject) => {
    resolver = resolve;
    rejeitar = reject;
  });
  return { promise, resolver, rejeitar };
}

function preparar({ podeEditar = true } = {}) {
  const ofertas = [];
  const simulacoes = [];
  const gravacoes = [];
  const aplicados = [];
  const timers = new Map();
  let sequencia = 0;
  let retomada;
  const requisicao = (lista, payload, config) => {
    const resposta = pendente();
    lista.push({ payload, config, ...resposta });
    return resposta.promise;
  };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useIfoodSimulacaoPreco.js", import.meta.url)),
    {
      invoke: (hook, props) => hook(props.item, props.opcoes),
      props: {
        item: oferta(),
        opcoes: { podeEditar, onAplicado: (item) => aplicados.push(item) },
      },
      mocks: new Map([
        [
          "../../api/ifood",
          {
            getIfoodCatalogo: (payload, config) => requisicao(ofertas, payload, config),
            simularPrecoIfoodProduto: (payload, config) => requisicao(simulacoes, payload, config),
          },
        ],
        [
          "../../api/produtos",
          { updateProduto: (id, payload) => requisicao(gravacoes, { id, ...payload }) },
        ],
        [
          "../../hooks/useIfoodPromotionRefresh",
          {
            __esModule: true,
            default: (metadata, callback, options) => {
              retomada = { metadata, callback, options };
            },
          },
        ],
        ["./ifoodPresentation", { mensagemErroIfood: (_, fallback) => fallback }],
      ]),
      globals: {
        AbortController,
        window: {
          setTimeout(callback) {
            const id = ++sequencia;
            timers.set(id, callback);
            return id;
          },
          clearTimeout(id) {
            timers.delete(id);
          },
        },
      },
    },
  );
  async function executarDebounce() {
    const callbacks = [...timers.values()];
    timers.clear();
    callbacks.forEach((callback) => callback());
    await harness.settle();
  }
  async function concluirConsultas(atual = oferta(), simulada = atual) {
    ofertas.at(-1).resolver({ data: { items: [atual] } });
    await executarDebounce();
    simulacoes.at(-1).resolver({ data: simulada });
    await harness.settle();
  }
  return {
    harness,
    ofertas,
    simulacoes,
    gravacoes,
    aplicados,
    executarDebounce,
    concluirConsultas,
    get retomada() {
      return retomada;
    },
  };
}

test("resposta antiga de preço não substitui a digitação mais recente nem grava", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  const anterior = env.simulacoes.at(-1);
  await env.harness.act(() => env.harness.tree.alterarValor(170));
  assert.equal(anterior.config.signal.aborted, true);
  assert.equal(env.harness.tree.pronta, false);
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(170) });
  await env.harness.settle();
  anterior.resolver({ data: oferta(160) });
  await env.harness.settle();
  assert.equal(env.harness.tree.valor, 170);
  assert.equal(env.harness.tree.resultado.effective_price, 170);
  assert.equal(env.harness.tree.salvo.effective_price, 150);
  assert.equal(env.harness.tree.pronta, true);
  assert.deepEqual(env.gravacoes, []);
});

test("viradas renovam oferta e simulação preservando o preço digitado sem gravar", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  await env.harness.act(() => env.retomada.callback());
  assert.equal(env.harness.tree.pronta, false);
  assert.equal(env.harness.tree.valor, 160);
  const ativa = oferta(120, 1, {
    regular_price: 150,
    promotion_active: true,
    next_price_change_at: instante(2),
    pending: [{ code: "margem_abaixo_meta", kind: "rentabilidade" }],
  });
  await env.concluirConsultas(ativa, { ...ativa, regular_price: 160 });
  assert.equal(env.harness.tree.salvo.effective_price, 120);
  assert.equal(env.harness.tree.resultado.effective_price, 120);
  assert.equal(env.harness.tree.valor, 160);
  await env.harness.act(() => env.retomada.callback());
  await env.concluirConsultas(oferta(150, 3), oferta(160, 3));
  assert.equal(env.harness.tree.salvo.effective_price, 150);
  assert.equal(env.harness.tree.resultado.effective_price, 160);
  assert.deepEqual(env.harness.tree.resultado.pending, []);
  assert.equal(env.harness.tree.valor, 160);
  assert.deepEqual(env.gravacoes, []);
});

test("falha de reconsulta mantém rascunho e última estimativa mas bloqueia aplicação", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  await env.harness.act(() => env.retomada.callback());
  env.ofertas.at(-1).rejeitar(new Error("offline"));
  await env.executarDebounce();
  env.simulacoes.at(-1).rejeitar(new Error("offline"));
  await env.harness.settle();
  assert.equal(env.harness.tree.pronta, false);
  assert.match(env.harness.tree.erroOferta, /última oferta/);
  assert.match(env.harness.tree.erroSimulacao, /Não foi possível/);
  assert.equal(env.harness.tree.valor, 160);
  assert.equal(env.harness.tree.resultado.effective_price, 160);
  await env.harness.act(() => env.harness.tree.aplicar());
  assert.deepEqual(env.gravacoes, []);
  await env.harness.act(() => env.harness.tree.repetir());
  await env.concluirConsultas(oferta(150, 1), oferta(160, 1));
  assert.equal(env.harness.tree.pronta, true);
  assert.equal(env.harness.tree.erroOferta, "");
  assert.equal(env.harness.tree.erroSimulacao, "");
  assert.equal(env.harness.tree.valor, 160);
});

test("duplo clique aplica uma vez e envia somente o preço específico", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  const aplicar = env.harness.tree.aplicar;
  const primeira = aplicar();
  const segunda = aplicar();
  await env.harness.settle();
  assert.equal(env.gravacoes.length, 1);
  assert.deepEqual(env.gravacoes[0].payload, { id: 2, preco_ifood: 160 });
  assert.equal(env.harness.tree.salvando, true);
  assert.equal(env.harness.tree.pronta, false);
  assert.equal(env.retomada.options.enabled, false);
  env.gravacoes[0].resolver({ data: {} });
  await env.harness.settle();
  env.ofertas.at(-1).resolver({
    data: { items: [oferta(160, 1, { saved_specific_price: 160 })] },
  });
  await Promise.all([primeira, segunda]);
  await env.harness.settle();
  assert.equal(env.aplicados.length, 1);
  assert.equal(env.aplicados[0].saved_specific_price, 160);
  assert.equal(env.harness.tree.salvando, false);
  assert.equal(env.harness.tree.pronta, false, "reconsulta após PUT ainda está pendente");
  await env.concluirConsultas(oferta(160, 1, { saved_specific_price: 160 }));
  assert.equal(env.harness.tree.pronta, true);
  assert.equal(env.harness.tree.alterado, false);
});

test("sem permissão permite simular mas nunca aplica", async () => {
  const env = preparar({ podeEditar: false });
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  assert.equal(env.harness.tree.pronta, true);
  await env.harness.act(() => env.harness.tree.aplicar());
  assert.deepEqual(env.gravacoes, []);
});

test("oferta renovada não sobrescreve rascunho; restaurar usa valor salvo mais recente", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.harness.update({ item: oferta(180, 1, { saved_specific_price: 180 }) });
  assert.equal(env.harness.tree.valor, 160);
  assert.equal(env.harness.tree.salvo.regular_price, 180);
  await env.harness.act(() => env.harness.tree.restaurar());
  assert.equal(env.harness.tree.valor, 180);
  assert.equal(env.harness.tree.modo, "especifico");
  assert.deepEqual(env.gravacoes, []);
});

test("seguir regra da loja aplica null sem copiar outros campos", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarModo("regra_loja"));
  await env.executarDebounce();
  assert.deepEqual(env.simulacoes.at(-1).payload, { product_id: 2, preco_ifood: null });
  env.simulacoes.at(-1).resolver({ data: oferta(100) });
  await env.harness.settle();
  const aplicacao = env.harness.tree.aplicar();
  assert.deepEqual(env.gravacoes.at(-1).payload, { id: 2, preco_ifood: null });
  env.gravacoes.at(-1).resolver({ data: {} });
  await env.harness.settle();
  env.ofertas.at(-1).resolver({
    data: { items: [oferta(100, 1, { saved_specific_price: null })] },
  });
  await aplicacao;
  await env.harness.settle();
  assert.equal(env.aplicados.at(-1).saved_specific_price, null);
});

test("oferta mais antiga do GET não substitui nova oferta recebida da central", async () => {
  const env = preparar();
  await env.harness.update({ item: oferta(180, 2, { saved_specific_price: 180 }) });
  assert.deepEqual(env.ofertas[0].payload, { product_id: 2, limit: 1 });
  await env.concluirConsultas(oferta(150, 1), oferta(150, 2));
  assert.equal(env.harness.tree.salvo.effective_price, 180);
  assert.equal(env.harness.tree.salvo.saved_specific_price, 180);
  assert.equal(env.harness.tree.valor, 150, "oferta nova não troca valor iniciado pelo usuário");
  assert.deepEqual(env.gravacoes, []);
});

test("produto ausente na releitura bloqueia aplicação mesmo com simulação válida", async () => {
  const env = preparar();
  env.ofertas[0].resolver({ data: { items: [] } });
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(150) });
  await env.harness.settle();
  assert.match(env.harness.tree.erroOferta, /Não foi possível atualizar/);
  assert.equal(env.harness.tree.pronta, false);
  assert.equal(env.harness.tree.resultado.effective_price, 150);
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  await env.harness.act(() => env.harness.tree.aplicar());
  assert.deepEqual(env.gravacoes, []);
});

test("falha ao salvar conserva preço digitado, não confirma sucesso e relê oferta", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  const aplicacao = env.harness.tree.aplicar();
  await env.harness.settle();
  env.gravacoes.at(-1).rejeitar(new Error("servidor indisponível"));
  await aplicacao;
  await env.harness.settle();
  assert.match(env.harness.tree.erroSalvar, /Não foi possível aplicar/);
  assert.equal(env.harness.tree.sucesso, "");
  assert.equal(env.harness.tree.valor, 160);
  assert.equal(env.harness.tree.salvo.saved_specific_price, 150);
  assert.deepEqual(env.aplicados, []);
  assert.equal(env.harness.tree.pronta, false);
  await env.concluirConsultas(oferta(150, 1), oferta(160, 1));
  assert.equal(env.harness.tree.pronta, true);
  assert.equal(env.harness.tree.alterado, true);
});

test("taxas temporárias preservam zero e null e são enviadas somente à simulação", async () => {
  const env = preparar();
  await env.concluirConsultas();
  assert.equal(env.harness.tree.podeSimularCustos, true);
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("commission_merchant_percent", 15));
  await env.harness.act(() => env.harness.tree.alterarCusto("payment_fee_percent", 0));
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", null));
  await env.executarDebounce();
  const rascunho = custos({
    commission_merchant_percent: 15,
    payment_fee_percent: 0,
    tax_percent: null,
  });
  assert.deepEqual(env.simulacoes.at(-1).payload, {
    product_id: 2,
    preco_ifood: 150,
    custos_simulados: rascunho,
  });
  env.simulacoes.at(-1).resolver({
    data: oferta(150, 0, { simulation_costs: rascunho, simulation_costs_active: true }),
  });
  await env.harness.settle();
  assert.deepEqual(env.harness.tree.custosSimulados, rascunho);
  assert.equal(env.harness.tree.custosAtivos, true);
  assert.equal(env.harness.tree.alterado, false, "alterar taxas não cria preço para aplicar");
  assert.deepEqual(env.harness.tree.salvo.simulation_costs, custos());
  assert.deepEqual(env.gravacoes, []);
});

test("resposta antiga de taxas não substitui os valores ou a margem mais recentes", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", 5));
  await env.executarDebounce();
  const anterior = env.simulacoes.at(-1);
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", 8));
  assert.equal(anterior.config.signal.aborted, true);
  assert.equal(env.harness.tree.pronta, false);
  assert.equal(env.harness.tree.resultado, null);
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({
    data: oferta(150, 0, {
      simulation_costs: custos({ tax_percent: 8 }),
      simulation_costs_active: true,
    }),
  });
  await env.harness.settle();
  anterior.resolver({
    data: oferta(150, 0, {
      simulation_costs: custos({ tax_percent: 5 }),
      simulation_costs_active: true,
    }),
  });
  await env.harness.settle();
  assert.equal(env.harness.tree.resultado.simulation_costs.tax_percent, 8);
  assert.equal(env.harness.tree.custosSimulados.tax_percent, 8);
  assert.equal(env.harness.tree.pronta, true);
  assert.deepEqual(env.gravacoes, []);
});

test("promoção e reconsulta conservam taxas e preço temporários; restaurar taxas não muda preço", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("commission_ifood_percent", 26));
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  const simulada = oferta(120, 1, {
    regular_price: 160,
    promotion_active: true,
    next_price_change_at: instante(2),
    simulation_costs: custos({ commission_ifood_percent: 26 }),
    simulation_costs_active: true,
  });
  env.simulacoes.at(-1).resolver({ data: simulada });
  await env.harness.settle();
  await env.harness.act(() => env.retomada.callback());
  await env.concluirConsultas(oferta(120, 1), simulada);
  assert.equal(env.harness.tree.custosSimulados.commission_ifood_percent, 26);
  assert.equal(env.harness.tree.valor, 160);
  await env.harness.update({ item: oferta(150, 2) });
  assert.equal(env.harness.tree.custosSimulados.commission_ifood_percent, 26);
  await env.harness.act(() => env.harness.tree.restaurarCustos());
  await env.concluirConsultas(
    oferta(150, 2),
    oferta(160, 2, { simulation_costs: custos({ tax_percent: 7 }) }),
  );
  assert.deepEqual(env.simulacoes.at(-1).payload, { product_id: 2, preco_ifood: 160 });
  assert.equal(env.harness.tree.custosAtivos, false);
  assert.equal(env.harness.tree.custosSimulados.tax_percent, 7);
  assert.equal(env.harness.tree.valor, 160);
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  assert.equal(env.harness.tree.custosSimulados.tax_percent, 7);
  assert.equal(env.harness.tree.custosSimulados.commission_ifood_percent, 23);
  assert.deepEqual(env.gravacoes, []);
});

test("alternar taxas da loja conserva rascunho e restaurar preço não apaga taxas", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", 9));
  await env.harness.act(() => env.harness.tree.alterarValor(180));
  await env.harness.act(() => env.harness.tree.alterarModoCustos("loja"));
  await env.executarDebounce();
  assert.equal(Object.hasOwn(env.simulacoes.at(-1).payload, "custos_simulados"), false);
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  assert.equal(env.harness.tree.custosSimulados.tax_percent, 9);
  await env.harness.act(() => env.harness.tree.restaurar());
  assert.equal(env.harness.tree.valor, 150);
  assert.equal(env.harness.tree.custosSimulados.tax_percent, 9);
  assert.equal(env.harness.tree.custosAtivos, true);
});

test("aplicar somente preço relê oferta canônica e não contamina catálogo com taxas hipotéticas", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", 1));
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({
    data: oferta(160, 1, {
      simulation_costs: custos({ tax_percent: 1 }),
      simulation_costs_active: true,
      margins: { MERCHANT: { calculated: true, contribution: 99 } },
    }),
  });
  await env.harness.settle();
  const aplicacao = env.harness.tree.aplicar();
  await env.harness.settle();
  assert.deepEqual(env.gravacoes.at(-1).payload, { id: 2, preco_ifood: 160 });
  env.gravacoes.at(-1).resolver({ data: {} });
  await env.harness.settle();
  assert.deepEqual(env.aplicados, []);
  assert.equal(env.harness.tree.salvando, true);
  const canonica = oferta(160, 2, {
    saved_specific_price: 160,
    simulation_costs: undefined,
    simulation_costs_active: undefined,
    margins: { MERCHANT: { calculated: true, contribution: 20 } },
  });
  env.ofertas.at(-1).resolver({ data: { items: [canonica] } });
  await aplicacao;
  await env.harness.settle();
  assert.deepEqual(env.aplicados, [canonica]);
  assert.equal(env.harness.tree.salvo.margins.MERCHANT.contribution, 20);
  assert.equal(env.harness.tree.custosSimulados.tax_percent, 1);
  assert.equal(env.harness.tree.custosAtivos, true);
  assert.match(env.harness.tree.sucesso, /taxas.*não foram salvas/);
});

test("falha ao reler após PUT reconhece preço salvo e só confirma dados canônicos na recuperação", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarValor(160));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  const aplicacao = env.harness.tree.aplicar();
  env.gravacoes.at(-1).resolver({ data: {} });
  await env.harness.settle();
  env.ofertas.at(-1).rejeitar(new Error("offline após gravação"));
  await aplicacao;
  await env.harness.settle();
  assert.match(env.harness.tree.erroSalvar, /Preço salvo.*não foi possível atualizar/);
  assert.equal(env.harness.tree.sucesso, "");
  assert.equal(env.harness.tree.pronta, false);
  assert.deepEqual(env.aplicados, []);
  env.ofertas.at(-1).rejeitar(new Error("offline"));
  await env.executarDebounce();
  env.simulacoes.at(-1).resolver({ data: oferta(160) });
  await env.harness.settle();
  await env.harness.act(() => env.harness.tree.aplicar());
  assert.equal(env.gravacoes.length, 1);
  await env.harness.act(() => env.harness.tree.repetir());
  const canonica = oferta(160, 2, { saved_specific_price: 160 });
  await env.concluirConsultas(canonica);
  assert.deepEqual(env.aplicados, [canonica]);
  assert.equal(env.harness.tree.erroSalvar, "");
  assert.equal(env.harness.tree.alterado, false);
});

test("acesso sem editar produtos pode experimentar taxas sem gravar", async () => {
  const env = preparar({ podeEditar: false });
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", 0));
  await env.harness.act(() => env.harness.tree.alterarValor(180));
  await env.executarDebounce();
  assert.equal(env.simulacoes.at(-1).payload.custos_simulados.tax_percent, 0);
  env.simulacoes.at(-1).resolver({ data: oferta(180, 1, { simulation_costs_active: true }) });
  await env.harness.settle();
  await env.harness.act(() => env.harness.tree.aplicar());
  assert.deepEqual(env.gravacoes, []);
});

test("sem premissas na resposta não exibe editor nem envia taxas", async () => {
  const env = preparar();
  await env.concluirConsultas(oferta(150, 0, { simulation_costs: undefined }));
  assert.equal(env.harness.tree.podeSimularCustos, false);
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", 0));
  await env.harness.act(() => env.harness.tree.alterarValor(180));
  await env.executarDebounce();
  assert.equal(env.harness.tree.custosAtivos, false);
  assert.equal(Object.hasOwn(env.simulacoes.at(-1).payload, "custos_simulados"), false);
});

test("erro da simulação mantém taxas digitadas e reenvia rascunho no retry", async () => {
  const env = preparar();
  await env.concluirConsultas();
  await env.harness.act(() => env.harness.tree.alterarModoCustos("temporarios"));
  await env.harness.act(() => env.harness.tree.alterarCusto("tax_percent", 9));
  await env.executarDebounce();
  env.simulacoes.at(-1).rejeitar(new Error("offline"));
  await env.harness.settle();
  assert.equal(env.harness.tree.custosSimulados.tax_percent, 9);
  assert.equal(env.harness.tree.pronta, false);
  assert.match(env.harness.tree.erroSimulacao, /Não foi possível/);
  await env.harness.act(() => env.harness.tree.repetir());
  await env.executarDebounce();
  assert.equal(env.simulacoes.at(-1).payload.custos_simulados.tax_percent, 9);
  assert.deepEqual(env.gravacoes, []);
});
