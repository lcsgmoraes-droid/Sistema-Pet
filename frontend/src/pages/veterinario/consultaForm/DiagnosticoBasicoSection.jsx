import { css } from "./consultaFormUtils";

function campo(label, obrigatorio = false) {
  return function renderCampo(children) {
    return (
      <div className="space-y-1">
        <label className="block text-xs font-medium text-gray-600">
          {label} {obrigatorio && <span className="text-red-400">*</span>}
        </label>
        {children}
      </div>
    );
  };
}

export default function DiagnosticoBasicoSection({
  modoSomenteLeitura,
  form,
  setCampo,
}) {
  return (
    <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
      <h2 className="font-semibold text-gray-700">Diagnóstico e tratamento</h2>
      {campo("Diagnóstico")(
        <textarea value={form.diagnostico} onChange={(e) => setCampo("diagnostico", e.target.value)} className={css.textarea} placeholder="Diagnóstico principal e diferenciais..." />
      )}
      {campo("Prognóstico")(
        <select value={form.prognostico} onChange={(e) => setCampo("prognostico", e.target.value)} className={css.select}>
          <option value="">-</option>
          <option>Favorável</option><option>Reservado</option><option>Grave</option><option>Desfavorável</option>
        </select>
      )}
      {campo("Tratamento prescrito")(
        <textarea value={form.tratamento} onChange={(e) => setCampo("tratamento", e.target.value)} className={css.textarea} placeholder="Protocolo terapêutico, cuidados em casa..." />
      )}
      <div className="grid grid-cols-2 gap-3">
        {campo("Retorno em (dias)")(
          <input type="number" value={form.retorno_em_dias} onChange={(e) => setCampo("retorno_em_dias", e.target.value)} className={css.input} placeholder="ex: 15" />
        )}
      </div>
      {campo("Observações adicionais")(
        <textarea value={form.observacoes} onChange={(e) => setCampo("observacoes", e.target.value)} className={css.textarea} placeholder="Observações para o tutor, cuidados especiais..." />
      )}
    </fieldset>
  );
}
