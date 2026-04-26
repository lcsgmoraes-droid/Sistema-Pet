export default function BanhoTosaServicosTable({
  servicos,
  onEdit,
  onDelete,
  onToggleAtivo,
}) {
  return (
    <div className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Servicos
          </p>
          <h2 className="mt-2 text-xl font-black text-slate-900">
            Lista operacional
          </h2>
        </div>
        <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">
          {servicos.length} itens
        </span>
      </div>

      <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
            <tr>
              <th className="px-4 py-3">Servico</th>
              <th className="px-4 py-3">Categoria</th>
              <th className="px-4 py-3">Duracao</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Acoes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {servicos.map((servico) => (
              <tr key={servico.id}>
                <td className="px-4 py-3 font-bold text-slate-900">{servico.nome}</td>
                <td className="px-4 py-3 text-slate-600">{servico.categoria}</td>
                <td className="px-4 py-3 text-slate-600">{servico.duracao_padrao_minutos} min</td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onToggleAtivo(servico)}
                    className={`rounded-full px-3 py-1 text-xs font-bold ${
                      servico.ativo
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {servico.ativo ? "Ativo" : "Inativo"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    <ActionButton onClick={() => onEdit(servico)}>Editar</ActionButton>
                    <ActionButton danger onClick={() => onDelete(servico)}>Excluir</ActionButton>
                  </div>
                </td>
              </tr>
            ))}
            {servicos.length === 0 && (
              <tr>
                <td className="px-4 py-8 text-center text-slate-500" colSpan={5}>
                  Nenhum servico cadastrado ainda.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ActionButton({ children, danger = false, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-black transition ${
        danger
          ? "bg-red-50 text-red-700 hover:bg-red-100"
          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      }`}
    >
      {children}
    </button>
  );
}
