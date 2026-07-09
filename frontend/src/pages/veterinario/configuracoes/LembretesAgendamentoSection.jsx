import { Bell } from "lucide-react";

export default function LembretesAgendamentoSection({
  form,
  onChangeForm,
  onSave,
  salvando,
}) {
  if (!form) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between p-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Bell size={20} className="text-blue-500" />
          <h2 className="text-lg font-semibold text-gray-900">Lembretes de agendamento</h2>
        </div>
        <button
          onClick={onSave}
          disabled={salvando}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {salvando ? "Salvando..." : "Salvar"}
        </button>
      </div>

      <div className="p-5 space-y-4">
        <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-700">
          <input
            type="checkbox"
            checked={Boolean(form.lembretes_agendamento_ativos)}
            onChange={(event) =>
              onChangeForm({ lembretes_agendamento_ativos: event.target.checked })
            }
            className="h-4 w-4 accent-blue-600"
          />
          Enviar lembretes no app
        </label>

        <div className="grid grid-cols-1 sm:grid-cols-[auto_auto_140px] gap-4">
          <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-700">
            <input
              type="checkbox"
              checked={Boolean(form.lembrete_agendamento_1d_ativo)}
              onChange={(event) =>
                onChangeForm({ lembrete_agendamento_1d_ativo: event.target.checked })
              }
              className="h-4 w-4 accent-blue-600"
            />
            1 dia antes
          </label>
          <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-700">
            <input
              type="checkbox"
              checked={Boolean(form.lembrete_agendamento_horas_ativo)}
              onChange={(event) =>
                onChangeForm({ lembrete_agendamento_horas_ativo: event.target.checked })
              }
              className="h-4 w-4 accent-blue-600"
            />
            No dia
          </label>
          <label className="block">
            <span className="block text-xs font-medium text-gray-600 mb-1">Horas antes</span>
            <input
              type="number"
              min="1"
              max="168"
              value={form.lembrete_agendamento_horas_antes}
              onChange={(event) =>
                onChangeForm({ lembrete_agendamento_horas_antes: event.target.value })
              }
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </label>
        </div>
      </div>
    </div>
  );
}
