import { CalendarPlus } from "lucide-react";

import { css, formatDateTimeBR } from "./consultaFormUtils";

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
  consultaIdAtual,
  modoSomenteLeitura,
  form,
  onAgendarRetorno,
  setCampo,
}) {
  const retornoAgendado = form.retorno_agendado;

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
      <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-gray-700">
            {retornoAgendado ? "Retorno agendado" : "Retorno"}
          </p>
          <p className="text-xs text-gray-500">
            {retornoAgendado
              ? formatDateTimeBR(retornoAgendado.data_hora)
              : "Escolha o dia e horario livre na agenda."}
          </p>
        </div>
        <button
          type="button"
          onClick={onAgendarRetorno}
          disabled={!consultaIdAtual || modoSomenteLeitura}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-blue-200 bg-white px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
          title={!consultaIdAtual ? "Salve a consulta em rascunho antes de agendar retorno" : ""}
        >
          <CalendarPlus size={16} />
          {retornoAgendado ? "Alterar retorno" : "Agendar retorno"}
        </button>
      </div>
      {campo("Observações adicionais")(
        <textarea value={form.observacoes} onChange={(e) => setCampo("observacoes", e.target.value)} className={css.textarea} placeholder="Observações para o tutor, cuidados especiais..." />
      )}
    </fieldset>
  );
}
