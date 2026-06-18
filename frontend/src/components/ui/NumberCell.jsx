export function isZeroNumberValue(value) {
  const numericValue = Number(value || 0);
  return Number.isFinite(numericValue) && Math.abs(numericValue) < 0.0001;
}

export function formatNumberCellValue(
  value,
  { decimals = 0, locale = "pt-BR", prefix = "", suffix = "", zeroAsDash = false } = {},
) {
  const numericValue = Number(value || 0);
  const isZero = isZeroNumberValue(numericValue);

  if (zeroAsDash && isZero) return "-";

  const formatted = numericValue.toLocaleString(locale, {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  });

  return `${prefix}${formatted}${suffix}`;
}

export default function NumberCell({
  className = "",
  decimals = 0,
  prefix = "",
  suffix = "",
  value,
  zeroAsDash = false,
}) {
  return (
    <span className={className}>
      {formatNumberCellValue(value, { decimals, prefix, suffix, zeroAsDash })}
    </span>
  );
}
