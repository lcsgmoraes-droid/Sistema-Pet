import CustomerIdentity from "../../../components/ui/CustomerIdentity";
import EmptyState from "../../../components/ui/EmptyState";
import Panel from "../../../components/ui/Panel";
import { formatNumber } from "../banhoTosaUtils";

export default function BanhoTosaCreditosList({ creditos = [] }) {
  return (
    <Panel
      actions={
        <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
          {creditos.length} saldos
        </span>
      }
      subtitle="Saldos liberados por pacote, tutor e pet vinculado."
      title="Creditos dos clientes"
    >
      <div className="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
        {creditos.map((credito) => (
          <div key={credito.id} className="grid gap-3 p-3 md:grid-cols-[1.2fr_0.8fr_0.7fr_0.7fr] md:items-center">
            <div>
              <p className="font-semibold text-slate-900">{credito.pacote_nome}</p>
              <p className="flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
                <CustomerIdentity
                  codeLabel="Cod. tutor"
                  fallback={`Tutor #${credito.cliente_id || "-"}`}
                  layout="inline"
                  nameClassName="font-medium text-slate-600"
                  record={credito}
                />
                <span>| {credito.pet_nome || "todos os pets"}</span>
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
          <EmptyState
            compact
            description="Libere um pacote para o cliente e o saldo aparecera aqui."
            title="Nenhum credito liberado"
          />
        )}
      </div>
    </Panel>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p>
      <p className="text-sm font-semibold text-slate-900">{value}</p>
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
