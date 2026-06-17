import { formatMoneyBRL } from "../../utils/formatters";

export function isZeroMoneyValue(value) {
  const numericValue = Number(value || 0);
  return Number.isFinite(numericValue) && Math.abs(numericValue) < 0.005;
}

export function formatMoneyCellValue(
  value,
  { absolute = false, sign = "", zeroAsDash = false } = {},
) {
  const numericValue = Number(value || 0);
  const isZero = isZeroMoneyValue(numericValue);

  if (zeroAsDash && isZero) return "-";

  const displayValue = absolute || sign ? Math.abs(numericValue) : numericValue;
  const prefix = sign && !isZero ? sign : "";
  return `${prefix}${formatMoneyBRL(displayValue)}`;
}

export default function MoneyCell({
  absolute = false,
  className = "",
  sign = "",
  value,
  zeroAsDash = false,
}) {
  return (
    <span className={className}>{formatMoneyCellValue(value, { absolute, sign, zeroAsDash })}</span>
  );
}
