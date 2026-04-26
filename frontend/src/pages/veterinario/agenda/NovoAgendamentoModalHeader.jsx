import { X } from "lucide-react";

export default function NovoAgendamentoModalHeader({ agendamentoEditandoId, onClose }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h2 className="font-bold text-gray-800">
          {agendamentoEditandoId ? "Editar agendamento" : "Novo agendamento"}
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Escolha o tipo do servico, veja a agenda do dia e abra depois o fluxo certo com pet e tutor ja prontos.
        </p>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
        aria-label="Fechar modal"
      >
        <X size={18} />
      </button>
    </div>
  );
}
