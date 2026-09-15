import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  COLUNAS_PADRAO_RELATORIO_PESSOAS,
  desenharCabecalhoTabelaPdf,
  montarLinhasRelatorioPessoas,
  obterColunasRelatorio,
  obterNomeEmpresaRelatorio,
  ordenarPessoasRelatorio,
} from "../src/components/pessoas/pessoasRelatorioUtils.js";

const pessoas = [
  {
    id: 1,
    codigo: "20",
    nome: "Zelia",
    telefone: "1111-1111",
    cep: "11111-111",
    endereco: "Rua B",
    bairro: "Centro",
    created_at: "2026-01-01T10:00:00Z",
  },
  {
    id: 2,
    codigo: "3",
    nome: "Ana",
    celular: "2299999-9999",
    cep: "22222-222",
    endereco: "Rua A",
    bairro: "Jardim",
    created_at: "2026-02-01T10:00:00Z",
  },
];

assert.deepEqual(COLUNAS_PADRAO_RELATORIO_PESSOAS, ["nome", "telefone"]);
assert.deepEqual(
  ordenarPessoasRelatorio(pessoas, "nome_asc").map((pessoa) => pessoa.nome),
  ["Ana", "Zelia"],
);
assert.deepEqual(
  ordenarPessoasRelatorio(pessoas, "codigo_asc").map((pessoa) => pessoa.codigo),
  ["3", "20"],
);
assert.deepEqual(
  ordenarPessoasRelatorio(pessoas, "cadastro_desc").map((pessoa) => pessoa.nome),
  ["Ana", "Zelia"],
);
assert.deepEqual(
  montarLinhasRelatorioPessoas([pessoas[1]], ["nome", "telefone", "cep", "endereco", "bairro"]),
  [
    ["Nome", "Telefone", "CEP", "Rua / endereco", "Bairro"],
    ["Ana", "2299999-9999", "22222-222", "Rua A", "Jardim"],
  ],
);
assert.equal(obterNomeEmpresaRelatorio({ nome: "Pet Feliz", slug: "pet-feliz" }), "Pet Feliz");
assert.equal(obterNomeEmpresaRelatorio({ slug: "pet-feliz" }), "pet-feliz");

const chamadasPdf = [];
const docPdf = {
  setFillColor: (...args) => chamadasPdf.push(["setFillColor", ...args]),
  setDrawColor: (...args) => chamadasPdf.push(["setDrawColor", ...args]),
  setTextColor: (...args) => chamadasPdf.push(["setTextColor", ...args]),
  setFont: (...args) => chamadasPdf.push(["setFont", ...args]),
  setFontSize: (...args) => chamadasPdf.push(["setFontSize", ...args]),
  rect: (...args) => chamadasPdf.push(["rect", ...args]),
  splitTextToSize: (texto) => [texto],
  text: (...args) => chamadasPdf.push(["text", ...args]),
};
desenharCabecalhoTabelaPdf(docPdf, {
  colunasAtivas: obterColunasRelatorio(["nome", "telefone"]),
  larguras: [120, 70],
  margem: 10,
  y: 34,
  tamanhoFonte: 8,
});
assert.deepEqual(
  chamadasPdf.find((chamada) => chamada[0] === "rect" && chamada.at(-1) === "F"),
  ["rect", 10, 34, 190, 7, "F"],
);
assert.deepEqual(
  chamadasPdf.filter((chamada) => chamada[0] === "text").map((chamada) => chamada[1]),
  ["Nome", "Telefone"],
);

const raiz = resolve(import.meta.dirname, "..");
const pagina = readFileSync(resolve(raiz, "src/pages/ClientesNovo.jsx"), "utf8");
const barra = readFileSync(
  resolve(raiz, "src/components/clientes/ClientesNovoActionsBar.jsx"),
  "utf8",
);
const modal = readFileSync(
  resolve(raiz, "src/components/pessoas/PessoasRelatorioModal.jsx"),
  "utf8",
);

assert.match(pagina, /PessoasRelatorioModal/);
assert.match(pagina, /title="Pessoas"/);
assert.match(barra, />\s*Relatorios\s*</);
assert.match(modal, /Nome \+ telefone/);
assert.match(modal, /Contato \+ endereco/);
assert.match(modal, /Baixar Excel/);
assert.match(modal, /Baixar PDF/);
assert.match(modal, /empresa/);

console.log("Contrato do relatorio personalizado de pessoas validado.");
