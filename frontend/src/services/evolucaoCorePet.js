import api from "../api";

const STORAGE_KEY = "corepet.evolucao.itens-vistos";
export const EVOLUCAO_VISTA_EVENT = "corepet:evolucao-vista";

export async function listarEvolucaoCorePet() {
  const { data } = await api.get("/evolucao");
  return {
    itens: Array.isArray(data?.itens) ? data.itens : [],
    atualizadoEm: data?.atualizado_em ?? null,
  };
}

export function lerIdsEvolucaoVistos() {
  if (typeof window === "undefined") return new Set();
  try {
    const value = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
    return new Set(Array.isArray(value) ? value.filter(Boolean) : []);
  } catch {
    return new Set();
  }
}

export function contarNovidadesNaoVistas(itens) {
  const vistos = lerIdsEvolucaoVistos();
  return itens.filter((item) => item.status === "disponivel" && !vistos.has(item.id)).length;
}

export function marcarNovidadesComoVistas(itens) {
  if (typeof window === "undefined") return;
  const vistos = lerIdsEvolucaoVistos();
  itens.filter((item) => item.status === "disponivel").forEach((item) => vistos.add(item.id));
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...vistos]));
  window.dispatchEvent(new CustomEvent(EVOLUCAO_VISTA_EVENT));
}
