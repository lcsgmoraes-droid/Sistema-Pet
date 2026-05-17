import AutocompleteSelect from "../../../components/ui/AutocompleteSelect";

const OPCOES_MUCOSA = [
  { value: "R\u00f3sea", label: "R\u00f3sea" },
  { value: "P\u00e1lida", label: "P\u00e1lida" },
  { value: "Ict\u00e9rica", label: "Ict\u00e9rica" },
  { value: "Cian\u00f3tica", label: "Cian\u00f3tica" },
  { value: "Hiper\u00eamica", label: "Hiper\u00eamica" },
];

const OPCOES_HIDRATACAO = [
  { value: "Normal", label: "Normal" },
  { value: "Leve desidrata\u00e7\u00e3o", label: "Leve desidrata\u00e7\u00e3o" },
  { value: "Moderada desidrata\u00e7\u00e3o", label: "Moderada desidrata\u00e7\u00e3o" },
  { value: "Grave desidrata\u00e7\u00e3o", label: "Grave desidrata\u00e7\u00e3o" },
];

const OPCOES_CONSCIENCIA = [
  { value: "Alerta", label: "Alerta" },
  { value: "Deprimido", label: "Deprimido" },
  { value: "Estupor", label: "Estupor" },
  { value: "Coma", label: "Coma" },
];

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
        {renderCampo("Temperatura (\u00b0C)")(
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
          <AutocompleteSelect
            value={form.mucosa}
            onChange={(valor) => setCampo("mucosa", valor)}
            options={OPCOES_MUCOSA}
            placeholder="Digite para buscar..."
            emptyLabel="Nenhuma mucosa encontrada"
            showLabel={false}
          />
        )}
        {renderCampo("Hidrata\u00e7\u00e3o")(
          <AutocompleteSelect
            value={form.estado_hidratacao}
            onChange={(valor) => setCampo("estado_hidratacao", valor)}
            options={OPCOES_HIDRATACAO}
            placeholder="Digite para buscar..."
            emptyLabel={"Nenhuma hidrata\u00e7\u00e3o encontrada"}
            showLabel={false}
          />
        )}
        {renderCampo("Consci\u00eancia")(
          <AutocompleteSelect
            value={form.nivel_consciencia}
            onChange={(valor) => setCampo("nivel_consciencia", valor)}
            options={OPCOES_CONSCIENCIA}
            placeholder="Digite para buscar..."
            emptyLabel={"Nenhum n\u00edvel encontrado"}
            showLabel={false}
          />
        )}
        {renderCampo("Dor (0-10)")(
          <input type="number" min={0} max={10} value={form.nivel_dor} onChange={(event) => setCampo("nivel_dor", event.target.value)} className={css.input} placeholder="0 = sem dor" />
        )}
      </div>
    </>
  );
}
