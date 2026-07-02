import { CatalogOrder } from "../../../services/shop.service";
import { Produto } from "../../../types";

export const ORDER_OPTIONS: Array<{ value: CatalogOrder; label: string }> = [
  { value: "prontos", label: "Relevancia" },
  { value: "nome", label: "A-Z" },
  { value: "menor_preco", label: "Menor preco" },
  { value: "maior_preco", label: "Maior preco" },
];

export type EspecieFiltro = "todos" | "cao" | "gato";
export type PesoEmbalagemFiltro = number | null;

export type CatalogoFiltros = {
  especie: EspecieFiltro;
  pesoEmbalagem: PesoEmbalagemFiltro;
  marca: string;
};

export const FILTROS_PADRAO: CatalogoFiltros = {
  especie: "todos",
  pesoEmbalagem: null,
  marca: "",
};

export const ESPECIE_OPTIONS: Array<{ value: EspecieFiltro; label: string }> = [
  { value: "todos", label: "Todos" },
  { value: "cao", label: "Cao" },
  { value: "gato", label: "Gato" },
];

export function normalizarTexto(value: string | null | undefined): string {
  return (value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function textoProduto(produto: Produto): string {
  return normalizarTexto(
    [
      produto.nome,
      produto.categoria_nome,
      produto.marca_nome,
      produto.descricao,
    ]
      .filter(Boolean)
      .join(" "),
  );
}

function combinaEspecie(texto: string, especie: EspecieFiltro): boolean {
  if (especie === "todos") return true;

  const termosCao = /\b(cao|caes|canin|cachorro|dog|puppy)\b/;
  const termosGato = /\b(gato|gatos|felin|cat|kitten)\b/;

  if (especie === "cao") {
    if (termosCao.test(texto)) return true;
    return !termosGato.test(texto);
  }

  if (termosGato.test(texto)) return true;
  return !termosCao.test(texto);
}

export function normalizarPesoEmbalagem(
  value: number | string | null | undefined,
): number | null {
  if (value === null || value === undefined || value === "") return null;
  const peso =
    typeof value === "string"
      ? Number(value.replace(",", ".").trim())
      : Number(value);
  if (!Number.isFinite(peso) || peso <= 0) return null;
  return Number(peso.toFixed(3));
}

export function formatarPesoEmbalagemFiltro(peso: number): string {
  const valor = Number(peso.toFixed(3));
  return `${String(valor).replace(".", ",")} kg`;
}

function combinaPesoEmbalagem(
  peso: number | null | undefined,
  filtro: PesoEmbalagemFiltro,
): boolean {
  if (filtro === null) return true;
  const pesoKg = normalizarPesoEmbalagem(peso);
  return pesoKg !== null && Math.abs(pesoKg - filtro) < 0.001;
}

export function aplicarFiltrosCatalogo(
  produto: Produto,
  filtros: CatalogoFiltros,
): boolean {
  const texto = textoProduto(produto);

  if (filtros.marca && produto.marca_nome !== filtros.marca) return false;
  if (!combinaEspecie(texto, filtros.especie)) return false;
  if (!combinaPesoEmbalagem(produto.peso_embalagem_kg, filtros.pesoEmbalagem))
    return false;

  return true;
}
