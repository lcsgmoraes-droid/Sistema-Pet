import { ArrowRight, Route } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import { TextField } from "../../../components/ui/FormField";
import PetAvatar from "../../../components/ui/PetAvatar";
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
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm font-medium text-slate-500 shadow-sm">
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
        <EmptyState compact description="Cadastre um transporte vinculado a um agendamento." icon={Route} title="Nenhum taxi dog para esta data" />
      )}
    </div>
  );
}

function TaxiCard({ item, saving, onAtualizarMedicao, onSalvarMedicao, onStatus }) {
  const proximo = proximoStatus(item.status);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <PetAvatar alt={item.pet_nome || "Pet"} name={item.pet_nome} size="md" url={item.pet_foto_url} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate text-sm font-semibold text-slate-900">{item.pet_nome} / {item.cliente_nome}</h3>
              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">{labelStatus(item.status)}</span>
            </div>
            <p className="mt-1 text-sm text-slate-500">{labelTipo(item.tipo)} | {hora(item.janela_inicio)} - {hora(item.janela_fim)}</p>
          </div>
        </div>
        {proximo && (
          <ActionButton disabled={saving} icon={ArrowRight} intent="edit" onClick={() => onStatus(item, proximo)}>
            Avancar status
          </ActionButton>
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
        <ActionButton className="self-end" disabled={saving} intent="neutral" onClick={() => onSalvarMedicao(item)} tone="soft">
          Salvar
        </ActionButton>
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
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function labelStatus(status) {
  const labels = {
    agendado: "Agendado",
    motorista_a_caminho: "A caminho",
    pet_coletado: "Pet coletado",
    entregue_na_clinica: "Na loja",
    aguardando_retorno: "Aguardando retorno",
    retornando: "Retornando",
    entregue_ao_tutor: "Entregue",
  };
  return labels[status] || status;
}

function labelTipo(tipo) {
  const labels = {
    ida: "Somente ida",
    volta: "Somente volta",
    ida_volta: "Ida e volta",
  };
  return labels[tipo] || tipo;
}
