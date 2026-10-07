export function inferirNaturezaDRE({ nome, tipo }) {
  if (tipo === "receita") return "receita";
  const nomeComparacao = normalizarNomeCategoria(nome);
  return /^(cmv|cpv|custo das mercadorias vendidas|custo dos produtos vendidos|custo dos servicos prestados)$/.test(
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

function encontrarCategoriaDRE(categorias, nome, natureza) {
  const nomeComparacao = normalizarNomeCategoria(nome);
  return categorias.find(
    (categoria) =>
      categoria.ativo !== false &&
      categoria.natureza === natureza &&
      normalizarNomeCategoria(categoria.nome) === nomeComparacao,
  );
}

export async function prevalidarSubcategoriasDRE(
  api,
  { nomeCategoria, tipoCategoria, categoriaFinanceiraId, categoriaDREId, subcategorias },
) {
  const informadas = (subcategorias || []).filter((subcategoria) => subcategoria.nome?.trim());
  if (informadas.length === 0) return;

  const [categoriasResponse, subcategoriasResponse] = await Promise.all([
    api.get("/dre/categorias"),
    api.get("/dre/subcategorias"),
  ]);
  const categoriasDRE = categoriasResponse.data || [];
  const existentes = subcategoriasResponse.data || [];
  const natureza = inferirNaturezaDRE({ nome: nomeCategoria, tipo: tipoCategoria });
  const grupoNovas =
    categoriaDREId || encontrarCategoriaDRE(categoriasDRE, nomeCategoria, natureza)?.id || "novo";

  const pretendidas = informadas.flatMap((subcategoria) => {
    const nomeNormalizado = normalizarNomeCategoria(subcategoria.nome);
    if (!subcategoria.id) {
      return [
        { id: null, categoriaId: grupoNovas, nome: subcategoria.nome.trim(), nomeNormalizado },
      ];
    }

    const original = existentes.find((item) => item.id === subcategoria.id);
    if (
      !original ||
      original.categoria_financeira_id !== categoriaFinanceiraId ||
      original.ativo === false ||
      normalizarNomeCategoria(original.nome) === nomeNormalizado
    ) {
      return [];
    }
    return [
      {
        id: subcategoria.id,
        categoriaId: original.categoria_id,
        nome: subcategoria.nome.trim(),
        nomeNormalizado,
      },
    ];
  });

  for (const pretendida of pretendidas) {
    const repetidaNoFormulario = pretendidas.some(
      (outra) =>
        outra !== pretendida &&
        outra.categoriaId === pretendida.categoriaId &&
        outra.nomeNormalizado === pretendida.nomeNormalizado,
    );
    const jaExistente = existentes.some(
      (existente) =>
        existente.ativo !== false &&
        existente.id !== pretendida.id &&
        existente.categoria_id === pretendida.categoriaId &&
        normalizarNomeCategoria(existente.nome) === pretendida.nomeNormalizado,
    );
    if (repetidaNoFormulario || jaExistente) {
      throw new Error(`Subcategoria DRE "${pretendida.nome}" já existe nessa categoria.`);
    }
  }
}

export async function garantirCategoriaDRE(api, { nome, tipo, categoriasDRE = [] }) {
  const nomeNormalizado = String(nome || "").trim();
  const natureza = inferirNaturezaDRE({ nome, tipo });
  const existentes = categoriasDRE.length
    ? categoriasDRE
    : (await api.get("/dre/categorias")).data || [];
  const correspondente = encontrarCategoriaDRE(existentes, nomeNormalizado, natureza);
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
    const criadaEmParalelo = encontrarCategoriaDRE(atualizadas, nomeNormalizado, natureza);
    if (criadaEmParalelo) return criadaEmParalelo.id;
    throw error;
  }
}
