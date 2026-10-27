import toast from "react-hot-toast";
import { Pencil, Power, Trash2 } from "lucide-react";
import BotaoMenuAcoes from "../../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import EmptyState from "../../../components/ui/EmptyState";
import Panel from "../../../components/ui/Panel";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../banhoTosaUtils";

export default function BanhoTosaPacotesList({ pacotes = [], onChanged, onEdit, onDelete }) {
  async function toggleAtivo(pacote) {
    try {
      await banhoTosaApi.atualizarPacote(pacote.id, { ativo: !pacote.ativo });
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível atualizar o pacote."));
    }
  }
  return (
    <Panel
      actions={
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {pacotes.length} itens
        </span>
      }
      subtitle="Modelos de pacote com os serviços e quantidades para cada nova contratação."
      title="Catálogo de pacotes"
    >
      <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-700">
        {pacotes.map((pacote) => (
          <div
            key={pacote.id}
            className="grid gap-3 p-3 md:grid-cols-[auto_1.3fr_0.7fr_0.7fr] md:items-center"
          >
            <BotaoMenuAcoes
              rotulo={`Ações do pacote ${pacote.nome}`}
              acoes={[
                { icon: Pencil, label: "Editar", onClick: () => onEdit?.(pacote) },
                {
                  icon: Power,
                  label: pacote.ativo ? "Desativar" : "Ativar",
                  onClick: () => toggleAtivo(pacote),
                },
                {
                  icon: Trash2,
                  label: "Excluir",
                  tom: "perigo",
                  onClick: () => onDelete?.(pacote),
                },
              ]}
            />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-slate-900 dark:text-slate-100">{pacote.nome}</p>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${pacote.ativo ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"}`}
                >
                  {pacote.ativo ? "Ativo" : "Inativo"}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {pacote.servicos?.length
                  ? pacote.servicos
                      .map(
                        (item) =>
                          `${formatNumber(item.quantidade_creditos, 0)} × ${item.servico_nome || "serviço"}`,
                      )
                      .join(" · ")
                  : pacote.servico_nome || "Qualquer serviço (legado)"}
                {` · ${pacote.validade_dias} dias`}
              </p>
            </div>
            <Info label="Serviços no pacote" value={formatNumber(pacote.quantidade_creditos, 0)} />
            <Info label="Preço" value={formatCurrency(pacote.preco)} />
          </div>
        ))}
        {pacotes.length === 0 && (
          <EmptyState
            compact
            description="Crie o primeiro pacote para vincular serviços aos pets dos clientes."
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
      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{value}</p>
    </div>
  );
}
