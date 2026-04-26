export default function CalculadoraDoseFields({
  css,
  petSelecionadoLabel,
  calculadoraForm,
  setCalculadoraForm,
  medicamentosCatalogo,
  medicamentoSelecionado,
}) {
  return (
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
          <option value="">Selecione...</option>
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
            Faixa do catálogo: {medicamentoSelecionado?.dose_minima_mg_kg || "-"}
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
  );
}
