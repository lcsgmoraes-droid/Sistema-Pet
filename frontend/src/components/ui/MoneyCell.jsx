import { formatMoneyBRL } from "../../utils/formatters";

export default function MoneyCell({
  className = "",
  value,
  zeroAsDash = false,
}) {
  const numericValue = Number(value || 0);
  const isZero = Math.abs(numericValue) < 0.005;

  return (
    <span className={className}>
      {zeroAsDash && isZero ? "-" : formatMoneyBRL(numericValue)}
    </span>
  );
}
