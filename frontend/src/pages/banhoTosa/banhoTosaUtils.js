export function formatCurrency(value) {
  const numericValue = Number(value || 0);
  return numericValue.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function formatNumber(value, fractionDigits = 2) {
  const numericValue = Number(value || 0);
  return numericValue.toLocaleString("pt-BR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

export function toApiDecimal(value, fallback = "0") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  return String(value).replace(",", ".");
}

export function getApiErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }

  return fallback;
}
