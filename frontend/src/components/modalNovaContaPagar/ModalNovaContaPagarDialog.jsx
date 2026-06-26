import { Edit3, FileText, Plus, X } from "lucide-react";
import ContaPagarBasicFields from "./ContaPagarBasicFields";
import ContaPagarParcelamentoSection from "./ContaPagarParcelamentoSection";
import ContaPagarRecorrenciaSection from "./ContaPagarRecorrenciaSection";

export default function ModalNovaContaPagarDialog({ controller, onClose, onOpenCategoria }) {
  const { dados, fecharComReset, handleSubmit, isEditando, loading, setDados } = controller;

  return (
    <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full m-4 max-h-[90vh] overflow-y-auto">
      <div className="flex justify-between items-center p-6 border-b sticky top-0 bg-white">
        <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          {isEditando ? <Edit3 className="text-blue-600" /> : <Plus className="text-red-600" />}
          {isEditando ? "Editar Conta a Pagar" : "Nova Conta a Pagar"}
        </h2>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
          <X size={24} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        <section className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-700 flex items-center gap-2">
            <FileText size={20} className="text-blue-600" />
            Informações Básicas
          </h3>
          <ContaPagarBasicFields controller={controller} onOpenCategoria={onOpenCategoria} />
        </section>

        <ContaPagarRecorrenciaSection controller={controller} />
        <ContaPagarParcelamentoSection controller={controller} />

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
          <textarea
            value={dados.observacoes}
            onChange={(event) => setDados({ ...dados, observacoes: event.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            rows="3"
            placeholder="Informações adicionais..."
          />
        </div>

        <div className="flex justify-end gap-3 border-t pt-4">
          <button
            type="button"
            onClick={fecharComReset}
            className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? "Salvando..." : isEditando ? "Salvar Alterações" : "Salvar Conta"}
          </button>
        </div>
      </form>
    </div>
  );
}
