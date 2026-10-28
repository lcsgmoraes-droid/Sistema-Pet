import InputCombobox from "../InputCombobox/InputCombobox";
import { useId } from "react";
import InputTexto from "../InputTexto/InputTexto";
import { formatMoneyBRL } from "../../../utils/formatters";

export default function CamposCartaoRecebimento({
  operadoras = [],
  operadoraId,
  onOperadoraChange,
  bandeiras = [],
  bandeira,
  onBandeiraChange,
  nsu,
  onNsuChange,
  parcelas = [1],
  numeroParcelas = 1,
  onParcelasChange,
  valor = 0,
  disabled = false,
  permiteParcelamento = true,
}) {
  const baseId = useId();
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <InputCombobox
        id={`${baseId}-operadora`}
        label="Operadora"
        value={operadoraId}
        required
        disabled={disabled}
        opcoes={operadoras.map((op) => ({ value: op.id, label: op.nome }))}
        onChange={(id) => onOperadoraChange?.(Number(id) || null)}
      />
      <InputCombobox
        id={`${baseId}-bandeira`}
        label="Bandeira"
        value={bandeira}
        required
        disabled={disabled}
        opcoes={bandeiras.map((nome) => ({ value: nome, label: nome }))}
        onChange={(nome) => onBandeiraChange?.(nome || "")}
      />
      <InputTexto
        label="NSU / número da transação"
        value={nsu || ""}
        disabled={disabled}
        onChange={onNsuChange}
        help="Identificação usada na conciliação do cartão."
      />
      {permiteParcelamento && (
        <InputCombobox
          id={`${baseId}-parcelas`}
          label="Número de parcelas"
          value={numeroParcelas}
          required
          disabled={disabled}
          permitirLimpar={false}
          opcoes={parcelas.map((n) => ({
            value: n,
            label: `${n}x de ${formatMoneyBRL(valor / n)}`,
          }))}
          onChange={(n) => onParcelasChange?.(Number(n) || 1)}
        />
      )}
    </div>
  );
}
