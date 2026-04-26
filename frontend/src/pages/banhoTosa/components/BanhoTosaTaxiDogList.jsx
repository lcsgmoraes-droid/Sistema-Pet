import { formatCurrency } from "../banhoTosaUtils";

const statusFlow = [
  "agendado",
  "motorista_a_caminho",
  "pet_coletado",
  "entregue_na_clinica",
  "aguardando_retorno",
  "retornando",
  "entregue_ao_tutor",
];

export default function BanhoTosaTaxiDogList({
  items,
  loading,
  saving,
  onAtualizarMedicao,
  onSalvarMedicao,
  onStatus,
}) {
  if (loading) {
    return (
      <div className="rounded-3xl bg-white p-8 text-center text-sm font-semibold text-slate-500">
        Carregando taxi dog...
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <TaxiCard
          key={item.id}
          item={item}
          saving={saving}
          onAtualizarMedicao={onAtualizarMedicao}
          onSalvarMedicao={onSalvarMedicao}
          onStatus={onStatus}
        />
      ))}
      {items.length === 0 && (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          Nenhum taxi dog para esta data.
        </div>
      )}
    </div>
  );
}

function TaxiCard({ item, saving, onAtualizarMedicao, onSalvarMedicao, onStatus }) {
  const proximo = proximoStatus(item.status);
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-orange-500">{item.status}</p>
          <h3 className="mt-1 text-lg font-black text-slate-900">{item.pet_nome} / {item.cliente_nome}</h3>
          <p className="text-sm text-slate-500">{item.tipo} | {hora(item.janela_inicio)} - {hora(item.janela_fim)}</p>
        </div>
        {proximo && (
          <button type="button" disabled={saving} onClick={() => onStatus(item, proximo)} className="rounded-2xl bg-orange-500 px-4 py-2 text-xs font-bold text-white disabled:opacity-50">
            Avancar status
          </button>
        )}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <MiniMetric label="Motorista" value={item.motorista_nome || "Nao definido"} />
        <MiniMetric label="Valor" value={formatCurrency(item.valor_cobrado)} />
        <MiniMetric label="Custo" value={formatCurrency(item.custo_real || item.custo_estimado)} />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <TextField label="Km real" type="number" value={String(item.km_real ?? "0")} onChange={(value) => atualizarItem(item.id, "km_real", value, onAtualizarMedicao)} />
        <TextField label="Custo real" type="number" value={String(item.custo_real ?? "0")} onChange={(value) => atualizarItem(item.id, "custo_real", value, onAtualizarMedicao)} />
        <button type="button" disabled={saving} onClick={() => onSalvarMedicao(item)} className="self-end rounded-2xl border border-slate-200 px-4 py-2 text-xs font-bold text-slate-700 disabled:opacity-50">
          Salvar
        </button>
      </div>
    </div>
  );
}

function atualizarItem(id, field, value, onAtualizarMedicao) {
  onAtualizarMedicao((prev) => prev.map((item) => (item.id === id ? { ...item, [field]: value } : item)));
}

function proximoStatus(status) {
  const index = statusFlow.indexOf(status);
  if (index < 0 || index >= statusFlow.length - 1) return null;
  return statusFlow[index + 1];
}

function hora(value) {
  return value ? String(value).slice(11, 16) : "--:--";
}

function MiniMetric({ label, value }) {
  return (
    <div className="rounded-2xl bg-slate-50 px-3 py-2">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p>
      <p className="font-black text-slate-900">{value}</p>
    </div>
  );
}

function TextField({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <input type={type} step={type === "number" ? "0.01" : undefined} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100" />
    </label>
  );
}
