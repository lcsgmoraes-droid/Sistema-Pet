import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../../scripts/helpers/reactControllerHarness.mjs";

const caminho = fileURLToPath(new URL("./ResumoFaturamento.jsx", import.meta.url));
const mocks = new Map([
  [
    "lucide-react",
    {
      ChevronDown: "ChevronDown",
      ChevronUp: "ChevronUp",
      TrendingUp: "TrendingUp",
      ExternalLink: "ExternalLink",
      AlertTriangle: "AlertTriangle",
    },
  ],
  ["../BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
  ["../BotaoLink/BotaoLink", { __esModule: true, default: "BotaoLink" }],
  ["../CartaoIndicador/CartaoIndicador", { __esModule: true, default: "CartaoIndicador" }],
]);

const composicao = (extra = {}) => ({
  quantidade: 2,
  valor_pago: 150,
  formas_pagamento: [
    { forma_pagamento: "Cartão de crédito", total: 100, quantidade: 1 },
    { forma_pagamento: "Pix", total: 50, quantidade: 1 },
  ],
  total_formas_pagamento: 150,
  ajustes_formas_pagamento: 0,
  creditos_utilizados: 15,
  crediario_receber: 20,
  detalhes: [],
  ...extra,
});

function preparar(dados, exportName = "TotaisFormasPagamento", props = {}, globals = {}) {
  return createControllerHarness(caminho, {
    exportName,
    mocks,
    props: { composicao: dados, ...props },
    globals,
  });
}

function linhas(tree) {
  return elements(tree)
    .filter((node) => node.type === "div" && node.props.children?.[0]?.type === "dt")
    .map((node) => node.props.children.map((child) => elementText(child).trim()));
}

test("mostra formas normalizadas pelo servidor e o total pago, sem incluir benefícios ou crediário", () => {
  const env = preparar(composicao());
  assert.deepEqual(linhas(env.tree), [
    ["Cartão de crédito", "R$ 100,00"],
    ["Pix", "R$ 50,00"],
    ["Total aplicado às vendas", "R$ 150,00"],
  ]);
  const texto = elementText(env.tree);
  assert.match(texto, /Pagamentos das vendas do período/);
  assert.match(texto, /mesmas vendas deste indicador/);
  assert.match(texto, /outras datas ou\s+caixas/);
  assert.doesNotMatch(texto, /R\$ 15,00|R\$ 20,00/);
  assert.doesNotMatch(texto, /Ajustes não atribuídos a uma forma/);
});

test("novos totais da API substituem o retrato anterior sem recalcular pelas vendas", async () => {
  const env = preparar(composicao());
  await env.update({
    composicao: composicao({
      valor_pago: 225,
      total_formas_pagamento: 225,
      formas_pagamento: [
        { forma_pagamento: "Cartão de crédito", total: 100, quantidade: 1 },
        { forma_pagamento: "Pix", total: 125, quantidade: 3 },
      ],
    }),
  });
  assert.deepEqual(linhas(env.tree), [
    ["Cartão de crédito", "R$ 100,00"],
    ["Pix", "R$ 125,00"],
    ["Total aplicado às vendas", "R$ 225,00"],
  ]);
});

test("ajustes assinados ficam separados e o total continua sendo o valor oficial da API", () => {
  for (const [ajuste, pago, exibido] of [
    [-20, 130, "R$ -20,00"],
    [10, 160, "R$ 10,00"],
  ]) {
    const env = preparar(composicao({ ajustes_formas_pagamento: ajuste, valor_pago: pago }));
    assert.deepEqual(linhas(env.tree).slice(-2), [
      ["Diferença entre pagamentos e valor das vendas", exibido],
      ["Total aplicado às vendas", `R$ ${pago},00`],
    ]);
    assert.match(elementText(env.tree), /O histórico preserva os pagamentos registrados/);
    assert.match(elementText(env.tree), /não criam lançamentos financeiros/);
  }
});

test("ausência do contrato agregado mostra indisponibilidade, inclusive quando pago é zero", () => {
  for (const dados of [
    null,
    { valor_pago: 0 },
    composicao({ formas_pagamento: undefined }),
    composicao({ ajustes_formas_pagamento: undefined }),
  ]) {
    const env = preparar(dados);
    assert.match(elementText(env.tree), /totais por forma de pagamento estão indisponíveis/);
    assert.deepEqual(linhas(env.tree), []);
    assert.doesNotMatch(elementText(env.tree), /Nenhum pagamento registrado/);
  }
});

test("array vazio e total zero mostram ausência de pagamentos confirmada pela API", () => {
  const env = preparar(
    composicao({ formas_pagamento: [], valor_pago: 0, total_formas_pagamento: 0 }),
  );
  assert.match(elementText(env.tree), /Nenhum pagamento registrado para as vendas do período/);
  assert.deepEqual(linhas(env.tree), [["Total aplicado às vendas", "R$ 0,00"]]);
  assert.doesNotMatch(elementText(env.tree), /indisponíveis/);
});

test("pagamento legado sem forma não é apresentado como ausência de pagamentos", () => {
  const env = preparar(
    composicao({
      formas_pagamento: [],
      valor_pago: 40,
      total_formas_pagamento: 0,
      ajustes_formas_pagamento: 40,
    }),
  );
  assert.deepEqual(linhas(env.tree), [
    ["Pagamentos registrados", "R$ 0,00"],
    ["Diferença entre pagamentos e valor das vendas", "R$ 40,00"],
    ["Total aplicado às vendas", "R$ 40,00"],
  ]);
  assert.doesNotMatch(elementText(env.tree), /Nenhum pagamento registrado/);
});

const origemCredito = {
  venda_id: 42,
  numero_venda: "202610220021",
  data_venda: "2026-10-22T13:00:00",
  valor_pago: 109.9,
  total_vendas: 109.9,
  descontos: 10,
  devolucoes: 0,
  total_pagamentos_registrados: 119.9,
  diferenca: -10,
  formas_pagamento: [{ forma_pagamento: "Cartão de crédito", total: 119.9, quantidade: 1 }],
  motivo: "pagamento_acima_total_venda",
};
const casoCredito = () =>
  composicao({
    quantidade: 1,
    valor_pago: 109.9,
    total_formas_pagamento: 119.9,
    formas_pagamento: origemCredito.formas_pagamento,
    ajustes_formas_pagamento: -10,
    diferencas_pagamentos: [origemCredito],
    resumo_diferencas_pagamentos: [{ motivo: origemCredito.motivo, diferenca: -10, quantidade: 1 }],
    detalhes: [{ ...origemCredito, faturamento_liquido: 109.9, pagamentos: [] }],
  });

test("excesso de crédito tem origem na venda, forma e desconto, sem presumir estorno", async () => {
  const aberturas = [];
  const env = preparar(
    casoCredito(),
    "TotaisFormasPagamento",
    {},
    {
      window: { open: (...args) => aberturas.push(args) },
    },
  );
  assert.deepEqual(linhas(env.tree), [
    ["Cartão de crédito", "R$ 119,90"],
    ["Pagamentos registrados", "R$ 119,90"],
    ["Pagamentos acima do valor aplicado às vendas", "R$ -10,00"],
    ["Total aplicado às vendas", "R$ 109,90"],
  ]);
  assert.doesNotMatch(elementText(env.tree), /não atribuídos|estorno no cartão/);
  assert.equal(elements(env.tree).filter((node) => node.type === "article").length, 0);
  await env.act(() =>
    elements(env.tree)
      .find((node) => node.type === "BotaoInteracao")
      .props.onClick(),
  );
  const texto = elementText(env.tree);
  assert.match(texto, /202610220021/);
  assert.match(texto, /Descontos da venda:\s+R\$ 10,00/);
  assert.match(texto, /Cartão de crédito\s*:\s+R\$ 119,90/);
  await env.act(() =>
    elements(env.tree)
      .find((node) => elementText(node) === "Corrigir")
      .props.onClick(),
  );
  assert.deepEqual(aberturas, [["/pdv?venda=42", "_blank", "noopener,noreferrer"]]);
  await env.update({ composicao: composicao() });
  assert.doesNotMatch(elementText(env.tree), /202610220021|Ver origem das diferenças/);
});

test("devolução preserva forma original e orienta consultar restituição, sem tratar como erro", async () => {
  const origem = { ...origemCredito, motivo: "devolucao", descontos: 0, devolucoes: 10 };
  const env = preparar(
    composicao({
      ajustes_formas_pagamento: -10,
      diferencas_pagamentos: [origem],
      resumo_diferencas_pagamentos: [{ motivo: "devolucao", diferenca: -10, quantidade: 1 }],
    }),
  );
  assert.match(elementText(env.tree), /Devoluções consideradas nas vendas/);
  await env.act(() =>
    elements(env.tree)
      .find((node) => node.type === "BotaoInteracao")
      .props.onClick(),
  );
  assert.match(elementText(env.tree), /formas acima são dos pagamentos originais/);
  assert.ok(elements(env.tree).find((node) => elementText(node) === "Consultar venda"));
  assert.equal(
    elements(env.tree).find((node) => elementText(node) === "Corrigir"),
    undefined,
  );
});

test("dashboard e caixa destacam a venda e filtram pendências fora das primeiras 20", async () => {
  const dados = casoCredito();
  dados.detalhes = [
    ...Array.from({ length: 20 }, (_, indice) => ({ venda_id: 100 + indice, pagamentos: [] })),
    dados.detalhes[0],
  ];
  dados.quantidade = 21;
  for (const mostrarTotaisPorForma of [false, true]) {
    const env = preparar(dados, "DetalhesFaturamento", { mostrarTotaisPorForma });
    const contagem = elements(env.tree).find(
      (node) =>
        node.type === "p" && elementText(node).includes("venda(s) com pagamento a conferir"),
    );
    assert.equal(contagem.props.children[0], 1);
    await env.act(() =>
      elements(env.tree)
        .find(
          (node) =>
            node.type === "BotaoInteracao" && elementText(node) === "Ver pagamentos a conferir",
        )
        .props.onClick(),
    );
    assert.equal(elements(env.tree).filter((node) => node.type === "article").length, 1);
    const aviso = elements(env.tree).find((node) => node.type?.name === "AvisoPagamentoVenda");
    assert.equal(aviso.props.venda.venda_id, 42);
    assert.equal(aviso.props.diferenca, origemCredito);
    const artigo = elements(env.tree).find((node) => node.type === "article");
    assert.match(artigo.props.className, /amber/);
    await env.update({ composicao: composicao() });
    assert.match(elementText(env.tree), /Nenhum pagamento a conferir nesta seleção/);
    assert.ok(elements(env.tree).find((node) => elementText(node) === "Ver todas as vendas"));
  }
});

test("aviso abre somente consulta em outra aba e distingue legado de devolução normal", async () => {
  const caminhoAviso = fileURLToPath(new URL("./AvisoPagamentoVenda.jsx", import.meta.url));
  const aberturas = [];
  const props = { venda: { ...origemCredito, pagamentos: [] }, diferenca: origemCredito };
  const env = createControllerHarness(caminhoAviso, {
    mocks,
    props,
    globals: { window: { open: (...args) => aberturas.push(args) } },
  });
  assert.match(elementText(env.tree), /Conferir pagamento/);
  assert.match(elementText(env.tree), /pagamentos registrados estão acima do valor aplicado/);
  await env.act(() =>
    elements(env.tree)
      .find((node) => node.type === "BotaoInteracao")
      .props.onClick(),
  );
  assert.deepEqual(aberturas, [["/pdv?venda=42", "_blank", "noopener,noreferrer"]]);
  await env.update({ diferenca: { ...origemCredito, motivo: "devolucao" } });
  assert.equal(env.tree, null);
  await env.update({
    diferenca: null,
    venda: {
      venda_id: 42,
      pagamentos: [
        {
          origem: "venda_legada",
          forma_pagamento: "Quitação legada pelo status da venda",
        },
      ],
    },
  });
  assert.match(elementText(env.tree), /considerada quitada pelo status/);
  assert.match(elementText(env.tree), /sem histórico detalhado/);
  await env.update({
    venda: { venda_id: "42?invalido", pagamentos: props.venda.pagamentos },
    diferenca: origemCredito,
  });
  assert.equal(
    elements(env.tree).find((node) => node.type === "BotaoInteracao"),
    undefined,
  );
});

test("totais abrangem o agregado completo mesmo com a lista limitada às primeiras 20 vendas", async () => {
  const dados = composicao({
    quantidade: 21,
    valor_pago: 1120,
    total_formas_pagamento: 1120,
    formas_pagamento: [{ forma_pagamento: "Pix", total: 1120, quantidade: 21 }],
    detalhes: Array.from({ length: 21 }, (_, indice) => ({
      venda_id: indice + 1,
      valor_pago: indice === 20 ? 1100 : 1,
      pagamentos: [],
    })),
  });
  const env = preparar(dados, "DetalhesFaturamento", { mostrarTotaisPorForma: true });
  const slot = elements(env.tree).find((node) => node.type?.name === "TotaisFormasPagamento");
  assert.equal(slot.props.composicao, dados);
  assert.equal(elements(env.tree).filter((node) => node.type === "article").length, 20);
  assert.deepEqual(linhas(preparar(slot.props.composicao).tree), [
    ["Pix", "R$ 1.120,00"],
    ["Total aplicado às vendas", "R$ 1.120,00"],
  ]);
  const nodes = elements(env.tree);
  assert.ok(nodes.indexOf(slot) < nodes.findIndex((node) => node.type === "article"));
  await env.act(() =>
    elements(env.tree)
      .find((node) => node.type === "BotaoInteracao")
      .props.onClick(),
  );
  assert.equal(elements(env.tree).filter((node) => node.type === "article").length, 21);
  assert.equal(
    elements(env.tree).find((node) => node.type?.name === "TotaisFormasPagamento").props.composicao,
    dados,
  );
});

test("bloco é opt-in nos detalhes e a prop atravessa o resumo sem afetar caixa ou auditoria", () => {
  const dados = composicao();
  const detalhes = preparar(dados, "DetalhesFaturamento");
  assert.equal(
    elements(detalhes.tree).find((node) => node.type?.name === "TotaisFormasPagamento"),
    undefined,
  );
  for (const mostrarTotaisPorForma of [false, true]) {
    const resumo = preparar(dados, "default", { expandido: true, mostrarTotaisPorForma });
    const slot = elements(resumo.tree).find((node) => node.type?.name === "DetalhesFaturamento");
    assert.equal(slot.props.mostrarTotaisPorForma, mostrarTotaisPorForma);
  }
});
