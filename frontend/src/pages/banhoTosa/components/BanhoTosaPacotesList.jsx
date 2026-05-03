import toast from "react-hot-toast";
import { Pencil, Power, Trash2 } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaPacotesList({
  pacotes = [],
  onChanged,
  onEdit,
  onDelete,
}) {
  async function toggleAtivo(pacote) {
    try {
      await banhoTosaApi.atualizarPacote(pacote.id, { ativo: !pacote.ativo });
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel atualizar o pacote."));
    }
  }

  return (
    <Panel
      actions={
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
          {pacotes.length} itens
        </span>
      }
      subtitle="Planos disponiveis para venda recorrente no banho e tosa."
      title="Catalogo de pacotes"
    >
      <div className="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
        {pacotes.map((pacote) => (
          <div key={pacote.id} className="grid gap-3 p-3 md:grid-cols-[1.3fr_0.7fr_0.7fr_auto] md:items-center">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-slate-900">{pacote.nome}</p>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  pacote.ativo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                }`}>
                  {pacote.ativo ? "Ativo" : "Inativo"}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-500">
                {pacote.servico_nome || "Qualquer servico"} | {pacote.validade_dias} dias
              </p>
            </div>
            <Info label="Creditos" value={formatNumber(pacote.quantidade_creditos, 0)} />
            <Info label="Preco" value={formatCurrency(pacote.preco)} />
            <div className="flex flex-wrap justify-start gap-2 md:justify-end">
              <ActionButton icon={Power} intent={pacote.ativo ? "neutral" : "create"} tone="soft" size="xs" onClick={() => toggleAtivo(pacote)}>
                {pacote.ativo ? "Desativar" : "Ativar"}
              </ActionButton>
              <ActionButton icon={Pencil} intent="edit" tone="soft" size="xs" onClick={() => onEdit?.(pacote)}>Editar</ActionButton>
              <ActionButton icon={Trash2} intent="delete" tone="soft" size="xs" onClick={() => onDelete?.(pacote)}>Excluir</ActionButton>
            </div>
          </div>
        ))}
        {pacotes.length === 0 && (
          <EmptyState
            compact
            description="Crie o primeiro pacote para liberar creditos recorrentes aos clientes."
            title="Nenhum pacote cadastrado"
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
      <p className="text-sm font-black text-slate-900">{value}</p>
    </div>
  );
}
