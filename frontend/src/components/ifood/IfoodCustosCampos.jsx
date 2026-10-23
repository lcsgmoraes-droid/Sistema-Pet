import InputCheck from "../v2/InputCheck/InputCheck";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import InputPercentual from "../v2/InputPercentual/InputPercentual";
import { valorConhecido } from "./ifoodPresentation";

export const IFOOD_CUSTOS = [
  { key: "commission_merchant_percent", label: "Comissão · entrega própria" },
  { key: "commission_ifood_percent", label: "Comissão · entrega iFood" },
  { key: "payment_fee_percent", label: "Taxa de pagamento" },
  { key: "tax_percent", label: "Tributos estimados" },
  {
    key: "additional_unit_cost",
    label: "Despesa adicional por unidade",
    moeda: true,
    max: 1000000,
  },
  { key: "target_margin_percent", label: "Meta de contribuição", max: 99.99 },
];

// Editor do domínio iFood compartilhado pelas regras salvas e pelo rascunho da calculadora.
export default function IfoodCustosCampos({
  valores,
  onChange,
  disabled = false,
  prefixo = "ifood",
  className = "grid gap-4 md:grid-cols-2 xl:grid-cols-3",
}) {
  return (
    <div className={className}>
      {IFOOD_CUSTOS.map((campo) => {
        const value = valores?.[campo.key];
        const conhecido = valorConhecido(value);
        const CampoValor = campo.moeda ? InputMoeda : InputPercentual;
        return (
          <div
            key={campo.key}
            className="rounded-xl border border-slate-200 p-3 dark:border-slate-700"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="v2-texto font-medium">{campo.label}</p>
              <InputCheck
                id={`${prefixo}-custo-${campo.key}`}
                checked={conhecido}
                disabled={disabled}
                label={conhecido ? "Informado" : "Definir valor"}
                onChange={(checked) => onChange(campo.key, checked ? 0 : null)}
              />
            </div>
            {conhecido ? (
              <CampoValor
                id={`${prefixo}-valor-${campo.key}`}
                label={campo.label}
                disabled={disabled}
                value={value}
                onChange={(novoValor) => onChange(campo.key, novoValor)}
                maxValue={campo.max}
                help="Zero confirma que este custo não se aplica."
              />
            ) : (
              <p className="v2-texto-ajuda mt-2">Não informado</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
