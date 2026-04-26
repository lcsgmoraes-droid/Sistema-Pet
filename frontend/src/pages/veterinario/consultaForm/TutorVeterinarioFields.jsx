export default function TutorVeterinarioFields({
  isEdicao,
  form,
  setCampo,
  css,
  renderCampo,
  buscaTutor,
  setBuscaTutor,
  tutorSelecionado,
  setTutorSelecionado,
  tutoresSugeridos,
  selecionarTutor,
  limparTutor,
  veterinarios,
}) {
  function handleBuscaTutorChange(event) {
    setBuscaTutor(event.target.value);
    if (tutorSelecionado) {
      setTutorSelecionado(null);
      setCampo("pet_id", "");
    }
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {renderCampo("Tutor (nome/telefone)", true)(
        <div className="relative">
          <input
            type="text"
            value={buscaTutor}
            onChange={handleBuscaTutorChange}
            placeholder="Digite nome ou telefone do tutor..."
            className={css.input}
            disabled={isEdicao}
          />
          {!isEdicao && tutorSelecionado && (
            <button
              type="button"
              onClick={limparTutor}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700"
            >
              limpar
            </button>
          )}

          {!isEdicao && buscaTutor.trim().length >= 1 && !tutorSelecionado && tutoresSugeridos.length > 0 && (
            <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
              {tutoresSugeridos.map((tutor) => (
                <button
                  key={tutor.id}
                  type="button"
                  onClick={() => selecionarTutor(tutor)}
                  className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b last:border-b-0"
                >
                  <div className="text-sm font-medium text-gray-800">{tutor.nome}</div>
                  <div className="text-xs text-gray-500">
                    {[tutor.telefone, tutor.celular].filter(Boolean).join(" • ") || "Sem telefone"}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {renderCampo("Veterinário")(
        <select value={form.veterinario_id} onChange={(event) => setCampo("veterinario_id", event.target.value)} className={css.select}>
          <option value="">Selecione...</option>
          {veterinarios.map((veterinario) => (
            <option key={veterinario.id} value={veterinario.id}>{veterinario.nome}</option>
          ))}
        </select>
      )}
    </div>
  );
}
