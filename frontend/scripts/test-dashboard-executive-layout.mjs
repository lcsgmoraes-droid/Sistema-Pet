import assert from "node:assert/strict";
import fs from "node:fs";

const dashboard = fs.readFileSync("src/pages/v2/DashboardFinanceiro.jsx", "utf8");
const revenue = fs.readFileSync(
  "src/components/v2/ResumoFaturamento/ResumoFaturamento.jsx",
  "utf8",
);
for (const title of ["Pedidos / unidades", "Lucro das vendas", "Pagamentos que vencem hoje"]) {
  assert.ok(dashboard.includes(`titulo="${title}"`), `Indicador ausente: ${title}`);
}
assert.ok(dashboard.includes("<ResumoFaturamento"));
assert.ok(dashboard.includes("summary?.composicao_vendas"));
assert.ok(dashboard.includes("mostrarDetalhes={false}"));
assert.ok(!dashboard.includes("DetalhesFaturamento"));
assert.ok(
  !dashboard.includes("summary?.indicador_comercial"),
  "Faturamento não pode alternar para recebimentos/bruto",
);
assert.ok(revenue.includes('titulo = "Faturamento líquido"'));
assert.ok(revenue.includes("composicao.faturamento_liquido"));
assert.ok(revenue.includes("aria-expanded={expandidoAtual}"));
assert.ok(dashboard.includes('navigate("/financeiro/dre")'));
console.log("Dashboard executivo usa faturamento líquido, sem detalhamento de caixa.");
