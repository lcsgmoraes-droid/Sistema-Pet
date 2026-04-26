export default function ProcedimentoDadosForm({ form, setCampo }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className="md:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Nome *</label>
        <input
          type="text"
          value={form.nome}
          onChange={(event) => setCampo("nome", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Categoria</label>
        <input
          type="text"
          value={form.categoria}
          onChange={(event) => setCampo("categoria", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder="Consulta, coleta, curativo..."
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Duracao (min)</label>
        <input
          type="number"
          value={form.duracao}
          onChange={(event) => setCampo("duracao", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Preco sugerido (R$)</label>
        <input
          type="text"
          value={form.preco}
          onChange={(event) => setCampo("preco", event.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder="0,00"
        />
      </div>
      <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm">
        <input
          type="checkbox"
          checked={form.requer_anestesia}
          onChange={(event) => setCampo("requer_anestesia", event.target.checked)}
        />
        Requer anestesia
      </label>
      <div className="md:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Descricao</label>
        <textarea
          value={form.descricao}
          onChange={(event) => setCampo("descricao", event.target.value)}
          className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
      <div className="md:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Observacoes internas</label>
        <textarea
          value={form.observacoes}
          onChange={(event) => setCampo("observacoes", event.target.value)}
          className="min-h-[72px] w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        />
      </div>
    </div>
  );
}
