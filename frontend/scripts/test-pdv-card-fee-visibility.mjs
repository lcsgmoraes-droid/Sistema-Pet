import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const panelSource = readFileSync(
  new URL("../src/components/modalPagamento/ModalPagamentoFormaPanel.jsx", import.meta.url),
  "utf8",
);

for (const textoFinanceiro of [
  "Taxa:",
  "Taxa cadastrada:",
  "Recebimento previsto",
  "taxas configuradas",
  "Nenhuma taxa",
  "Sem taxa",
]) {
  assert.ok(
    !panelSource.includes(textoFinanceiro),
    `O PDV nao deve exibir informacoes financeiras ao operador: ${textoFinanceiro}`,
  );
}
assert.ok(
  panelSource.includes("!taxaCartaoSelecionada"),
  "O aviso deve aparecer apenas quando faltar uma regra para a combinacao selecionada.",
);
assert.ok(
  panelSource.includes("Esta combinacao nao esta disponivel"),
  "O PDV deve continuar bloqueando combinacoes sem regra cadastrada.",
);

console.log("Contrato de privacidade das taxas no PDV validado.");
