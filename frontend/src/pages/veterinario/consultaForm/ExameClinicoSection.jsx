import { FlaskConical } from "lucide-react";

import ExameChatIAAvancada from "../components/ExameChatIAAvancada";

export default function ExameClinicoSection({
  modoSomenteLeitura,
  form,
  setCampo,
  css,
  renderCampo,
  consultaIdAtual,
  refreshExamesToken,
  onNovoExame,
  abrirFluxoConsulta,
}) {
  return (
    <>
      <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
        <h2 className="font-semibold text-gray-700">Exame clínico</h2>
        {renderCampo("Histórico clínico")(
          <textarea
            value={form.historico_clinico}
            onChange={(event) => setCampo("historico_clinico", event.target.value)}
            className={css.textarea}
            placeholder="Histórico médico, cirurgias anteriores, medicações em uso…"
          />
        )}
        {renderCampo("Exame físico detalhado")(
          <textarea
            value={form.exame_fisico}
            onChange={(event) => setCampo("exame_fisico", event.target.value)}
            className={css.textarea}
            style={{ minHeight: 200 }}
            placeholder="Descrição sistemática: cabeça, tórax, abdômen, membros, pele…"
          />
        )}
      </fieldset>

      <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-blue-900">Exames ligados a esta consulta</h3>
            <p className="text-xs text-blue-700">
              Cadastre o exame já com anexo e mantenha a IA olhando o mesmo caso clínico.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onNovoExame}
              disabled={modoSomenteLeitura || !form.pet_id || !consultaIdAtual}
              className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-60"
            >
              <FlaskConical size={15} />
              Novo exame / anexo
            </button>
            {consultaIdAtual && (
              <button
                type="button"
                onClick={() => abrirFluxoConsulta("/veterinario/exames", { acao: "novo" })}
                className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100"
              >
                Ver tela de exames
              </button>
            )}
          </div>
        </div>
      </div>

      <ExameChatIAAvancada
        petId={form.pet_id}
        refreshToken={refreshExamesToken}
        onNovoExame={onNovoExame}
      />
    </>
  );
}
