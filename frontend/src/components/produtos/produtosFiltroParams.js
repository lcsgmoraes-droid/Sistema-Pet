export function montarFiltrosProdutosParams(
  filtrosAtuais = {},
  {
    page,
    pageSize,
    includeVariations = Boolean(filtrosAtuais.mostrarPaisVariacoes),
    buscaCompleta = false,
    incluirImagens = false,
    incluirLotes = false,
    incluirDetalhesComposto = false,
    incluirFlagsListagem = true,
  } = {},
) {
  const filtrosLimpos = {};

  Object.entries(filtrosAtuais || {}).forEach(([key, valor]) => {
    if (key === "mostrarPaisVariacoes") {
      return;
    }

    if (key === "ativo") {
      if (valor === "ativos") {
        filtrosLimpos.ativo = true;
      } else if (valor === "inativos") {
        filtrosLimpos.ativo = false;
      } else if (valor === "todos") {
        filtrosLimpos.ativo_status = "todos";
      }
      return;
    }

    if (valor === "" || valor === null || valor === undefined) {
      return;
    }

    if (typeof valor === "boolean") {
      if (valor) {
        filtrosLimpos[key] = true;
      }
      return;
    }

    filtrosLimpos[key] = valor;
  });

  if (page !== undefined) {
    filtrosLimpos.page = page;
  }

  if (pageSize !== undefined) {
    filtrosLimpos.page_size = pageSize;
  }

  if (incluirFlagsListagem) {
    filtrosLimpos.include_variations = Boolean(includeVariations);
    filtrosLimpos.busca_completa = Boolean(buscaCompleta);
    filtrosLimpos.incluir_imagens = Boolean(incluirImagens);
    filtrosLimpos.incluir_lotes = Boolean(incluirLotes);
    filtrosLimpos.incluir_detalhes_composto = Boolean(incluirDetalhesComposto);
  }

  return filtrosLimpos;
}
