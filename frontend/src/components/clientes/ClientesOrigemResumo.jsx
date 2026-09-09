import ClienteOrigemSelect from "./ClienteOrigemSelect";

export default function ClientesOrigemResumo({ filtros, onChange, resumo, loading }) {
  const total = resumo.reduce((soma, item) => soma + item.total, 0);
  return (
    <section
      className="mb-5 rounded-xl border border-slate-200 bg-white p-4"
      aria-label="Clientes por origem"
    >
      <h2 className="font-semibold text-slate-900">Clientes por origem</h2>
      <p className="mt-1 text-sm text-slate-500">
        Filtre pela origem e pela data de cadastro do cliente.
      </p>
      <div className="mt-3 grid items-end gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <ClienteOrigemSelect
          filtro
          value={filtros.origem}
          onChange={(origem) => onChange({ ...filtros, origem })}
        />
        <label className="text-sm font-medium text-slate-700">
          Cadastrados a partir de
          <input
            type="date"
            value={filtros.inicio}
            max={filtros.fim || undefined}
            onChange={(event) => onChange({ ...filtros, inicio: event.target.value })}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3"
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Cadastrados até
          <input
            type="date"
            value={filtros.fim}
            min={filtros.inicio || undefined}
            onChange={(event) => onChange({ ...filtros, fim: event.target.value })}
            className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3"
          />
        </label>
        <button
          type="button"
          onClick={() => onChange({ origem: "", inicio: "", fim: "" })}
          className="h-10 rounded-lg border border-slate-300 text-sm text-slate-700"
        >
          Limpar filtros de origem e data
        </button>
      </div>
      <details className="mt-4" open>
        <summary className="cursor-pointer text-sm font-medium text-slate-700">
          Resumo por origem
        </summary>
        {loading ? (
          <p role="status" className="mt-2 text-sm text-slate-500">
            Atualizando resumo...
          </p>
        ) : (
          <>
            <table className="mt-2 w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2">Origem</th>
                  <th className="text-right">Clientes</th>
                  <th className="text-right">Participação</th>
                </tr>
              </thead>
              <tbody>
                {resumo.map((item) => (
                  <tr key={item.origem || "nao_identificada"} className="border-b border-slate-100">
                    <td className="py-2 text-slate-700">{item.nome}</td>
                    <td className="text-right">{item.total.toLocaleString("pt-BR")}</td>
                    <td className="text-right">
                      {(total ? item.total / total : 0).toLocaleString("pt-BR", {
                        style: "percent",
                        maximumFractionDigits: 1,
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="font-semibold">
                  <td className="pt-2">Total</td>
                  <td className="pt-2 text-right">{total.toLocaleString("pt-BR")}</td>
                  <td />
                </tr>
              </tfoot>
            </table>
            <p className="mt-2 text-xs text-slate-500">
              Considera os clientes da consulta em todas as páginas. Sem período informado,
              considera todas as datas de cadastro.
            </p>
          </>
        )}
      </details>
    </section>
  );
}
