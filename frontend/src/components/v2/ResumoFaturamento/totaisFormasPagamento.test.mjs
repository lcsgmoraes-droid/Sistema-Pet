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
    { ChevronDown: "ChevronDown", ChevronUp: "ChevronUp", TrendingUp: "TrendingUp" },
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

function preparar(dados, exportName = "TotaisFormasPagamento", props = {}) {
  return createControllerHarness(caminho, {
    exportName,
    mocks,
    props: { composicao: dados, ...props },
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
    ["Total pago", "R$ 150,00"],
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
    ["Total pago", "R$ 225,00"],
  ]);
});

test("ajustes assinados ficam separados e o total continua sendo o valor oficial da API", () => {
  for (const [ajuste, pago, exibido] of [
    [-20, 130, "R$ -20,00"],
    [10, 160, "R$ 10,00"],
  ]) {
    const env = preparar(composicao({ ajustes_formas_pagamento: ajuste, valor_pago: pago }));
    assert.deepEqual(linhas(env.tree).slice(-2), [
      ["Ajustes não atribuídos a uma forma", exibido],
      ["Total pago", `R$ ${pago},00`],
    ]);
    assert.match(elementText(env.tree), /Devoluções e diferenças entre os pagamentos registrados/);
    assert.match(elementText(env.tree), /quando a forma do ajuste não está identificada/);
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
  assert.deepEqual(linhas(env.tree), [["Total pago", "R$ 0,00"]]);
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
    ["Ajustes não atribuídos a uma forma", "R$ 40,00"],
    ["Total pago", "R$ 40,00"],
  ]);
  assert.doesNotMatch(elementText(env.tree), /Nenhum pagamento registrado/);
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
    ["Total pago", "R$ 1.120,00"],
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
