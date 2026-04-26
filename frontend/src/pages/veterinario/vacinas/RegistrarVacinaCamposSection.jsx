export default function RegistrarVacinaCamposSection({ form, onSetCampo, veterinarios }) {
  return (
    <>
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
          placeholder="Ex: V10, Antirrabica, Gripe felina..."
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
          Data de aplicacao *
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
          Proxima dose
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
          Veterinario responsavel
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
          Observacoes
        </label>
        <textarea
          id="vacinas-observacoes"
          value={form.observacoes}
          onChange={(event) => onSetCampo("observacoes", event.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16"
        />
      </div>
    </>
  );
}
