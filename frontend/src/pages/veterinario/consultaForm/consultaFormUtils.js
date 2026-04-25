export const css = {
  input:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300",
  textarea:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 resize-y min-h-[80px]",
  select:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white",
};

export const ETAPAS = ["Triagem", "Exame Clínico", "Diagnóstico / Prescrição"];

export function toNumber(value) {
  if (value == null || value === "") return 0;
  return Number(String(value).replace(",", ".")) || 0;
}

export function parseNumero(valor) {
  if (valor === null || valor === undefined) return NaN;
  const texto = String(valor).trim().replace(",", ".");
  if (!texto) return NaN;
  return Number.parseFloat(texto);
}

export function hojeIso() {
  return new Date().toISOString().slice(0, 10);
}

export function formatDateTimeBR(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function obterResumoProcedimentoSelecionado(item, catalogos) {
  const catalogo = catalogos.find((proc) => String(proc.id) === String(item.catalogo_id));
  const valorCobrado = toNumber(item.valor || catalogo?.valor_padrao || 0);
  const custoTotal = toNumber(catalogo?.custo_estimado || 0);
  const margemValor = valorCobrado - custoTotal;
  const margemPercentual = valorCobrado > 0 ? (margemValor / valorCobrado) * 100 : 0;
  return {
    possuiCatalogo: Boolean(catalogo),
    valorCobrado,
    custoTotal,
    margemValor,
    margemPercentual,
  };
}
