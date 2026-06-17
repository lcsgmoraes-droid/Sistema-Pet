import { Pencil, Power, Trash2 } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import Panel from "../../../components/ui/Panel";
import { formatCurrency, formatNumber } from "../banhoTosaUtils";

export default function BanhoTosaRecursosList({ recursos = [], onEdit, onDelete, onToggleAtivo }) {
  return (
    <Panel
      actions={
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
          {recursos.length} itens
        </span>
      }
      subtitle="Estrutura usada na agenda, fila, relatorios de ocupacao e custos."
      title="Estrutura da operacao"
    >
      <div className="grid gap-3 md:grid-cols-2">
        {recursos.map((recurso) => (
          <article
            key={recurso.id}
            className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="truncate font-semibold text-slate-900">{recurso.nome}</p>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      recurso.ativo
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {recurso.ativo ? "Ativo" : "Inativo"}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-500">{labelTipo(recurso.tipo)}</p>
              </div>
            </div>
            <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
              <MiniMetric label="Cap." value={formatNumber(recurso.capacidade_simultanea, 0)} />
              <MiniMetric
                label="Watts"
                value={recurso.potencia_watts ? formatNumber(recurso.potencia_watts, 0) : "-"}
              />
              <MiniMetric label="Manut." value={formatCurrency(recurso.custo_manutencao_hora)} />
            </div>
            <div className="mt-3 flex flex-wrap justify-end gap-2">
              <ActionButton
                icon={Power}
                intent={recurso.ativo ? "neutral" : "create"}
                tone="soft"
                size="xs"
                onClick={() => onToggleAtivo(recurso)}
              >
                {recurso.ativo ? "Desativar" : "Ativar"}
              </ActionButton>
              <ActionButton
                icon={Pencil}
                intent="edit"
                tone="soft"
                size="xs"
                onClick={() => onEdit(recurso)}
              >
                Editar
              </ActionButton>
              <ActionButton
                icon={Trash2}
                intent="delete"
                tone="soft"
                size="xs"
                onClick={() => onDelete(recurso)}
              >
                Excluir
              </ActionButton>
            </div>
          </article>
        ))}
        {recursos.length === 0 && (
          <EmptyState
            className="md:col-span-2"
            compact
            description="Cadastre o primeiro recurso para controlar capacidade e ocupacao."
            title="Nenhum recurso cadastrado"
          />
        )}
      </div>
    </Panel>
  );
}

function MiniMetric({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-0.5 font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function labelTipo(tipo) {
  const labels = {
    banheira: "Banheira",
    mesa_tosa: "Mesa de tosa",
    secador: "Secador / soprador",
    box: "Sala / box",
    veiculo: "Taxi dog / veiculo",
    outro: "Outro",
  };

  return labels[tipo] || tipo || "-";
}
