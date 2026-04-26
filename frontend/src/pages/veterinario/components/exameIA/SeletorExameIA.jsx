export default function SeletorExameIA({ exameId, exames, onChange }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-indigo-700">Exame para consultar</label>
      <select
        value={exameId}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
      >
        <option value="">Selecione um exame...</option>
        {exames.map((exame) => (
          <option key={exame.id} value={exame.id}>
            #{exame.id} - {exame.nome || exame.tipo || "Exame"}
            {exame.data_solicitacao ? ` - ${exame.data_solicitacao}` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
