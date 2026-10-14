// Par rotulo/valor de uma "ficha" integrada (dl/dt/dd) — icone pequeno e discreto ao lado do
// rotulo, sem caixa/borda individual: a coesao vem do container pai (um unico painel dividido
// por secao), nao de cada campo isolado em seu proprio cartao.
export default function PetDetalhesInfoField({ icon: Icone, label, mono = false, value }) {
  return (
    <div className="min-w-0">
      <dt className="flex items-center gap-1.5 text-xs font-medium text-gray-600">
        {Icone ? <Icone className="h-3.5 w-3.5 flex-none text-gray-500" aria-hidden="true" /> : null}
        {label}
      </dt>
      <dd
        className={[
          "mt-0.5 truncate text-sm text-gray-900",
          mono ? "font-mono font-medium" : "font-semibold",
        ].join(" ")}
        title={typeof value === "string" ? value : undefined}
      >
        {value || "-"}
      </dd>
    </div>
  );
}
