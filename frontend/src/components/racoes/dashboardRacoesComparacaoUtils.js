export const calcularMargem = (custo, venda) => {
  if (!venda || venda === 0) return 0;
  return parseFloat((((venda - custo) / venda) * 100).toFixed(2));
};

export const calcularMarkup = (custo, venda) => {
  if (!custo || custo === 0) return 0;
  return parseFloat((((venda - custo) / custo) * 100).toFixed(2));
};

export const calcularLucro = (custo, venda) => parseFloat((venda - custo).toFixed(2));

export const calcularROI = (custo, venda) => {
  if (!custo || custo === 0) return 0;
  return parseFloat((((venda - custo) / custo) * 100).toFixed(2));
};

export const formatarPesoCompacto = (peso) => {
  if (!peso && peso !== 0) return "-";
  return `${String(peso).replace(/\.0+$/, "")}kg`;
};

export const formatarMoedaCompacta = (valor) => `R$ ${Number(valor || 0).toFixed(2)}`;

export const getCorValor = (valor, min, max, inverter = false) => {
  if (max === min) return "text-slate-700";

  const percentual = ((valor - min) / (max - min)) * 100;

  if (inverter) {
    if (percentual <= 20) return "text-emerald-700 font-semibold";
    if (percentual <= 60) return "text-slate-700";
    return "text-rose-600";
  }

  if (percentual >= 80) return "text-emerald-700 font-semibold";
  if (percentual >= 40) return "text-slate-700";
  return "text-rose-600";
};

export const getCorMargem = (margem) => {
  if (margem >= 40) return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (margem >= 30) return "text-blue-700 bg-blue-50 border-blue-200";
  if (margem >= 20) return "text-amber-700 bg-amber-50 border-amber-200";
  if (margem >= 10) return "text-orange-700 bg-orange-50 border-orange-200";
  return "text-rose-700 bg-rose-50 border-rose-200";
};
