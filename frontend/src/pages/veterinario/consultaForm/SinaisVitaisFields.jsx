export default function SinaisVitaisFields({
  form,
  setCampo,
  css,
  renderCampo,
}) {
  return (
    <>
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
            <option value="">-</option>
            <option>Rósea</option><option>Pálida</option><option>Ictérica</option>
            <option>Cianótica</option><option>Hiperêmica</option>
          </select>
        )}
        {renderCampo("Hidratação")(
          <select value={form.estado_hidratacao} onChange={(event) => setCampo("estado_hidratacao", event.target.value)} className={css.select}>
            <option value="">-</option>
            <option>Normal</option><option>Leve desidratação</option>
            <option>Moderada desidratação</option><option>Grave desidratação</option>
          </select>
        )}
        {renderCampo("Consciência")(
          <select value={form.nivel_consciencia} onChange={(event) => setCampo("nivel_consciencia", event.target.value)} className={css.select}>
            <option value="">-</option>
            <option>Alerta</option><option>Deprimido</option><option>Estupor</option><option>Coma</option>
          </select>
        )}
        {renderCampo("Dor (0-10)")(
          <input type="number" min={0} max={10} value={form.nivel_dor} onChange={(event) => setCampo("nivel_dor", event.target.value)} className={css.input} placeholder="0 = sem dor" />
        )}
      </div>
    </>
  );
}
