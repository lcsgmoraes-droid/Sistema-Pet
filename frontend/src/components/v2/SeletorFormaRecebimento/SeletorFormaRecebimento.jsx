import BotaoInteracao from "../BotaoInteracao/BotaoInteracao";
import PaymentMethodIcon from "../../PaymentMethodIcon";

export default function SeletorFormaRecebimento({
  formas = [],
  value,
  onChange,
  disabled = false,
  children,
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {children}
      {formas.map((forma) => (
        <div
          key={forma.id}
          className={
            String(value) === String(forma.id)
              ? "min-w-0 rounded-xl ring-2 ring-blue-400 ring-offset-2 dark:ring-offset-slate-900"
              : "min-w-0"
          }
        >
          <BotaoInteracao
            larguraTotal
            disabled={disabled}
            aria-pressed={String(value) === String(forma.id)}
            onClick={() => onChange?.(forma)}
            className={String(value) === String(forma.id) ? "ring-2 ring-blue-500" : ""}
          >
            <span className="flex shrink-0">
              <PaymentMethodIcon icone={forma.icone} nome={forma.nome} />
            </span>
            <span className="min-w-0 whitespace-normal text-center leading-tight">
              {forma.nome}
            </span>
          </BotaoInteracao>
        </div>
      ))}
    </div>
  );
}
