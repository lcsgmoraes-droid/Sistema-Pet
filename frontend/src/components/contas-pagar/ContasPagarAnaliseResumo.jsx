import { FileSearch } from "lucide-react";

export function PainelResumo({ titulo, valor, detalhe, destaque = "slate", onClick }) {
  const estilos = {
    slate: "border-slate-200 bg-white text-slate-900",
    amber: "border-amber-200 bg-amber-50 text-amber-950",
    blue: "border-blue-200 bg-blue-50 text-blue-950",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-950",
    red: "border-red-200 bg-red-50 text-red-950",
    violet: "border-violet-200 bg-violet-50 text-violet-950",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-[96px] rounded-lg border p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
        estilos[destaque] || estilos.slate
      }`}
    >
      <div className="text-xs font-semibold uppercase">{titulo}</div>
      <div className="mt-2 text-xl font-bold leading-tight">{valor}</div>
      <div className="mt-1 text-xs opacity-80">{detalhe}</div>
      <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold opacity-80">
        <FileSearch className="h-3.5 w-3.5" />
        Detalhes
      </div>
    </button>
  );
}

export function TabelaResumo({ grupo, titulo, subtitulo, itens, formatarMoeda, onDetalhes }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-900">{titulo}</h3>
        <p className="text-xs text-slate-500">{subtitulo}</p>
      </div>
      <div className="max-h-[340px] overflow-auto">
        {itens.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-slate-500">Sem dados no filtro.</div>
        ) : (
          <table className="min-w-full divide-y divide-slate-100">
            <tbody className="divide-y divide-slate-100">
              {itens.map((item) => (
                <tr key={`${item.id}-${item.nome}`} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{item.nome}</div>
                    <div className="text-xs text-slate-500">{item.quantidade} conta(s)</div>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-900">
                    <div>{formatarMoeda(item.total_aberto)}</div>
                    <button
                      type="button"
                      className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:text-blue-900"
                      onClick={() => onDetalhes({ ...item, grupo, grupo_id: item.id })}
                    >
                      <FileSearch className="h-3.5 w-3.5" />
                      Detalhes
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
