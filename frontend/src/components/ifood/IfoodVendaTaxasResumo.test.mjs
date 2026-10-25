import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";
import {
  calcularTotalizadoresListaVendasFinanceiro,
  calcularAnaliseInteligenteVendas,
  COLUNAS_RELATORIO_VENDAS,
  montarCardsTotalizadoresListaVendasFinanceiro,
  montarLinhasCobrancasIfoodExcel,
} from "../financeiro/vendasFinanceiroUtils.js";

const parcial = {
  charges: [
    {
      code: "ORDER_COMMISSION",
      label: "Comissão iFood",
      amount: 7.8,
      status: "known",
      source: "ifood_financial_events",
    },
  ],
  pending_components: [
    {
      code: "PAYMENT_TRANSACTION_FEE",
      label: "Taxa de pagamento iFood",
      reason: "Ainda não recebida",
    },
  ],
  complete: false,
  simulated: false,
  fee_known_total: 7.8,
  fee_total: null,
  checkout: { delivery_fee: 8.9, ifood_service_fee: 1.99 },
};

function render(financeiro, extra = {}) {
  return createControllerHarness(
    fileURLToPath(new URL("./IfoodVendaTaxasResumo.jsx", import.meta.url)),
    {
      props: { financeiro, ...extra },
      mocks: new Map(),
    },
  );
}

test("taxa conhecida permanece visível e apenas componente ausente fica pendente", async () => {
  const harness = render(parcial);
  assert.equal(harness.tree.props.style.maxWidth, "min(56rem, calc(100vw - 4rem))");
  assert.match(harness.tree.props.className, /w-full/);
  let text = elementText(harness.tree);
  assert.match(text, /Comissão iFood/);
  assert.match(text, /R\$\s*7,80/);
  assert.match(text, /Taxa de pagamento iFood/);
  assert.match(text, /Aguardando Financial/);
  assert.match(text, /Frete cobrado do cliente:.*8,90/s);
  assert.match(text, /Serviço iFood pago pelo consumidor:.*1,99/s);
  assert.doesNotMatch(text, /R\$\s*0,00/);
  await harness.update({
    financeiro: {
      ...parcial,
      complete: true,
      fee_total: 7.8,
      pending_components: [],
      charges: [
        ...parcial.charges,
        {
          code: "PAYMENT_TRANSACTION_FEE",
          label: "Taxa de pagamento iFood",
          amount: 0,
          status: "known",
        },
      ],
    },
  });
  text = elementText(harness.tree);
  assert.match(text, /R\$\s*0,00/);
  assert.match(text, /Cobranças recebidas/);
  assert.doesNotMatch(text, /Aguardando Financial|Apuração parcial/);
  assert.match(text, /não comprovam.*repasse entrou no banco/s);
});

test("totalizador preserva e identifica subtotal conhecido sem tratá-lo como taxa completa", () => {
  const totais = calcularTotalizadoresListaVendasFinanceiro([
    { taxa_ifood: 6.5, taxa_cartao: 0, ifood_financial: parcial, taxas_ifood_pendentes: true },
    {
      taxa_ifood: null,
      taxa_cartao: null,
      ifood_financial: { charges: [] },
      taxas_ifood_pendentes: true,
    },
  ]);
  assert.equal(totais.taxa_ifood, null);
  assert.equal(totais.taxa_ifood_conhecida, 6.5);
  assert.equal(totais.taxa_cartao, null);
  assert.equal(totais.taxa_cartao_conhecida, 0);
  const cards = montarCardsTotalizadoresListaVendasFinanceiro(totais);
  assert.match(
    cards.find((card) => card.label === "Taxas iFood").value,
    /6,50.*subtotal conhecido.*pendente/,
  );
  assert.match(
    cards.find((card) => card.label === "Tx. Pagto").value,
    /0,00.*subtotal conhecido.*pendente/,
  );
  assert.equal(cards.find((card) => card.label === "Lucro").value, "Pendente iFood");
});

test("ranking apurado usa lucro após taxas e exclui valores incompletos sem voltar a receita menos CMV", () => {
  const antes = {
    nome: "SKU 018631.1",
    categoria: "Pet",
    quantidade: 1,
    valor_total: 65,
    custo_total: 40,
  };
  const concorrente = { nome: "Outro produto", quantidade: 1, valor_total: 62, custo_total: 40 };
  const legado = calcularAnaliseInteligenteVendas({ produtosAnalise: [antes, concorrente] });
  assert.equal(legado.produtosMaisLucrativos[0].nome, antes.nome);
  assert.equal(legado.produtosMaisLucrativos[0].lucro_total, 25);
  const apurada = calcularAnaliseInteligenteVendas({
    produtosAnalise: [
      { ...antes, rentabilidade_calculada: true, lucro_total: 18.5, valor_liquido_total: 58.5 },
      concorrente,
    ],
  });
  assert.equal(apurada.produtosMaisLucrativos[0].nome, concorrente.nome);
  const produto = apurada.produtosMaisLucrativos[1];
  assert.equal(produto.lucro_total, 18.5);
  assert.equal(produto.preco, 65);
  assert.equal(produto.margem, 46.25);
  assert.ok(produto.margem < legado.produtosMaisLucrativos[0].margem);
  const pendente = calcularAnaliseInteligenteVendas({
    produtosAnalise: [
      { ...antes, rentabilidade_calculada: true, lucro_total: null, valor_liquido_total: null },
    ],
  });
  assert.equal(pendente.produtosMaisLucrativos.length, 0);
  assert.equal(pendente.produtosPorCategoria.Pet.margem_media, null);
  assert.equal(pendente.alertasInteligentesVendas.length, 0);
});

test("simulação e valor não classificado continuam identificados, sem virar margem real", () => {
  const text = elementText(
    render({
      ...parcial,
      simulated: true,
      simulation_complete: true,
      charges: [
        {
          code: "EXTRA",
          label: "Cobrança adicional",
          amount: null,
          signed_amount: -4,
          status: "simulated",
          classification: "unclassified",
        },
      ],
    }).tree,
  );
  assert.match(text, /Simulação em DEV/);
  assert.match(text, /Valores fictícios/);
  assert.match(text, /Cobrança adicional/);
  assert.match(text, /R\$\s*-4,00/);
  assert.match(text, /Não classificado/);
  assert.match(text, /valor observado/);
  assert.doesNotMatch(text, /Cobranças recebidas|Total classificado até agora/);
});

test("ausência de cobrança não fabrica custo zero e painel não aparece nos outros canais", () => {
  assert.equal(render(null).tree, null);
  const text = elementText(render({ ...parcial, charges: [], fee_known_total: 0 }).tree);
  assert.match(text, /Nenhuma cobrança recebida/);
  assert.doesNotMatch(text, /Total classificado até agora|R\$\s*0,00/);
});

test("relatório e Excel preservam pagamento conhecido mesmo com comissão pendente", () => {
  const venda = {
    venda_bruta: 65,
    custo_produtos: 40,
    taxa_cartao: 0,
    taxa_ifood: null,
    lucro: null,
    venda_liquida: null,
    rentabilidade_status: "pending_ifood_financial",
    taxas_ifood_pendentes: true,
    ifood_financial: {
      ...parcial,
      charges: [
        {
          code: "PAYMENT_TRANSACTION_FEE",
          label: "Taxa de pagamento iFood",
          amount: 0,
          status: "known",
        },
      ],
      pending_components: [
        { code: "ORDER_COMMISSION", label: "Comissão iFood", reason: "Aguardando evento" },
      ],
    },
  };
  const totais = calcularTotalizadoresListaVendasFinanceiro([venda]);
  assert.equal(totais.taxa_cartao, 0);
  assert.equal(totais.taxa_ifood, null);
  assert.equal(totais.lucro, null);
  assert.equal(COLUNAS_RELATORIO_VENDAS.find((c) => c.key === "taxa_cartao").value(venda), 0);
  assert.equal(
    COLUNAS_RELATORIO_VENDAS.find((c) => c.key === "taxa_ifood").value(venda),
    "Pendente iFood",
  );
  const discriminadas = COLUNAS_RELATORIO_VENDAS.find((c) => c.key === "cobrancas_ifood").value(
    venda,
  );
  assert.match(discriminadas, /Taxa de pagamento iFood: R\$\s*0,00/);
  assert.match(
    COLUNAS_RELATORIO_VENDAS.find((c) => c.key === "pendencias_ifood").value(venda),
    /Comissão iFood: Aguardando evento/,
  );
  const simulada = COLUNAS_RELATORIO_VENDAS.find((c) => c.key === "cobrancas_ifood").value({
    ...venda,
    ifood_financial: { ...venda.ifood_financial, simulated: true },
  });
  assert.match(simulada, /^SIMULAÇÃO DEV/);
  const linhas = montarLinhasCobrancasIfoodExcel([venda]);
  assert.equal(linhas[1][1], "Taxa de pagamento iFood");
  assert.equal(linhas[1][2], 0);
  assert.equal(linhas[2][1], "Comissão iFood");
  assert.equal(linhas[2][2], "Aguardando Financial");
});
