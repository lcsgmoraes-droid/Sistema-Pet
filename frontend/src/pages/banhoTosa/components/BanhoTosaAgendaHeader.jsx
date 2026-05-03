import { RefreshCw } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";

export default function BanhoTosaAgendaHeader({ dataRef, onAtualizar }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-base font-semibold text-slate-900">
          Agendamentos de {dataRef}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Status do atendimento no dia selecionado.
        </p>
      </div>
      <ActionButton icon={RefreshCw} intent="neutral" onClick={onAtualizar} tone="soft">
        Atualizar
      </ActionButton>
    </div>
  );
}
