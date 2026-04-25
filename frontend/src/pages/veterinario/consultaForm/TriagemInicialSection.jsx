import NovoPetButton from "../../../components/veterinario/NovoPetButton";

export default function TriagemInicialSection({
  modoSomenteLeitura,
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
  listaPetsExpandida,
  setListaPetsExpandida,
  petSelecionadoLabel,
  petsDoTutor,
  abrirModalNovoPet,
}) {
  function handleBuscaTutorChange(event) {
    setBuscaTutor(event.target.value);
    if (tutorSelecionado) {
      setTutorSelecionado(null);
      setCampo("pet_id", "");
    }
  }

  return (
    <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
      <h2 className="font-semibold text-gray-700">Triagem inicial</h2>

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
            <option value="">Selecione…</option>
            {veterinarios.map((veterinario) => (
              <option key={veterinario.id} value={veterinario.id}>{veterinario.nome}</option>
            ))}
          </select>
        )}
      </div>

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

      {renderCampo("Motivo da consulta", true)(
        <textarea
          value={form.motivo_consulta}
          onChange={(event) => setCampo("motivo_consulta", event.target.value)}
          className={css.textarea}
          placeholder="Descreva o motivo da consulta…"
        />
      )}

      <h3 className="text-sm font-medium text-gray-500 pt-2">Sinais vitais</h3>
      <div className="grid grid-cols-3 gap-3">
        {renderCampo("Peso (kg)")(
          <input type="number" step="0.1" value={form.peso_kg} onChange={(event) => setCampo("peso_kg", event.target.value)} className={css.input} placeholder="ex: 12,5" />
        )}
        {renderCampo("Temperatura (°C)")(
          <input type="number" step="0.1" value={form.temperatura} onChange={(event) => setCampo("temperatura", event.target.value)} className={css.input} placeholder="ex: 38,5" />
        )}
        {renderCampo("FC (bpm)")(
          <input type="number" value={form.freq_cardiaca} onChange={(event) => setCampo("freq_cardiaca", event.target.value)} className={css.input} placeholder="ex: 80" />
        )}
        {renderCampo("FR (rpm)")(
          <input type="number" value={form.freq_respiratoria} onChange={(event) => setCampo("freq_respiratoria", event.target.value)} className={css.input} placeholder="ex: 20" />
        )}
        {renderCampo("TPC")(
          <input type="text" value={form.tpc} onChange={(event) => setCampo("tpc", event.target.value)} className={css.input} placeholder="ex: < 2 seg" />
        )}
        {renderCampo("Mucosa")(
          <select value={form.mucosa} onChange={(event) => setCampo("mucosa", event.target.value)} className={css.select}>
            <option value="">—</option>
            <option>Rósea</option><option>Pálida</option><option>Ictérica</option>
            <option>Cianótica</option><option>Hiperêmica</option>
          </select>
        )}
        {renderCampo("Hidratação")(
          <select value={form.estado_hidratacao} onChange={(event) => setCampo("estado_hidratacao", event.target.value)} className={css.select}>
            <option value="">—</option>
            <option>Normal</option><option>Leve desidratação</option>
            <option>Moderada desidratação</option><option>Grave desidratação</option>
          </select>
        )}
        {renderCampo("Consciência")(
          <select value={form.nivel_consciencia} onChange={(event) => setCampo("nivel_consciencia", event.target.value)} className={css.select}>
            <option value="">—</option>
            <option>Alerta</option><option>Deprimido</option><option>Estupor</option><option>Coma</option>
          </select>
        )}
        {renderCampo("Dor (0–10)")(
          <input type="number" min={0} max={10} value={form.nivel_dor} onChange={(event) => setCampo("nivel_dor", event.target.value)} className={css.input} placeholder="0 = sem dor" />
        )}
      </div>
    </fieldset>
  );
}
