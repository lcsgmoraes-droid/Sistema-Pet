import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const dashboardPath = path.join(root, "src/pages/DashboardFinanceiro.jsx");
const cardsPath = path.join(root, "src/pages/dashboard/DashboardCards.jsx");
const dashboardSource = fs.readFileSync(dashboardPath, "utf8");
const cardsSource = fs.readFileSync(cardsPath, "utf8");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

for (const label of ["Pedidos / unidades", "Lucro das vendas"]) {
  assert(dashboardSource.includes(`label="${label}"`), `Card principal ausente: ${label}`);
}

assert(
  dashboardSource.includes('label={porRecebimento ? "Recebimentos de vendas" : "Faturamento"}'),
  "Indicador principal deve acompanhar a visão da empresa, preservando Faturamento no padrão",
);

assert(
  dashboardSource.includes('onClick={() => navigate("/financeiro/dre")}'),
  "Lucro das vendas deve abrir o detalhamento da DRE",
);
assert(
  dashboardSource.includes('label="Pagamentos que vencem hoje"'),
  "Dashboard deve separar pagamentos que vencem hoje",
);
assert(
  !dashboardSource.includes("Visão geral do negócio"),
  "Cabecalho alto antigo deve sair da abertura do dashboard",
);
assert(cardsSource.includes("CompactMetricCard"), "Cards secundarios devem usar formato compacto");

console.log("Dashboard executive layout contract OK");
