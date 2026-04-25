import { X } from "lucide-react";
import ProdutoEstoqueAutocomplete from "../../../components/veterinario/ProdutoEstoqueAutocomplete";

export default function InsumoRapidoModal({
  isOpen,
  onClose,
  css,
  consultaIdAtual,
  petSelecionadoLabel,
  insumoSelecionado,
  setInsumoSelecionado,
  insumoForm,
  setInsumoForm,
  salvarInsumo,
  salvandoInsumo,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Lançar insumo rápido</h2>
            <p className="text-sm text-gray-500">
              Consulta #{consultaIdAtual || "—"} • {petSelecionadoLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar modal de insumo"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4">
          <ProdutoEstoqueAutocomplete
            selectedProduct={insumoSelecionado}
            onSelect={setInsumoSelecionado}
            helperText="Pesquise o material, medicamento ou item de consumo usado durante a consulta."
          />

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Quantidade utilizada *</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={insumoForm.quantidade_utilizada}
                onChange={(e) => setInsumoForm((prev) => ({ ...prev, quantidade_utilizada: e.target.value }))}
                className={css.input}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Desperdício / perda</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={insumoForm.quantidade_desperdicio}
                onChange={(e) => setInsumoForm((prev) => ({ ...prev, quantidade_desperdicio: e.target.value }))}
                className={css.input}
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Observações</label>
            <textarea
              value={insumoForm.observacoes}
              onChange={(e) => setInsumoForm((prev) => ({ ...prev, observacoes: e.target.value }))}
              rows={4}
              className={css.textarea}
              placeholder="Ex.: usado 1 tapete agora e outro precisou ser descartado, bolsa de soro conectada, desinfecção do campo..."
            />
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={salvarInsumo}
            disabled={salvandoInsumo}
            className="flex-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {salvandoInsumo ? "Salvando..." : "Registrar insumo"}
          </button>
        </div>
      </div>
    </div>
  );
}
