export default function BanhoTosaParametrosLista({
  parametros,
  onEdit,
  onDelete,
  onToggleAtivo,
}) {
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Parametros cadastrados
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">
        Custos esperados por tamanho
      </h2>

      <div className="mt-5 space-y-3">
        {parametros.map((item) => (
          <ParametroPorteCard
            key={item.id}
            item={item}
            onEdit={onEdit}
            onDelete={onDelete}
            onToggleAtivo={onToggleAtivo}
          />
        ))}

        {parametros.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500">
            Nenhum porte parametrizado ainda.
          </div>
        )}
      </div>
    </div>
  );
}

function ParametroPorteCard({ item, onEdit, onDelete, onToggleAtivo }) {
  const tempoTotal = item.tempo_banho_min + item.tempo_secagem_min + item.tempo_tosa_min;

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-lg font-black capitalize text-slate-900">
            {item.porte}
          </p>
          <p className="text-sm text-slate-500">
            {item.peso_min_kg ?? "-"}kg ate {item.peso_max_kg ?? "-"}kg
          </p>
        </div>
        <button
          type="button"
          onClick={() => onToggleAtivo?.(item)}
          className={`rounded-full px-3 py-1 text-xs font-bold ${
            item.ativo
              ? "bg-emerald-100 text-emerald-700"
              : "bg-slate-200 text-slate-500"
          }`}
        >
          {item.ativo ? "Ativo" : "Inativo"}
        </button>
      </div>
      <div className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
        <MiniMetric label="Agua" value={`${item.agua_padrao_litros} L`} />
        <MiniMetric label="Energia" value={`${item.energia_padrao_kwh} kWh`} />
        <MiniMetric label="Tempo" value={`${tempoTotal} min`} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <ActionButton onClick={() => onEdit?.(item)}>Editar</ActionButton>
        <ActionButton danger onClick={() => onDelete?.(item)}>Excluir</ActionButton>
      </div>
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
