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

export async function garantirCategoriaDRE(api, { nome, tipo, categoriasDRE = [] }) {
  const nomeNormalizado = String(nome || "").trim();
  const nomeComparacao = nomeNormalizado.toLocaleLowerCase("pt-BR");
  const natureza = inferirNaturezaDRE({ nome, tipo });
  const existentes = categoriasDRE.length
    ? categoriasDRE
    : (await api.get("/dre/categorias")).data || [];
  const correspondente = existentes.find(
    (categoria) =>
      categoria.ativo !== false &&
      categoria.natureza === natureza &&
      String(categoria.nome || "")
        .trim()
        .toLocaleLowerCase("pt-BR") === nomeComparacao,
  );
  if (correspondente) return correspondente.id;

  const response = await api.post("/dre/categorias", {
    nome: nomeNormalizado,
    natureza,
  });
  return response.data.id;
}
