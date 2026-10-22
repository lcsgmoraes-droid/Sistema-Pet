import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";
import { createEmptyDashboardSummary, createEmptyManagementMetrics } from "./dashboardOverview.js";

const componente = fileURLToPath(new URL("../v2/DashboardFinanceiro.jsx", import.meta.url));
const UI = {
  resumo: "ResumoFaturamento",
  detalhes: "DetalhesFaturamento",
  periodo: "SeletorOpcoes",
  intervalo: "InputPeriodo",
  indisponivel: "EstadoVazio",
};
const vazio = () => {};

function respostaResumo(liquido, vendaIds, formas = [{ forma_pagamento: "Pix", total: liquido }]) {
  const composicao = {
    escopo: "empresa",
    data_inicio: "2026-10-01",
    data_fim: "2026-10-22",
    faturamento_liquido: liquido,
    valor_pago: liquido,
    formas_pagamento: formas,
    total_formas_pagamento: liquido,
    ajustes_formas_pagamento: 0,
    quantidade: vendaIds.length,
    detalhes: vendaIds.map((venda_id) => ({
      venda_id,
      numero_venda: `DEV-${venda_id}`,
      pagamentos: [{ id: venda_id, forma_pagamento: "PIX", valor: 25 }],
    })),
  };
  const resumo = createEmptyDashboardSummary();
  resumo.composicao_vendas = composicao;
  resumo.vendas_periodo.quantidade = vendaIds.length;
  return resumo;
}

function preparar() {
  const consultas = [];
  const navegacoes = [];
  const monitores = [];
  let agora = Date.parse("2026-10-22T12:00:00.000Z");
  class Relogio extends Date {
    constructor(...args) {
      super(...(args.length ? args : [agora]));
    }
    static now() {
      return agora;
    }
  }
  const api = {
    get(url, config) {
      let resolver;
      let rejeitar;
      const promise = new Promise((resolve, reject) => {
        resolver = resolve;
        rejeitar = reject;
      });
      consultas.push({ url, config, resolver, rejeitar });
      return promise;
    },
  };
  const padrao = (type) => ({ __esModule: true, default: type });
  const harness = createControllerHarness(componente, {
    props: {},
    globals: { AbortController, Date: Relogio },
    mocks: new Map([
      ["../../api", padrao(api)],
      [
        "react-router-dom",
        {
          useNavigate:
            () =>
            (...args) =>
              navegacoes.push(args),
        },
      ],
      ["lucide-react", {}],
      ["recharts", {}],
      ["../../hooks/useTour", { useTour: () => ({ iniciarTour: vazio }) }],
      ["../../theme/ThemeContext", { useTheme: () => ({ isDark: false }) }],
      ["../../tours/tourDefinitions", { tourDashboard: [] }],
      ["../../components/v2/utils/tons", { TONS_BADGE: {} }],
      ["../../utils/formatters", { formatMoneyBRL: (valor) => String(valor || 0) }],
      [
        "../../components/financeiro/vendasFinanceiro/vendasFinanceiroDatas",
        { formatarDataLocal: (valor) => String(valor || "") },
      ],
      ["../../components/v2/BotaoInteracao/BotaoInteracao", padrao("BotaoInteracao")],
      ["../../components/v2/BotaoLink/BotaoLink", padrao("BotaoLink")],
      ["../../components/v2/CartaoIndicador/CartaoIndicador", padrao("CartaoIndicador")],
      ["../../components/v2/EstadoVazio/EstadoVazio", padrao(UI.indisponivel)],
      ["../../components/v2/SeletorOpcoes/SeletorOpcoes", padrao(UI.periodo)],
      ["../../components/v2/InputPeriodo/InputPeriodo", padrao(UI.intervalo)],
      [
        "../../components/v2/ResumoFaturamento/ResumoFaturamento",
        { ...padrao(UI.resumo), DetalhesFaturamento: UI.detalhes },
      ],
      [
        "../dashboard/dashboardRefresh",
        {
          iniciarAtualizacaoDashboard({ atualizar }) {
            const monitor = { atualizar, encerrado: false };
            monitores.push(monitor);
            return () => {
              monitor.encerrado = true;
            };
          },
        },
      ],
    ]),
  });
  const encontrar = (type) => elements(harness.tree).find((elemento) => elemento.type === type);
  async function concluir(
    lote,
    resumo,
    { falharResumo = false, falharGraficoProdutos = false } = {},
  ) {
    for (const consulta of lote) {
      if (consulta.url === "/dashboard/resumo") {
        if (falharResumo) consulta.rejeitar(new Error("Resumo indisponivel"));
        else consulta.resolver({ data: resumo });
      } else if (
        falharGraficoProdutos &&
        ["/dashboard/entradas-saidas", "/dashboard/top-produtos"].includes(consulta.url)
      ) {
        consulta.rejeitar(new Error("Bloco indisponivel"));
      } else if (consulta.url === "/dashboard/gerencial") {
        consulta.resolver({ data: createEmptyManagementMetrics() });
      } else if (consulta.url === "/dashboard/contas-vencidas") {
        consulta.resolver({ data: { contas_receber: [], contas_pagar: [] } });
      } else if (consulta.url === "/contas-bancarias/resumo/saldos") {
        consulta.resolver({ data: { total_geral: 500 } });
      } else consulta.resolver({ data: [] });
    }
    await harness.settle();
  }
  async function atualizarAutomaticamente() {
    const inicio = consultas.length;
    await harness.act(() => {
      void monitores.at(-1).atualizar();
    });
    return consultas.slice(inicio);
  }
  async function selecionarPeriodo(dias) {
    const inicio = consultas.length;
    await harness.act(() => encontrar(UI.periodo).props.aoSelecionar(dias));
    return consultas.slice(inicio);
  }
  async function editarIntervalo(inicio, fim) {
    await harness.act(() => encontrar(UI.intervalo).props.onChange({ inicio, fim }));
  }
  async function aplicarIntervalo() {
    const inicio = consultas.length;
    const aplicar = elements(harness.tree).find(
      (elemento) =>
        elemento.type === "BotaoInteracao" && elementText(elemento) === "Aplicar período",
    );
    await harness.act(() => aplicar.props.onClick());
    return consultas.slice(inicio);
  }
  const horario = () => elementText(harness.tree).match(/Atualizado às\s+(\d{2}:\d{2})/)?.[1];
  function conferirIndisponivel() {
    assert.equal(encontrar(UI.resumo), undefined, "Nao deve apresentar faturamento antigo ou zero");
    assert.equal(encontrar(UI.detalhes), undefined);
    assert.equal(
      encontrar(UI.indisponivel)?.props.titulo,
      "Não foi possível carregar o resultado do período",
    );
    assert.equal(horario(), undefined);
  }
  return {
    harness,
    consultas,
    navegacoes,
    monitores,
    encontrar,
    concluir,
    atualizarAutomaticamente,
    selecionarPeriodo,
    editarIntervalo,
    aplicarIntervalo,
    horario,
    conferirIndisponivel,
    avancarMinuto() {
      agora += 60000;
    },
  };
}

test("atualizacao automatica renova vendas e pagamentos com tres GET sem recolher detalhes", async () => {
  const caso = preparar();
  assert.equal(caso.consultas.length, 6);
  await caso.concluir(caso.consultas.slice(), respostaResumo(100, [1]));
  await caso.harness.act(() => caso.encontrar(UI.resumo).props.aoAlternarDetalhes());
  assert.equal(caso.encontrar(UI.resumo).props.expandido, true);
  assert.equal(caso.encontrar(UI.detalhes).props.mostrarTotaisPorForma, true);
  assert.deepEqual(caso.encontrar(UI.detalhes).props.composicao.formas_pagamento, [
    { forma_pagamento: "Pix", total: 100 },
  ]);
  assert.deepEqual(
    caso.encontrar(UI.detalhes).props.composicao.detalhes.map((v) => v.venda_id),
    [1],
  );
  const antes = caso.horario();
  caso.avancarMinuto();
  const automaticas = await caso.atualizarAutomaticamente();
  assert.deepEqual(automaticas.map((consulta) => consulta.url).sort(), [
    "/dashboard/entradas-saidas",
    "/dashboard/resumo",
    "/dashboard/top-produtos",
  ]);
  assert.ok(automaticas.every((consulta) => consulta.config.params.periodo_dias === 30));
  assert.equal((await caso.atualizarAutomaticamente()).length, 0, "Consulta pendente nao sobrepoe");
  const atual = respostaResumo(
    125,
    [1, 2],
    [
      { forma_pagamento: "Pix", total: 100 },
      { forma_pagamento: "Cartão de débito", total: 25 },
    ],
  );
  await caso.concluir(automaticas, atual);
  const cartao = caso.encontrar(UI.resumo);
  const detalhes = caso.encontrar(UI.detalhes);
  assert.equal(cartao.props.expandido, true);
  assert.equal(cartao.props.composicao, atual.composicao_vendas);
  assert.equal(detalhes.props.composicao, atual.composicao_vendas);
  assert.deepEqual(detalhes.props.composicao.formas_pagamento, [
    { forma_pagamento: "Pix", total: 100 },
    { forma_pagamento: "Cartão de débito", total: 25 },
  ]);
  assert.deepEqual(
    detalhes.props.composicao.detalhes.map((v) => v.venda_id),
    [1, 2],
  );
  assert.equal(detalhes.props.composicao.detalhes[1].pagamentos[0].forma_pagamento, "PIX");
  assert.notEqual(caso.horario(), antes);
});

test("falha do resumo no mesmo periodo preserva valores e horario da ultima carga valida", async () => {
  const caso = preparar();
  const valido = respostaResumo(180, [7]);
  await caso.concluir(caso.consultas.slice(), valido);
  await caso.harness.act(() => caso.encontrar(UI.resumo).props.aoAlternarDetalhes());
  const antes = caso.horario();
  assert.ok(antes);
  caso.avancarMinuto();
  const automaticas = await caso.atualizarAutomaticamente();
  await caso.concluir(automaticas, null, { falharResumo: true });
  assert.equal(caso.encontrar(UI.resumo).props.composicao, valido.composicao_vendas);
  assert.deepEqual(caso.encontrar(UI.detalhes).props.composicao.formas_pagamento, [
    { forma_pagamento: "Pix", total: 180 },
  ]);
  assert.equal(caso.horario(), antes);
  assert.match(elementText(caso.harness.tree), /resumo financeiro/);
});

test("mudar periodo e falhar mostra indisponibilidade em vez de vendas antigas ou zeros", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  const novas = await caso.selecionarPeriodo(1);
  assert.equal(novas.length, 6);
  assert.ok(
    novas
      .filter((c) => c.config.params?.periodo_dias)
      .every((c) => c.config.params.periodo_dias === 1),
  );
  await caso.concluir(novas, null, { falharResumo: true });
  assert.equal(caso.encontrar(UI.periodo).props.valorSelecionado, 1);
  caso.conferirIndisponivel();
});

test("30 dias validos, hoje indisponivel e retorno a 30 com falha nao recupera estado antigo", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  const hoje = await caso.selecionarPeriodo(1);
  await caso.concluir(hoje, null, { falharResumo: true });
  caso.conferirIndisponivel();
  const retorno = await caso.selecionarPeriodo(30);
  await caso.concluir(retorno, null, { falharResumo: true });
  assert.equal(caso.encontrar(UI.periodo).props.valorSelecionado, 30);
  caso.conferirIndisponivel();
});

test("resposta antiga mesmo entregue apos abort nao substitui o periodo novo", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  const antigas = await caso.atualizarAutomaticamente();
  assert.equal(antigas.length, 3);
  const monitorAntigo = caso.monitores.at(-1);
  const novas = await caso.selecionarPeriodo(1);
  assert.equal(monitorAntigo.encerrado, true);
  assert.ok(antigas.every((consulta) => consulta.config.signal.aborted));
  assert.ok(novas.every((consulta) => !consulta.config.signal.aborted));
  const atual = respostaResumo(201, [11]);
  await caso.concluir(novas, atual);
  const horarioAtual = caso.horario();
  caso.avancarMinuto();
  await caso.concluir(antigas, respostaResumo(999, [99]));
  assert.equal(caso.encontrar(UI.periodo).props.valorSelecionado, 1);
  assert.equal(caso.encontrar(UI.resumo).props.composicao, atual.composicao_vendas);
  assert.deepEqual(
    caso.encontrar(UI.resumo).props.composicao.detalhes.map((v) => v.venda_id),
    [11],
  );
  assert.equal(caso.horario(), horarioAtual);
});

test("rascunho e calendario incompleto nao consultam; aplicar usa as mesmas datas nos tres blocos", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  const antes = caso.consultas.length;
  assert.equal((await caso.selecionarPeriodo("personalizado")).length, 0);
  await caso.editarIntervalo("2026-10-01", "");
  assert.equal(caso.consultas.length, antes);
  assert.equal((await caso.aplicarIntervalo()).length, 0);
  assert.match(caso.encontrar(UI.intervalo).props.error, /data inicial e a data final/);
  assert.equal(caso.encontrar(UI.resumo).props.composicao.faturamento_liquido, 300);
  await caso.editarIntervalo("2026-10-01", "2026-10-07");
  assert.equal(caso.consultas.length, antes);
  const novas = await caso.aplicarIntervalo();
  assert.equal(novas.length, 6);
  const comerciais = novas.filter(
    (c) => c.url !== "/dashboard/gerencial" && c.config.params?.data_inicio,
  );
  assert.equal(comerciais.length, 3);
  for (const consulta of comerciais) {
    assert.equal(consulta.config.params.data_inicio, "2026-10-01");
    assert.equal(consulta.config.params.data_fim, "2026-10-07");
    assert.equal(consulta.config.params.periodo_dias, undefined);
  }
  await caso.concluir(novas, respostaResumo(107, [107]));
  assert.equal(caso.encontrar(UI.resumo).props.periodo, "01/10/2026 a 07/10/2026");
  assert.equal(caso.encontrar(UI.periodo).props.valorSelecionado, "personalizado");
  assert.equal(
    (await caso.aplicarIntervalo()).length,
    0,
    "Reaplicar o mesmo intervalo nao duplica GET",
  );
});

test("validacao bloqueia datas invertidas, invalidas e 91 dias, e aceita 90 inclusivos", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  await caso.selecionarPeriodo("personalizado");
  for (const [inicio, fim, mensagem] of [
    ["2026-10-08", "2026-10-07", /posterior/],
    ["2026-02-30", "2026-03-07", /datas válidas/],
    ["2026-07-24", "2026-10-22", /até 90 dias/],
  ]) {
    await caso.editarIntervalo(inicio, fim);
    assert.equal((await caso.aplicarIntervalo()).length, 0);
    assert.match(caso.encontrar(UI.intervalo).props.error, mensagem);
  }
  await caso.editarIntervalo("2026-07-25", "2026-10-22");
  const validas = await caso.aplicarIntervalo();
  assert.equal(validas.length, 6);
  await caso.concluir(validas, respostaResumo(90, [90]));
  assert.equal(caso.encontrar(UI.resumo).props.periodo, "25/07/2026 a 22/10/2026");
});

test("intervalos com igual numero de dias descartam respostas antigas e preservam datas no auto refresh", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  await caso.selecionarPeriodo("personalizado");
  await caso.editarIntervalo("2026-10-01", "2026-10-07");
  await caso.concluir(await caso.aplicarIntervalo(), respostaResumo(107, [107]));
  await caso.harness.act(() => caso.encontrar(UI.resumo).props.aoAlternarDetalhes());
  const antigas = await caso.atualizarAutomaticamente();
  const monitorAntigo = caso.monitores.at(-1);
  await caso.editarIntervalo("2026-10-08", "2026-10-14");
  assert.equal(caso.consultas.at(-1), antigas.at(-1), "Alterar rascunho nao faz GET");
  const novas = await caso.aplicarIntervalo();
  assert.equal(monitorAntigo.encerrado, true);
  assert.ok(antigas.every((consulta) => consulta.config.signal.aborted));
  const atual = respostaResumo(814, [814]);
  await caso.concluir(novas, atual);
  await caso.concluir(antigas, respostaResumo(999, [999]));
  assert.equal(caso.encontrar(UI.resumo).props.composicao, atual.composicao_vendas);
  assert.equal(caso.encontrar(UI.resumo).props.periodo, "08/10/2026 a 14/10/2026");
  const automaticas = await caso.atualizarAutomaticamente();
  assert.equal(automaticas.length, 3);
  assert.ok(automaticas.every((c) => c.config.params.data_inicio === "2026-10-08"));
  assert.ok(automaticas.every((c) => c.config.params.data_fim === "2026-10-14"));
  await caso.concluir(automaticas, respostaResumo(815, [814, 815]));
  assert.equal(caso.encontrar(UI.resumo).props.expandido, true);
  assert.equal(caso.encontrar(UI.detalhes).props.composicao.faturamento_liquido, 815);
  assert.equal(caso.encontrar(UI.intervalo).props.value.inicio, "2026-10-08");
});

test("falha em novo intervalo nao reaproveita vendas, fluxo ou produtos de outro intervalo", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  await caso.selecionarPeriodo("personalizado");
  await caso.editarIntervalo("2026-09-01", "2026-09-07");
  const novas = await caso.aplicarIntervalo();
  await caso.concluir(novas, null, { falharResumo: true });
  caso.conferirIndisponivel();
  assert.equal(caso.encontrar(UI.intervalo).props.value.inicio, "2026-09-01");
  const retry = await caso.atualizarAutomaticamente();
  assert.ok(retry.every((c) => c.config.params.data_inicio === "2026-09-01"));
  await caso.concluir(retry, respostaResumo(97, [97]));
  assert.equal(caso.encontrar(UI.resumo).props.composicao.faturamento_liquido, 97);
});

test("grafico e ranking que falham no novo intervalo mostram indisponibilidade ate uma leitura valida", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  await caso.selecionarPeriodo("personalizado");
  await caso.editarIntervalo("2026-09-01", "2026-09-07");
  await caso.concluir(await caso.aplicarIntervalo(), respostaResumo(97, [97]), {
    falharGraficoProdutos: true,
  });
  const titulos = () => elements(caso.harness.tree).map((el) => el.props?.titulo);
  assert.ok(titulos().includes("Fluxo diário indisponível neste período"));
  assert.ok(titulos().includes("Produtos indisponíveis neste período"));
  assert.ok(!titulos().includes("Sem movimento neste período"));
  assert.ok(!titulos().includes("Sem produtos vendidos no período"));
  await caso.concluir(await caso.atualizarAutomaticamente(), respostaResumo(97, [97]));
  assert.ok(titulos().includes("Sem movimento neste período"));
  assert.ok(titulos().includes("Sem produtos vendidos no período"));
});

test("links de relatorios e assistente recebem o intervalo aplicado, mesmo com outro rascunho", async () => {
  const caso = preparar();
  await caso.concluir(caso.consultas.slice(), respostaResumo(300, [30]));
  await caso.selecionarPeriodo("personalizado");
  await caso.editarIntervalo("2026-10-01", "2026-10-07");
  await caso.concluir(await caso.aplicarIntervalo(), respostaResumo(107, [107]));
  await caso.editarIntervalo("2026-10-08", "2026-10-14");
  await caso.harness.act(() => {
    elements(caso.harness.tree)
      .find((el) => el.props?.titulo === "Pedidos / unidades")
      .props.aoClicar();
  });
  assert.equal(
    caso.navegacoes.at(-1)[0],
    "/financeiro/vendas?data_inicio=2026-10-01&data_fim=2026-10-07",
  );
  await caso.harness.act(() => {
    elements(caso.harness.tree)
      .find((el) => el.props?.titulo === "Resultado de caixa")
      .props.aoClicar();
  });
  assert.equal(
    caso.navegacoes.at(-1)[0],
    "/financeiro/fluxo-caixa?data_inicio=2026-10-01&data_fim=2026-10-07",
  );
  await caso.harness.act(() => {
    elements(caso.harness.tree)
      .find((el) => elementText(el) === "Analisar com IA")
      .props.onClick();
  });
  assert.match(caso.navegacoes.at(-1)[1].state.perguntaInicial, /01\/10\/2026 a 07\/10\/2026/);
  assert.doesNotMatch(caso.navegacoes.at(-1)[1].state.perguntaInicial, /últimos/);
  const presets = await caso.selecionarPeriodo(7);
  assert.equal(presets.length, 6);
  assert.equal(caso.encontrar(UI.intervalo), undefined);
  assert.ok(
    presets
      .filter((c) => c.config.params?.periodo_dias)
      .every((c) => c.config.params.periodo_dias === 7),
  );
});
