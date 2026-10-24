import assert from "node:assert/strict";
import test from "node:test";
import { cadastroIfoodAlterado } from "./ifoodPublicacaoDraft.js";
import { dataHoraIfoodParaFormulario } from "../produto/ifoodProdutoDates.js";

const salvo = {
  codigo: "018631.1",
  nome: "Produto fictício",
  codigo_barras: "0789000000011",
  gtin_ean: "0789000000011",
  descricao_curta: "<p>Apresentação de teste</p>",
  preco_custo: 0,
  preco_venda: 100,
  preco_ifood: 110,
  preco_ifood_promo: 99,
  preco_ifood_promo_inicio: "2026-10-23T12:00:00Z",
  unidade: "UN",
  categoria_id: 4,
  anunciar_ifood: true,
  imagem_principal: "/teste.webp",
};
const formulario = () => ({
  ...salvo,
  descricao: "Apresentação de teste",
  preco_venda: "100.00",
  preco_custo: "",
  categoria_id: "4",
  preco_ifood_promo_inicio: dataHoraIfoodParaFormulario(salvo.preco_ifood_promo_inicio),
});

test("rascunho normalizado corresponde ao salvo sem converter EAN em número", () => {
  assert.equal(cadastroIfoodAlterado(formulario(), salvo), false);
  assert.equal(
    cadastroIfoodAlterado({ ...formulario(), codigo_barras: "789000000011" }, salvo),
    true,
  );
});

test("bloqueia rascunhos mesmo quando a seção monta depois da edição", () => {
  for (const patch of [
    { preco_ifood: 120 },
    { nome: "Nome em edição" },
    { descricao: "Descrição em edição" },
    { categoria_id: 8 },
    { ifood_pausado: true },
    { preco_ifood_promo_fim: "2026-10-24T13:00" },
    { composicao_kit: [{ produto_id: 9, quantidade: 2 }] },
  ])
    assert.equal(cadastroIfoodAlterado({ ...formulario(), ...patch }, salvo), true);
});

test("produto não salvo ou consulta ausente nunca libera operação pelo rascunho", () => {
  assert.equal(cadastroIfoodAlterado(formulario(), null), true);
  assert.equal(cadastroIfoodAlterado(null, salvo), false);
  assert.equal(
    cadastroIfoodAlterado(formulario(), salvo, [{ url: "/outro.webp", principal: true }]),
    true,
  );
});
