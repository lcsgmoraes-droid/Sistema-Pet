export const parseNumeroBR = (valor) => {
  if (valor === null || valor === undefined) return Number.NaN;
  const texto = String(valor).trim();
  if (!texto) return Number.NaN;
  return Number.parseFloat(texto.replaceAll(".", "").replace(",", "."));
};

export const formatQtd = (valor) => {
  const numero = Number(valor || 0);
  return numero.toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
};
