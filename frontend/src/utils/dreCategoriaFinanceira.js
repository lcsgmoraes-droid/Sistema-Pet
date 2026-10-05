export function inferirNaturezaDRE({ nome, tipo }) {
  if (tipo === "receita") return "receita";
  const nomeComparacao = String(nome || "")
    .trim()
    .toLocaleLowerCase("pt-BR");
  return /^(cmv|cpv|custo das mercadorias vendidas|custo dos produtos vendidos|custo dos serviços prestados)$/.test(
    nomeComparacao,
  )
    ? "custo"
    : "despesa";
}

function normalizarNomeCategoria(nome) {
  return String(nome || "")
    .trim()
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase("pt-BR")
    .replace(/\s+/g, " ");
}

export async function garantirCategoriaDRE(api, { nome, tipo, categoriasDRE = [] }) {
  const nomeNormalizado = String(nome || "").trim();
  const nomeComparacao = normalizarNomeCategoria(nomeNormalizado);
  const natureza = inferirNaturezaDRE({ nome, tipo });
  const encontrarCategoria = (categorias) =>
    categorias.find(
      (categoria) =>
        categoria.ativo !== false &&
        categoria.natureza === natureza &&
        normalizarNomeCategoria(categoria.nome) === nomeComparacao,
    );
  const existentes = categoriasDRE.length
    ? categoriasDRE
    : (await api.get("/dre/categorias")).data || [];
  const correspondente = encontrarCategoria(existentes);
  if (correspondente) return correspondente.id;

  try {
    const response = await api.post("/dre/categorias", {
      nome: nomeNormalizado,
      natureza,
    });
    return response.data.id;
  } catch (error) {
    if (error.response?.status !== 409) throw error;
    const atualizadas = (await api.get("/dre/categorias")).data || [];
    const criadaEmParalelo = encontrarCategoria(atualizadas);
    if (criadaEmParalelo) return criadaEmParalelo.id;
    throw error;
  }
}
