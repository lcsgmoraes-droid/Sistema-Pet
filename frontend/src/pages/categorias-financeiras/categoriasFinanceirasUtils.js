import {
  ICON_FALLBACK,
  MOJIBAKE_REPLACEMENTS,
  QUESTION_MARK_WORD_FIXES,
} from "./categoriasFinanceirasConstants.js";
import { inferirNaturezaDRE } from "../../utils/dreCategoriaFinanceira.js";

export function normalizeDisplayText(value) {
  if (typeof value !== "string") return value || "";

  let text = value;
  for (const [broken, fixed] of Object.entries(MOJIBAKE_REPLACEMENTS)) {
    text = text.split(broken).join(fixed);
  }

  for (const [pattern, fixed] of QUESTION_MARK_WORD_FIXES) {
    text = text.replace(pattern, fixed);
  }

  return text
    .replace(/�/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function normalizeIcon(iconValue) {
  const icon = normalizeDisplayText(iconValue);
  if (!icon || /[?�]/.test(icon)) return ICON_FALLBACK;
  return icon;
}

export function getSubcategoriasDREDaCategoria(categoria, subcategoriasDRE) {
  if (!categoria) return [];

  const porCatFinanceira = subcategoriasDRE.filter(
    (subcategoria) => subcategoria.categoria_financeira_id === categoria.id,
  );
  const principal = subcategoriasDRE.find(
    (subcategoria) => subcategoria.id === categoria.dre_subcategoria_id,
  );
  // O vínculo com a categoria DRE não dá propriedade das subcategorias irmãs.
  // O vínculo legado principal pode ser exibido, mas não deve ser apagado.
  return principal && !porCatFinanceira.some((sub) => sub.id === principal.id)
    ? [...porCatFinanceira, principal]
    : porCatFinanceira;
}

export function resolverCategoriaDREId({
  categoriaFinanceiraId,
  categorias,
  subcategoriasDRE,
  dreCategorias,
}) {
  const categoriaFinanceira = categorias.find(
    (categoria) => categoria.id === Number(categoriaFinanceiraId),
  );
  if (!categoriaFinanceira) return null;

  if (categoriaFinanceira.dre_subcategoria_id) {
    const subPrincipal = subcategoriasDRE.find(
      (subcategoria) => subcategoria.id === categoriaFinanceira.dre_subcategoria_id,
    );
    if (subPrincipal?.categoria_id) return subPrincipal.categoria_id;
  }

  const natureza = inferirNaturezaDRE(categoriaFinanceira);
  return (
    dreCategorias.find(
      (categoria) =>
        categoria.natureza === natureza &&
        categoria.ativo !== false &&
        String(categoria.nome || "")
          .trim()
          .toLocaleLowerCase("pt-BR") ===
          String(categoriaFinanceira.nome || "")
            .trim()
            .toLocaleLowerCase("pt-BR"),
    )?.id || null
  );
}

export function buildCategoriaPayload(formData) {
  return {
    nome: formData.nome,
    tipo: formData.tipo,
    cor: formData.cor,
    icone: formData.icone,
    descricao: formData.descricao,
    ativo: formData.ativo,
    tipo_custo: formData.tipo_custo,
  };
}

export function buildSubcategoriaDREPayload({ categoriaDREId, nome, categoriaFinanceiraId }) {
  return {
    categoria_id: categoriaDREId,
    nome,
    tipo_custo: "direto",
    escopo_rateio: "ambos",
    categoria_financeira_id: categoriaFinanceiraId,
  };
}

export function buildSubcategoriasExistentes(subcategorias, categoriaFinanceiraId) {
  return subcategorias.map((subcategoria) => ({
    id: subcategoria.id,
    nome: subcategoria.nome,
    descricao: subcategoria.descricao || "",
    ativo: subcategoria.ativo,
    tipo_custo: subcategoria.tipo_custo,
    escopo_rateio: subcategoria.escopo_rateio,
    somenteVinculo: subcategoria.categoria_financeira_id !== categoriaFinanceiraId,
  }));
}

export function filterCategoriasRaiz(categorias, filtroTipo) {
  return categorias.filter((categoria) => {
    if (categoria.categoria_pai_id) return false;
    if (filtroTipo === "todos") return true;
    return categoria.tipo === filtroTipo;
  });
}

export function countCategoriasByTipo(categorias, tipo) {
  return categorias.filter((categoria) => categoria.tipo === tipo).length;
}

export function podeClassificarCustoPeDRE(categoria, subcategoria) {
  return (
    categoria.pode_editar === true &&
    categoria.tipo_custo === "ambos" &&
    (subcategoria.categoria_financeira_id == null ||
      subcategoria.categoria_financeira_id === categoria.id)
  );
}

export function getFilhasFinanceiras(categorias, categoriaPaiId) {
  return categorias.filter((categoria) => categoria.categoria_pai_id === categoriaPaiId);
}
