import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

test("formas cadastradas do mesmo tipo exibem totais e detalhes separados", async () => {
  const pagamento = (id, forma, valor) => ({
    id: `pagamento-${id}`,
    venda_id: id,
    numero_venda: `TESTE-${id}`,
    forma_pagamento: forma,
    forma_pagamento_tipo: "PIX",
    valor,
    tipo: valor < 0 ? "estorno" : "pagamento",
    data_venda: "2026-10-24",
    data_recebimento: "2026-10-24T12:00:00",
  });
  const h = createControllerHarness(
    fileURLToPath(new URL("./RecebimentosCaixaPanel.jsx", import.meta.url)),
    {
      props: {
        composicao: {
          data_inicio: "2026-10-24",
          data_fim: "2026-10-24",
          total_recebido: 190,
          vendas_periodo: 200,
          vendas_anteriores: 0,
          devolucoes: 10,
          creditos_utilizados: 0,
          por_forma_pagamento: {
            Pix: { total: 40 },
            "Pix Stone": { total: 90 },
            "Pix Itaú": { total: 60 },
          },
          detalhes: [
            pagamento(1, "Pix", 40),
            pagamento(2, "Pix Stone", 100),
            pagamento(3, "Pix Itaú", 60),
            pagamento(4, "Pix Stone", -10),
          ],
        },
      },
      mocks: new Map([
        ["lucide-react", {}],
        ["../v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
      ]),
    },
  );
  const botoesFormas = () =>
    elements(h.tree).filter((el) => el.props?.["aria-label"]?.startsWith("Ver recebimentos em "));
  assert.deepEqual(
    botoesFormas().map((el) => el.props["aria-label"]),
    ["Ver recebimentos em Pix", "Ver recebimentos em Pix Stone", "Ver recebimentos em Pix Itaú"],
  );
  for (const valor of ["40,00", "90,00", "60,00"]) {
    assert.ok(elementText(h.tree).includes(valor));
  }
  assert.equal(elements(h.tree).filter((el) => el.props?.role === "listitem").length, 0);

  await h.act(() => botoesFormas()[1].props.onClick());
  const detalhes = () => elements(h.tree).filter((el) => el.props?.role === "listitem");
  assert.equal(detalhes().length, 2);
  assert.ok(detalhes().every((el) => elementText(el).includes("Pix Stone")));
  assert.ok(detalhes().some((el) => elementText(el).includes("Devolvido ou estornado em")));
  assert.ok(detalhes().every((el) => !elementText(el).includes("Pix Itaú")));

  await h.act(() =>
    elements(h.tree)
      .find((el) => el.type === "BotaoInteracao" && elementText(el) === "Ver todas as formas")
      .props.onClick(),
  );
  assert.equal(detalhes().length, 4);
});
