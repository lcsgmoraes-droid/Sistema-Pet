import assert from "node:assert/strict";
import { agruparProdutos, gerarCsvProdutos, resumirCurvaAbc } from "./analiseProdutosUtils.js";

const produtos = [
  {
    produto_id: 1,
    categoria_id: 10,
    categoria_nome: "Rações",
    quantidade: 3,
    faturamento: 300,
    lucro_estimado: 90,
    abc_faturamento: "A",
  },
  {
    produto_id: 2,
    categoria_id: 10,
    categoria_nome: "Rações",
    quantidade: 2,
    faturamento: 100,
    lucro_estimado: 20,
    abc_faturamento: "B",
  },
  {
    produto_id: 3,
    categoria_id: null,
    categoria_nome: null,
    quantidade: 1,
    faturamento: 50,
    lucro_estimado: -5,
    abc_faturamento: "C",
  },
];

const grupos = agruparProdutos(produtos, "categoria");
assert.equal(grupos[0].nome, "Rações");
assert.equal(grupos[0].produtos, 2);
assert.equal(grupos[0].faturamento, 400);
assert.equal(grupos[0].participacao_pct, 88.89);
assert.equal(grupos[1].nome, "Sem categoria");

const abc = resumirCurvaAbc(produtos, "faturamento");
assert.equal(abc.find((item) => item.classe === "A").valor, 300);
assert.equal(abc.find((item) => item.classe === "C").produtos, 1);

const csv = gerarCsvProdutos([{ produto_nome: 'Ração "Premium"', codigo: "ABC;1" }]);
assert.match(csv, /"Ração ""Premium"""/);
assert.match(csv, /"ABC;1"/);

console.log("analiseProdutosUtils: ok");
