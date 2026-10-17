import assert from "node:assert/strict";
import test from "node:test";

import { deveMostrarParcelaNaDescricao } from "./contasReceberDescricao.js";

test("descricao com a mesma parcela preserva texto sem repetir badge", () => {
  const conta = { eh_parcelado: true, numero_parcela: 3, total_parcelas: 3 };
  assert.equal(
    deveMostrarParcelaNaDescricao({ ...conta, descricao: "Venda 202610130004 - Parcela 3/3" }),
    false,
  );
  assert.equal(
    deveMostrarParcelaNaDescricao({ ...conta, descricao: "Venda - PARCELA 3 / 3" }),
    false,
  );
});

test("descricao livre mantem badge correto, sem confundir outra parcela", () => {
  const conta = { eh_parcelado: true, numero_parcela: 3, total_parcelas: 3 };
  assert.equal(deveMostrarParcelaNaDescricao({ ...conta, descricao: "Venda cliente" }), true);
  assert.equal(deveMostrarParcelaNaDescricao({ ...conta, descricao: "Parcela 3/33" }), true);
  assert.equal(deveMostrarParcelaNaDescricao({ ...conta, descricao: "Parcela 2/3" }), true);
  assert.equal(deveMostrarParcelaNaDescricao({ eh_parcelado: false }), false);
  assert.equal(deveMostrarParcelaNaDescricao({ ...conta, numero_parcela: null }), false);
});
