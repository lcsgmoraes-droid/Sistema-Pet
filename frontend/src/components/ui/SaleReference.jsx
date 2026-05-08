import CopyableValue from "./CopyableValue";

export function getSaleReferenceNumber(sale) {
  const value =
    sale?.numero_venda ??
    sale?.venda_numero ??
    sale?.numero ??
    sale?.venda_id ??
    sale?.id ??
    "";

  return value == null ? "" : String(value);
}

export default function SaleReference({
  buttonClassName = "",
  children,
  className = "",
  empty = null,
  label,
  prefix = "Venda",
  sale,
  showPrefix = true,
  title = "Copiar venda",
  value,
  valueClassName = "font-medium",
}) {
  const saleNumber = value == null ? getSaleReferenceNumber(sale) : String(value);

  if (!saleNumber) {
    return empty;
  }

  const displayValue = children ?? (showPrefix ? `${prefix} #${saleNumber}` : `#${saleNumber}`);

  return (
    <CopyableValue
      className={className}
      buttonClassName={buttonClassName}
      label={label}
      title={title}
      value={saleNumber}
      valueClassName={valueClassName}
    >
      {displayValue}
    </CopyableValue>
  );
}
