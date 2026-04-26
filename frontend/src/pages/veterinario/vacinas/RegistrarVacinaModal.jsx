import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";
import { formatData } from "./vacinaUtils";

export default function RegistrarVacinaModal({
  isOpen,
  consultaId,
  tutorFormSelecionado,
  form,
  petsDaPessoa,
  sugestaoDose,
  veterinarios,
  erro,
  salvando,
  retornoNovoPet,
  onSelecionarTutor,
  onSetCampo,
  onFechar,
  onSalvar,
  onBeforeNovoPet,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <h2 className="font-bold text-gray-800">Registrar vacina</h2>
        {consultaId && (
          <div className="rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-800">
            Esta vacina será vinculada à consulta <strong>#{consultaId}</strong>.
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <TutorAutocomplete
              label="Pessoa (tutor) *"
              inputId="vacinas-tutor-form"
              selectedTutor={tutorFormSelecionado}
              onSelect={onSelecionarTutor}
            />
          </div>

          <div className="col-span-2">
            <div className="mb-1 flex items-center justify-between gap-2">
              <label htmlFor="vacinas-pet-form" className="block text-xs font-medium text-gray-600">
                Pet da pessoa *
              </label>
              <NovoPetButton
                tutorId={tutorFormSelecionado?.id || form.pessoa_id}
                tutorNome={tutorFormSelecionado?.nome}
                returnTo={retornoNovoPet}
                onBeforeNavigate={onBeforeNovoPet}
              />
            </div>
            <select
              id="vacinas-pet-form"
              value={form.pet_id}
              onChange={(event) => onSetCampo("pet_id", event.target.value)}
              disabled={!form.pessoa_id}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white disabled:opacity-60"
            >
              <option value="">Selecione...</option>
              {petsDaPessoa.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.nome}
                  {pet.especie ? ` (${pet.especie})` : ""}
                </option>
              ))}
            </select>
            {form.pessoa_id && petsDaPessoa.length === 0 && (
              <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para esta pessoa.</p>
            )}
          </div>

          {sugestaoDose?.protocolo && (
            <div className="md:col-span-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm">
              <p className="font-semibold text-emerald-800">Sugestão automática de protocolo</p>
              <p className="text-emerald-700 mt-1">
                Protocolo encontrado: {sugestaoDose.protocolo.nome}
                {sugestaoDose.protocolo.especie ? ` - ${sugestaoDose.protocolo.especie}` : ""}
              </p>
              <p className="text-emerald-700 mt-1">
                Próxima dose sugerida:{" "}
                {sugestaoDose.proximaDose ? formatData(sugestaoDose.proximaDose) : "sem cálculo automático"}
              </p>
              {sugestaoDose.proximaDose && !form.proxima_dose && (
                <button
                  type="button"
                  onClick={() => onSetCampo("proxima_dose", sugestaoDose.proximaDose)}
                  className="mt-2 inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                >
                  Usar esta sugestão
                </button>
              )}
            </div>
          )}

          <div className="col-span-2">
            <label htmlFor="vacinas-nome" className="block text-xs font-medium text-gray-600 mb-1">
              Nome da vacina *
            </label>
            <input
              id="vacinas-nome"
              type="text"
              value={form.nome_vacina}
              onChange={(event) => onSetCampo("nome_vacina", event.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              placeholder="Ex: V10, Antirrábica, Gripe felina..."
            />
          </div>

          <div>
            <label htmlFor="vacinas-fabricante" className="block text-xs font-medium text-gray-600 mb-1">
              Fabricante
            </label>
            <input
              id="vacinas-fabricante"
              type="text"
              value={form.fabricante}
              onChange={(event) => onSetCampo("fabricante", event.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label htmlFor="vacinas-lote" className="block text-xs font-medium text-gray-600 mb-1">
              Lote
            </label>
            <input
              id="vacinas-lote"
              type="text"
              value={form.lote}
              onChange={(event) => onSetCampo("lote", event.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label htmlFor="vacinas-data-aplicacao" className="block text-xs font-medium text-gray-600 mb-1">
              Data de aplicação *
            </label>
            <input
              id="vacinas-data-aplicacao"
              type="date"
              value={form.data_aplicacao}
              onChange={(event) => onSetCampo("data_aplicacao", event.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label htmlFor="vacinas-proxima-dose" className="block text-xs font-medium text-gray-600 mb-1">
              Próxima dose
            </label>
            <input
              id="vacinas-proxima-dose"
              type="date"
              value={form.proxima_dose}
              onChange={(event) => onSetCampo("proxima_dose", event.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>

          <div className="col-span-2">
            <label htmlFor="vacinas-veterinario" className="block text-xs font-medium text-gray-600 mb-1">
              Veterinário responsável
            </label>
            <select
              id="vacinas-veterinario"
              value={form.veterinario_responsavel}
              onChange={(event) => onSetCampo("veterinario_responsavel", event.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
            >
              <option value="">Selecione...</option>
              {veterinarios.map((veterinario) => (
                <option key={veterinario.id} value={veterinario.nome}>
                  {veterinario.nome}
                  {veterinario.crmv ? ` - CRMV ${veterinario.crmv}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="col-span-2">
            <label htmlFor="vacinas-observacoes" className="block text-xs font-medium text-gray-600 mb-1">
              Observações
            </label>
            <textarea
              id="vacinas-observacoes"
              value={form.observacoes}
              onChange={(event) => onSetCampo("observacoes", event.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16"
            />
          </div>
        </div>

        {erro && <p className="text-xs text-red-600">{erro}</p>}

        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onFechar}
            className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onSalvar}
            disabled={salvando || !form.pet_id || !form.nome_vacina || !form.data_aplicacao}
            className="flex-1 px-4 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Registrar"}
          </button>
        </div>
      </div>
    </div>
  );
}
