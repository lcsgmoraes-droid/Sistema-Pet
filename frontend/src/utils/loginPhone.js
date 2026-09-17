export function normalizeBrazilianLoginPhone(value) {
  let digits = String(value || "").replace(/\D/g, "");
  if (digits.length === 13 && digits.startsWith("55")) {
    digits = digits.slice(2);
  }
  return digits;
}

export function isBrazilianMobileLogin(value) {
  const raw = String(value || "").trim();
  if (!looksLikePhoneLoginInput(raw)) return false;

  const digits = normalizeBrazilianLoginPhone(raw);
  return digits.length === 11 && digits[2] === "9";
}

export function looksLikePhoneLoginInput(value) {
  const raw = String(value || "").trim();
  return Boolean(raw) && /^[\d\s()+.-]+$/.test(raw);
}

export function formatBrazilianLoginPhone(value) {
  const digits = normalizeBrazilianLoginPhone(value);
  if (digits.length !== 11) return String(value || "");
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}
