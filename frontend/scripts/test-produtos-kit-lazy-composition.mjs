import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const listagemSource = read("src/hooks/useProdutosListagem.js");
const tabelaHookSource = read("src/hooks/useProdutosTabela.jsx");
const tabelaSource = read("src/components/produtos/ProdutosTabelaSection.jsx");

assert(
  listagemSource.includes("filtrosLimpos.incluir_detalhes_composto = false"),
  "A listagem principal deve continuar sem carregar todas as composicoes.",
);
assert(
  tabelaHookSource.includes("getProduto(produtoId)"),
  "A composicao deve ser buscada somente quando o kit for expandido.",
);
assert(
  tabelaHookSource.includes('status: "success"'),
  "A composicao carregada deve ficar em cache durante a permanencia na tela.",
);
assert(
  tabelaSource.includes("Carregando itens do kit"),
  "A linha expandida deve informar enquanto os itens sao carregados.",
);
assert(
  tabelaSource.includes("Tentar novamente"),
  "A linha expandida deve permitir nova tentativa quando a consulta falhar.",
);

console.log("Produtos kit lazy composition contract OK");
