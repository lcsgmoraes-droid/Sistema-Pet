import { X } from "lucide-react";

export default function CalculadoraDoseModal({
  isOpen,
  onClose,
  css,
  petSelecionadoLabel,
  calculadoraForm,
  setCalculadoraForm,
  medicamentosCatalogo,
  medicamentoSelecionado,
  resultado,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Calculadora rápida de dose</h2>
            <p className="text-sm text-gray-500">
              Modal livre para cálculo rápido durante a consulta.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Fechar calculadora"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Pet</label>
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
              {petSelecionadoLabel}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Peso atual (kg)</label>
            <input
              type="number"
              step="0.01"
              value={calculadoraForm.peso_kg}
              onChange={(e) => setCalculadoraForm((prev) => ({ ...prev, peso_kg: e.target.value }))}
              className={css.input}
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-gray-600">Medicamento</label>
            <select
              value={calculadoraForm.medicamento_id}
              onChange={(e) => {
                setCalculadoraForm((prev) => ({
                  ...prev,
                  medicamento_id: e.target.value,
                  dose_mg_kg: "",
                }));
              }}
              className={css.select}
            >
              <option value="">Selecione…</option>
              {medicamentosCatalogo.map((med) => (
                <option key={med.id} value={med.id}>
                  {med.nome}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Dose (mg/kg)</label>
            <input
              type="number"
              step="0.01"
              value={calculadoraForm.dose_mg_kg}
              onChange={(e) => setCalculadoraForm((prev) => ({ ...prev, dose_mg_kg: e.target.value }))}
              className={css.input}
            />
            {(medicamentoSelecionado?.dose_minima_mg_kg || medicamentoSelecionado?.dose_maxima_mg_kg) && (
              <p className="mt-1 text-[11px] text-gray-500">
                Faixa do catálogo: {medicamentoSelecionado?.dose_minima_mg_kg || "—"}
                {medicamentoSelecionado?.dose_maxima_mg_kg
                  ? ` a ${medicamentoSelecionado.dose_maxima_mg_kg}`
                  : ""} mg/kg
              </p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Frequência (horas)</label>
            <input
              type="number"
              min="1"
              value={calculadoraForm.frequencia_horas}
              onChange={(e) => setCalculadoraForm((prev) => ({ ...prev, frequencia_horas: e.target.value }))}
              className={css.input}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Dias de tratamento</label>
            <input
              type="number"
              min="1"
              value={calculadoraForm.dias}
              onChange={(e) => setCalculadoraForm((prev) => ({ ...prev, dias: e.target.value }))}
              className={css.input}
            />
          </div>
        </div>

        <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50 p-4">
          {!resultado ? (
            <p className="text-sm text-cyan-700">
              Informe peso e dose para calcular. Se quiser, você ainda pode abrir a calculadora completa depois.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <div>
                <p className="text-[11px] uppercase tracking-wide text-cyan-600">mg por dose</p>
                <p className="text-lg font-semibold text-cyan-900">{resultado.mgPorDose.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wide text-cyan-600">doses / dia</p>
                <p className="text-lg font-semibold text-cyan-900">
                  {resultado.dosesPorDia ? resultado.dosesPorDia.toFixed(2) : "—"}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wide text-cyan-600">mg / dia</p>
                <p className="text-lg font-semibold text-cyan-900">
                  {resultado.mgDia ? resultado.mgDia.toFixed(2) : "—"}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wide text-cyan-600">mg tratamento</p>
                <p className="text-lg font-semibold text-cyan-900">
                  {resultado.mgTratamento ? resultado.mgTratamento.toFixed(2) : "—"}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
