export default function BanhoTosaRecursosList({
  recursos,
  onEdit,
  onDelete,
  onToggleAtivo,
}) {
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Recursos
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">
            Estrutura da operacao
          </h2>
        </div>
        <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">
          {recursos.length} itens
        </span>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {recursos.map((recurso) => (
          <div key={recurso.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-black text-slate-900">{recurso.nome}</p>
                <p className="text-sm capitalize text-slate-500">{recurso.tipo}</p>
              </div>
              <button
                type="button"
                onClick={() => onToggleAtivo(recurso)}
                className={`rounded-full px-3 py-1 text-xs font-bold ${
                  recurso.ativo
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-200 text-slate-500"
                }`}
              >
                {recurso.ativo ? "Ativo" : "Inativo"}
              </button>
            </div>
            <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
              <MiniMetric label="Cap." value={recurso.capacidade_simultanea} />
              <MiniMetric label="Watts" value={recurso.potencia_watts || "-"} />
              <MiniMetric label="Manut." value={recurso.custo_manutencao_hora || "0"} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <ActionButton onClick={() => onEdit(recurso)}>Editar</ActionButton>
              <ActionButton danger onClick={() => onDelete(recurso)}>Excluir</ActionButton>
            </div>
          </div>
        ))}
        {recursos.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500 md:col-span-2">
            Nenhum recurso cadastrado ainda.
          </div>
        )}
      </div>
    </div>
  );
}

function MiniMetric({ label, value }) {
  return (
    <div className="rounded-xl bg-white px-3 py-2">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">
        {label}
      </p>
      <p className="font-black text-slate-900">{value}</p>
    </div>
  );
}

function ActionButton({ children, danger = false, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-black transition ${
        danger
          ? "bg-red-50 text-red-700 hover:bg-red-100"
          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      }`}
    >
      {children}
    </button>
  );
}
