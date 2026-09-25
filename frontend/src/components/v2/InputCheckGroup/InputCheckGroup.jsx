export default function InputCheckGroup({
  disabled = false,
  error = "",
  help = "",
  label,
  name,
  onChange,
  opcoes = [],
  required = false,
  value = [],
}) {
  const descricaoId = name && (error || help) ? `${name}-descricao` : undefined;
  const selecionados = Array.isArray(value) ? value : [];
  // Quando alguma opção tem `description`, o grupo vira um grid de cards (título + descrição)
  // em vez da fileira de pills curtas — mesmo toggle transparente/azul, só mais espaço pro texto.
  const temDescricao = opcoes.some((opcao) => opcao.description);

  const alternar = (opcaoValue, marcado) => {
    const proximos = marcado
      ? [...selecionados, opcaoValue]
      : selecionados.filter((item) => item !== opcaoValue);
    onChange?.(proximos);
  };

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
        role="group"
        aria-label={label}
        aria-describedby={descricaoId}
        className={
          temDescricao ? "mt-1 grid grid-cols-1 gap-2 sm:grid-cols-2" : "mt-1 flex flex-wrap gap-2"
        }
      >
        {opcoes.map((opcao) => {
          const idOpcao = `${name}-${opcao.value}`;
          const desabilitada = disabled || opcao.disabled;
          const marcado = selecionados.includes(opcao.value);

          return (
            <div key={opcao.value} className={temDescricao ? "" : "flex-1"}>
              <input
                id={idOpcao}
                name={idOpcao}
                type="checkbox"
                checked={marcado}
                disabled={desabilitada}
                onChange={(evento) => alternar(opcao.value, evento.target.checked)}
                aria-invalid={Boolean(error)}
                className="peer sr-only"
              />
              <label
                htmlFor={idOpcao}
                className={[
                  temDescricao
                    ? "flex w-full flex-col items-start gap-0.5 rounded-lg border px-3.5 py-2.5 text-left transition-colors"
                    : "flex h-9 w-full items-center justify-center rounded-lg border px-3.5 text-center text-sm font-medium transition-colors",
                  error
                    ? "border-red-500 dark:border-red-500"
                    : "border-slate-300 dark:border-slate-700",
                  "bg-white text-slate-700 hover:bg-slate-50",
                  "peer-checked:border-blue-600 peer-checked:bg-blue-600 peer-checked:text-white peer-checked:hover:bg-blue-700",
                  "peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2",
                  "dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
                  "dark:peer-checked:border-blue-500 dark:peer-checked:bg-blue-600 dark:peer-checked:text-white dark:peer-checked:hover:bg-blue-700",
                  desabilitada ? "cursor-not-allowed opacity-60" : "cursor-pointer",
                ].join(" ")}
              >
                {opcao.description ? (
                  <>
                    <span className="text-sm font-semibold">{opcao.label}</span>
                    <span className="text-xs opacity-80">{opcao.description}</span>
                  </>
                ) : (
                  opcao.label
                )}
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
