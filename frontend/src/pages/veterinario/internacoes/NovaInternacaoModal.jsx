import TutorAutocomplete from "../../../components/TutorAutocomplete";
import NovoPetButton from "../../../components/veterinario/NovoPetButton";

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
        <h2 className="font-bold text-gray-800">Nova internação</h2>
        <div className="space-y-3">
          {consultaIdQuery && (
            <div className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm text-purple-800">
              Esta internação ficará vinculada à consulta <strong>#{consultaIdQuery}</strong>.
            </div>
          )}
          <div>
            <TutorAutocomplete
              label="Pessoa (tutor) *"
              inputId="internacao-tutor"
              selectedTutor={tutorNovaSelecionado}
              onSelect={(cliente) => {
                setTutorNovaSelecionado(cliente);
                setFormNova((prev) => ({
                  ...prev,
                  pessoa_id: cliente?.id ? String(cliente.id) : "",
                  pet_id: "",
                }));
              }}
            />
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between gap-2">
              <label className="block text-xs font-medium text-gray-600">Pet da pessoa *</label>
              <NovoPetButton
                tutorId={formNova.pessoa_id}
                tutorNome={tutorAtualInternacao?.nome}
                returnTo={retornoNovoPet}
                onBeforeNavigate={onHideForNovoPet}
              />
            </div>
            <select
              value={formNova.pet_id}
              onChange={(e) => setFormNova((p) => ({ ...p, pet_id: e.target.value }))}
              disabled={!formNova.pessoa_id}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white disabled:opacity-60"
            >
              <option value="">Selecione...</option>
              {petsDaPessoa.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome}{p.especie ? ` (${p.especie})` : ""}
                </option>
              ))}
            </select>
            {formNova.pessoa_id && petsDaPessoa.length === 0 && (
              <p className="mt-2 text-xs text-amber-600">Nenhum pet ativo encontrado para esta pessoa.</p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Motivo da internação *</label>
            <textarea
              value={formNova.motivo}
              onChange={(e) => setFormNova((p) => ({ ...p, motivo: e.target.value }))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-20"
            />
          </div>
          <div>
            <div className="flex items-end justify-between mb-2">
              <label className="block text-xs font-medium text-gray-600">Mapa de baias (selecione uma livre) *</label>
              <div className="w-28">
                <input
                  type="number"
                  min="1"
                  max="200"
                  value={totalBaias}
                  onChange={(e) => {
                    const valor = Number.parseInt(e.target.value || "0", 10);
                    if (!Number.isFinite(valor)) return;
                    setTotalBaias(Math.max(1, Math.min(200, valor)));
                  }}
                  className="w-full border border-gray-200 rounded-lg px-2 py-1 text-xs"
                  title="Total de baias"
                />
              </div>
            </div>
            <div className="border border-gray-200 rounded-lg p-2 max-h-44 overflow-auto">
              <div className="grid grid-cols-3 gap-2">
                {mapaInternacao
                  .filter((baia) => Number.isFinite(Number.parseInt(String(baia.numero), 10)))
                  .sort((a, b) => Number(a.numero) - Number(b.numero))
                  .map((baia) => {
                    const numero = String(baia.numero);
                    const ocupadaPorOutro = baia.ocupada;
                    const selecionada = formNova.box === numero;
                    return (
                      <button
                        key={`nova_baia_${numero}`}
                        type="button"
                        disabled={ocupadaPorOutro}
                        onClick={() => setFormNova((p) => ({ ...p, box: numero }))}
                        className={`rounded-md border px-2 py-2 text-left transition-colors ${
                          ocupadaPorOutro
                            ? "bg-red-50 border-red-200 text-red-700 cursor-not-allowed"
                            : selecionada
                            ? "bg-purple-600 border-purple-600 text-white"
                            : "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
                        }`}
                      >
                        <p className="text-xs font-bold">Baia {numero}</p>
                        <p className="text-[11px] truncate">
                          {ocupadaPorOutro ? (baia.internacao?.pet_nome ?? "Ocupada") : "Disponível"}
                        </p>
                      </button>
                    );
                  })}
              </div>
            </div>
            <p className="text-xs mt-1 text-gray-500">
              Selecionada: <span className="font-semibold text-gray-800">{formNova.box || "nenhuma"}</span>
            </p>
          </div>
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
