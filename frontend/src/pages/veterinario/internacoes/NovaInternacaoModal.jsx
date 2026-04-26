import NovaInternacaoBaiasSection from "./NovaInternacaoBaiasSection";
import NovaInternacaoTutorPetSection from "./NovaInternacaoTutorPetSection";

export default function NovaInternacaoModal({
  isOpen,
  consultaIdQuery,
  tutorNovaSelecionado,
  setTutorNovaSelecionado,
  formNova,
  setFormNova,
  tutorAtualInternacao,
  retornoNovoPet,
  petsDaPessoa,
  mapaInternacao,
  totalBaias,
  setTotalBaias,
  onClose,
  onHideForNovoPet,
  onConfirm,
  salvando,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-bold text-gray-800">Nova internacao</h2>
        <div className="space-y-3">
          {consultaIdQuery && (
            <div className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm text-purple-800">
              Esta internacao ficara vinculada a consulta <strong>#{consultaIdQuery}</strong>.
            </div>
          )}

          <NovaInternacaoTutorPetSection
            formNova={formNova}
            onHideForNovoPet={onHideForNovoPet}
            petsDaPessoa={petsDaPessoa}
            retornoNovoPet={retornoNovoPet}
            setFormNova={setFormNova}
            setTutorNovaSelecionado={setTutorNovaSelecionado}
            tutorAtualInternacao={tutorAtualInternacao}
            tutorNovaSelecionado={tutorNovaSelecionado}
          />

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Motivo da internacao *</label>
            <textarea
              value={formNova.motivo}
              onChange={(event) => setFormNova((prev) => ({ ...prev, motivo: event.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20"
            />
          </div>

          <NovaInternacaoBaiasSection
            formNova={formNova}
            mapaInternacao={mapaInternacao}
            setFormNova={setFormNova}
            setTotalBaias={setTotalBaias}
            totalBaias={totalBaias}
          />
        </div>
        <div className="flex gap-3 pt-1">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={salvando || !formNova.pet_id || !formNova.motivo}
            className="flex-1 px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-60"
          >
            {salvando ? "Salvando..." : "Internar"}
          </button>
        </div>
      </div>
    </div>
  );
}
