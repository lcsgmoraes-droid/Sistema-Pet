import RegistrarVacinaCamposSection from "./RegistrarVacinaCamposSection";
import RegistrarVacinaSugestaoProtocolo from "./RegistrarVacinaSugestaoProtocolo";
import RegistrarVacinaTutorPetSection from "./RegistrarVacinaTutorPetSection";

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
            Esta vacina sera vinculada a consulta <strong>#{consultaId}</strong>.
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <RegistrarVacinaTutorPetSection
            form={form}
            onBeforeNovoPet={onBeforeNovoPet}
            onSelecionarTutor={onSelecionarTutor}
            onSetCampo={onSetCampo}
            petsDaPessoa={petsDaPessoa}
            retornoNovoPet={retornoNovoPet}
            tutorFormSelecionado={tutorFormSelecionado}
          />

          <RegistrarVacinaSugestaoProtocolo
            form={form}
            onSetCampo={onSetCampo}
            sugestaoDose={sugestaoDose}
          />

          <RegistrarVacinaCamposSection
            form={form}
            onSetCampo={onSetCampo}
            veterinarios={veterinarios}
          />
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
