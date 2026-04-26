import NovoPetButton from "../../../components/veterinario/NovoPetButton";

export default function PetConsultaSelector({
  isEdicao,
  form,
  setCampo,
  renderCampo,
  tutorSelecionado,
  listaPetsExpandida,
  setListaPetsExpandida,
  petSelecionadoLabel,
  petsDoTutor,
  abrirModalNovoPet,
}) {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          {renderCampo("Pet", true)(
            <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
              <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-3 py-2">
                <button
                  type="button"
                  onClick={() => tutorSelecionado && setListaPetsExpandida((prev) => !prev)}
                  disabled={!tutorSelecionado || isEdicao}
                  className="flex-1 text-left text-sm disabled:opacity-60"
                >
                  <span>{petSelecionadoLabel}</span>
                </button>
                <NovoPetButton
                  tutorId={tutorSelecionado?.id}
                  tutorNome={tutorSelecionado?.nome}
                  onClick={abrirModalNovoPet}
                />
                <span className="text-gray-500 text-xs">
                  {tutorSelecionado ? `${petsDoTutor.length} pet(s)` : "Sem tutor"}
                </span>
              </div>

              {listaPetsExpandida && tutorSelecionado && !isEdicao && (
                <div className="border-t border-gray-200 max-h-52 overflow-y-auto p-2 space-y-1">
                  {petsDoTutor.map((pet) => {
                    const ativo = String(form.pet_id) === String(pet.id);
                    return (
                      <button
                        key={pet.id}
                        type="button"
                        onClick={() => {
                          setCampo("pet_id", pet.id);
                          setListaPetsExpandida(false);
                        }}
                        className={`w-full text-left px-2.5 py-2 rounded text-sm transition-colors ${
                          ativo ? "bg-blue-50 border border-blue-200 text-blue-700" : "hover:bg-gray-50"
                        }`}
                      >
                        <div className="font-medium">{pet.nome}</div>
                        <div className="text-xs text-gray-500">
                          {pet.especie && !/\?/.test(pet.especie) ? pet.especie : "Pet"}
                          {pet.codigo ? ` • ${pet.codigo}` : ""}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {!isEdicao && tutorSelecionado && petsDoTutor.length === 0 && (
        <p className="text-xs text-amber-600">
          Nenhum pet ativo vinculado a esse tutor.
        </p>
      )}
    </>
  );
}
