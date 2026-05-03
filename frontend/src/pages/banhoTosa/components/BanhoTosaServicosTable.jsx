import { Scissors } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import Panel from "../../../components/ui/Panel";
import StatusBadge from "../../../components/ui/StatusBadge";
import { formatCurrency } from "../banhoTosaUtils";

export default function BanhoTosaServicosTable({
  servicos,
  onEdit,
  onDelete,
  onToggleAtivo,
}) {
  return (
    <Panel
      actions={<StatusBadge intent="info">{servicos.length} itens</StatusBadge>}
      subtitle="Use editar para ajustar o catalogo e inativar para preservar historico."
      title="Lista operacional"
    >
      {servicos.length === 0 ? (
        <EmptyState
          compact
          description="Cadastre o primeiro servico para usar na agenda, pacotes e fechamentos."
          icon={Scissors}
          title="Nenhum servico cadastrado"
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
            <tr>
              <th className="px-4 py-3">Servico</th>
              <th className="px-4 py-3">Categoria</th>
              <th className="px-4 py-3">Duracao</th>
              <th className="px-4 py-3">Preco base</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Acoes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {servicos.map((servico) => (
              <tr key={servico.id}>
                <td className="px-4 py-3 font-bold text-slate-900">{servico.nome}</td>
                <td className="px-4 py-3 text-slate-600">{servico.categoria}</td>
                <td className="px-4 py-3 text-slate-600">{servico.duracao_padrao_minutos} min</td>
                <td className="px-4 py-3 font-bold text-emerald-700">{formatCurrency(servico.preco_base)}</td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onToggleAtivo(servico)}
                    className="inline-flex"
                  >
                    <StatusBadge status={servico.ativo ? "ativo" : "inativo"} />
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    <ActionButton intent="edit" tone="soft" size="xs" onClick={() => onEdit(servico)}>Editar</ActionButton>
                    <ActionButton intent="delete" tone="soft" size="xs" onClick={() => onDelete(servico)}>Excluir</ActionButton>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </Panel>
  );
}
