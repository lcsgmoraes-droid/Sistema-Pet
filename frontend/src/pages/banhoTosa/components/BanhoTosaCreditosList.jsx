import { formatNumber } from "../banhoTosaUtils";

export default function BanhoTosaCreditosList({ creditos = [] }) {
  return (
    <section className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-600">Saldos</p>
          <h2 className="mt-2 text-xl font-black text-slate-900">Creditos dos clientes</h2>
        </div>
        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">
          {creditos.length} saldos
        </span>
      </div>

      <div className="mt-5 divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200">
        {creditos.map((credito) => (
          <div key={credito.id} className="grid gap-3 p-4 md:grid-cols-[1.2fr_0.8fr_0.7fr_0.7fr] md:items-center">
            <div>
              <p className="font-black text-slate-900">{credito.pacote_nome}</p>
              <p className="text-sm text-slate-500">
                {credito.cliente_nome || `Tutor #${credito.cliente_id}`} | {credito.pet_nome || "todos os pets"}
              </p>
            </div>
            <Info label="Saldo" value={`${formatNumber(credito.saldo_creditos, 0)} de ${formatNumber(credito.creditos_total, 0)}`} />
            <Info label="Validade" value={formatDate(credito.data_validade)} />
            <span className={`rounded-full px-3 py-2 text-center text-xs font-bold ${statusClass(credito)}`}>
              {credito.vencido ? "Vencido" : credito.status}
            </span>
          </div>
        ))}
        {creditos.length === 0 && (
          <p className="p-6 text-center text-sm text-slate-500">Nenhum credito liberado ainda.</p>
        )}
      </div>
    </section>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p>
      <p className="text-sm font-black text-slate-900">{value}</p>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

function statusClass(credito) {
  if (credito.vencido) return "bg-rose-100 text-rose-700";
  if (credito.disponivel) return "bg-emerald-100 text-emerald-700";
  return "bg-slate-100 text-slate-500";
}
