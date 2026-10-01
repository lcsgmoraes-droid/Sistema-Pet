// Cores por segmento comercial (Pet/Vet/Banho&Tosa) — usado quando os planos
// de um mesmo formulario precisam de blocos visualmente distintos (ver
// proposta comercial em ops-tenants). "azul" é o padrão (mesma cor de sempre,
// nenhuma tela existente precisa passar a prop `tom`).
const TONS_RADIO = {
  azul:
    "peer-checked:border-blue-600 peer-checked:bg-blue-600 peer-checked:hover:bg-blue-700 peer-focus-visible:ring-blue-500 dark:peer-checked:border-blue-500 dark:peer-checked:bg-blue-600 dark:peer-checked:hover:bg-blue-700",
  pet: "peer-checked:border-blue-600 peer-checked:bg-blue-600 peer-checked:hover:bg-blue-700 peer-focus-visible:ring-blue-500 dark:peer-checked:border-blue-500 dark:peer-checked:bg-blue-600 dark:peer-checked:hover:bg-blue-700",
  vet: "peer-checked:border-emerald-600 peer-checked:bg-emerald-600 peer-checked:hover:bg-emerald-700 peer-focus-visible:ring-emerald-500 dark:peer-checked:border-emerald-500 dark:peer-checked:bg-emerald-600 dark:peer-checked:hover:bg-emerald-700",
  grooming:
    "peer-checked:border-violet-600 peer-checked:bg-violet-600 peer-checked:hover:bg-violet-700 peer-focus-visible:ring-violet-500 dark:peer-checked:border-violet-500 dark:peer-checked:bg-violet-600 dark:peer-checked:hover:bg-violet-700",
};

export default function InputRadio({
  disabled = false,
  error = "",
  help = "",
  label,
  name,
  onChange,
  opcoes = [],
  required = false,
  tom = "azul",
  value,
}) {
  const descricaoId = name && (error || help) ? `${name}-descricao` : undefined;
  const corTom = TONS_RADIO[tom] || TONS_RADIO.azul;

  return (
    <div className="w-full">
      {label ? (
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          {label}
          {required ? (
            <span className="ml-0.5 text-red-500">
              *<span className="sr-only"> (obrigatório)</span>
            </span>
          ) : null}
        </span>
      ) : null}
      <div
        role="radiogroup"
        aria-label={label}
        aria-describedby={descricaoId}
        className="mt-1 flex flex-wrap gap-2"
      >
        {opcoes.map((opcao) => {
          const idOpcao = `${name}-${opcao.value}`;
          const desabilitada = disabled || opcao.disabled;

          return (
            <div key={opcao.value}>
              <input
                id={idOpcao}
                name={name}
                type="radio"
                value={opcao.value}
                checked={value === opcao.value}
                disabled={desabilitada}
                onChange={() => onChange?.(opcao.value)}
                className="peer sr-only"
              />
              <label
                htmlFor={idOpcao}
                className={[
                  "inline-flex h-9 items-center justify-center whitespace-nowrap rounded-lg border px-3.5 text-center text-sm font-medium transition-colors",
                  error
                    ? "border-red-500 dark:border-red-500"
                    : "border-slate-300 dark:border-slate-700",
                  "bg-white text-slate-700 hover:bg-slate-50",
                  "peer-checked:text-white",
                  "peer-focus-visible:ring-2 peer-focus-visible:ring-offset-2",
                  "dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
                  "dark:peer-checked:text-white",
                  corTom,
                  desabilitada ? "cursor-not-allowed opacity-60" : "cursor-pointer",
                ].join(" ")}
              >
                {opcao.label}
              </label>
            </div>
          );
        })}
      </div>
      {error || help ? (
        <span
          id={descricaoId}
          className={[
            "mt-1 block text-xs",
            error ? "text-red-600 dark:text-red-400" : "text-slate-500 dark:text-slate-400",
          ].join(" ")}
        >
          {error || help}
        </span>
      ) : null}
    </div>
  );
}
