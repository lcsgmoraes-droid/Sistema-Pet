import MoneyCell from "../ui/MoneyCell";
import NumberCell from "../ui/NumberCell";
import {
  descreverRentabilidadePendente,
  PENDENCIA_IFOOD_LABEL,
  temRentabilidadePendente,
} from "./vendasFinanceiro/rentabilidadePendente.js";

export default function RentabilidadeCell({ dados, percentual = false, value, ...props }) {
  if (temRentabilidadePendente(dados)) {
    return (
      <span
        className="text-xs font-semibold text-amber-800 dark:text-amber-300"
        title={descreverRentabilidadePendente(dados)}
      >
        {PENDENCIA_IFOOD_LABEL}
      </span>
    );
  }
  return percentual ? (
    <NumberCell value={value} decimals={1} suffix="%" {...props} />
  ) : (
    <MoneyCell value={value} {...props} />
  );
}
