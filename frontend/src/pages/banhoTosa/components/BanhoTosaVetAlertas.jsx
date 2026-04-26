const labels = {
  alergias: "Alergias",
  condicoes_cronicas: "Condicoes",
  medicamentos_continuos: "Medicamentos",
  restricoes_alimentares: "Restr. alimentares",
};

export default function BanhoTosaVetAlertas({
  restricoes,
  perfil,
  compact = false,
}) {
  const alertas = montarAlertas(restricoes);
  const perfilTexto = montarPerfil(perfil);

  if (alertas.length === 0 && !perfilTexto) {
    return null;
  }

  if (compact) {
    return (
      <div className="mt-2 flex flex-wrap gap-1">
        {alertas.slice(0, 3).map((alerta) => (
          <span key={alerta.key} className="rounded-full bg-red-100 px-2 py-1 text-[11px] font-black text-red-700">
            {alerta.label}
          </span>
        ))}
        {perfilTexto && (
          <span className="rounded-full bg-orange-100 px-2 py-1 text-[11px] font-black text-orange-700">
            {perfilTexto}
          </span>
        )}
      </div>
    );
  }

  return (
    <section className="mt-4 rounded-2xl border border-red-100 bg-red-50 p-4">
      <p className="text-xs font-black uppercase tracking-[0.16em] text-red-600">
        Alertas veterinarios para o banho
      </p>
      {alertas.length === 0 ? (
        <p className="mt-2 text-sm font-semibold text-slate-600">
          Nenhuma restricao clinica cadastrada. {perfilTexto || ""}
        </p>
      ) : (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {alertas.map((alerta) => (
            <div key={alerta.key} className="rounded-xl bg-white px-3 py-2">
              <p className="text-xs font-black uppercase tracking-[0.12em] text-red-500">
                {alerta.label}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-700">
                {alerta.valor}
              </p>
            </div>
          ))}
        </div>
      )}
      {perfilTexto && alertas.length > 0 && (
        <p className="mt-3 text-xs font-bold uppercase tracking-[0.12em] text-orange-600">
          Perfil: {perfilTexto}
        </p>
      )}
    </section>
  );
}

function montarAlertas(restricoes) {
  return Object.entries(labels)
    .map(([key, label]) => ({
      key,
      label,
      valor: normalizarLista(restricoes?.[key]).join(", "),
    }))
    .filter((item) => item.valor);
}

function montarPerfil(perfil) {
  const partes = [];
  if (perfil?.porte) partes.push(perfil.porte);
  if (perfil?.peso) partes.push(`${perfil.peso}kg`);
  return partes.join(" / ");
}

function normalizarLista(valor) {
  if (Array.isArray(valor)) {
    return valor.filter(Boolean);
  }
  if (typeof valor === "string" && valor.trim()) {
    return [valor.trim()];
  }
  return [];
}
