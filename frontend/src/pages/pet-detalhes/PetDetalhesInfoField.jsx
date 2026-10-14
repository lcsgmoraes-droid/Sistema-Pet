// Bloco compacto de informacao (icone + rotulo + valor) para a grade de "Dados Gerais" do pet —
// substitui o antigo par label/valor empilhado verticalmente, que desperdicava muito espaco
// vertical pra exibir pouco texto por campo.
export default function PetDetalhesInfoField({ icon: Icone, label, mono = false, value }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <span
        className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-white text-slate-500 shadow-sm"
        aria-hidden="true"
      >
        <Icone className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
          {label}
        </p>
        <p
          className={[
            "mt-0.5 truncate text-sm font-semibold text-slate-900",
            mono ? "font-mono" : "",
          ].join(" ")}
          title={typeof value === "string" ? value : undefined}
        >
          {value || "-"}
        </p>
      </div>
    </div>
  );
}
