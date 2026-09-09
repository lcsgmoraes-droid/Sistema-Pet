import { formatMoneyBRL } from "../../utils/formatters";
import { formatarQuantidade } from "./transferenciaParceiroUtils";

export default function DevolucaoParceiroItens({ registro, formBaixa, setFormBaixa, resumo }) {
  const itens = registro.itens_devolucao || [];
  return (
    <div className="mt-4 rounded-2xl border border-sky-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="font-semibold text-sky-900">Produtos desta devolução</h4>
          <p className="mt-1 text-sm text-slate-600">
            Informe apenas o que está voltando agora. O restante fica para as próximas devoluções.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-lg border border-sky-200 px-3 py-2 text-sm text-sky-800"
            onClick={() =>
              setFormBaixa((prev) => ({
                ...prev,
                itens_devolucao: Object.fromEntries(
                  itens.map((item) => [item.produto_id, item.quantidade_disponivel]),
                ),
              }))
            }
          >
            Devolver todos os restantes
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700"
            onClick={() => setFormBaixa((prev) => ({ ...prev, itens_devolucao: {} }))}
          >
            Limpar
          </button>
        </div>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-sky-50 text-sky-900">
            <tr>
              <th className="p-3 text-left">Produto</th>
              <th className="p-3 text-right">Enviado</th>
              <th className="p-3 text-right">Já devolvido</th>
              <th className="p-3 text-right">Restante</th>
              <th className="p-3 text-right">Devolver agora</th>
              <th className="p-3 text-right">Valor da devolução</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {itens.map((item) => (
              <tr key={item.produto_id}>
                <td className="p-3 text-slate-900">
                  <p className="font-medium">{item.produto_nome}</p>
                  <p className="mt-1 text-xs text-slate-500">Código: {item.codigo || "-"}</p>
                </td>
                <td className="p-3 text-right">{formatarQuantidade(item.quantidade)}</td>
                <td className="p-3 text-right">{formatarQuantidade(item.quantidade_devolvida)}</td>
                <td className="p-3 text-right">{formatarQuantidade(item.quantidade_disponivel)}</td>
                <td className="p-3 text-right">
                  <input
                    type="number"
                    min="0"
                    max={item.quantidade_disponivel}
                    step="0.001"
                    aria-label={`Quantidade a devolver de ${item.produto_nome}`}
                    disabled={item.quantidade_disponivel <= 0}
                    value={formBaixa.itens_devolucao?.[item.produto_id] ?? ""}
                    placeholder="0"
                    onChange={(event) =>
                      setFormBaixa((prev) => ({
                        ...prev,
                        itens_devolucao: {
                          ...prev.itens_devolucao,
                          [item.produto_id]: event.target.value,
                        },
                      }))
                    }
                    className="w-28 rounded-lg border border-sky-200 bg-white px-3 py-2 text-right text-slate-900 disabled:bg-slate-100"
                  />
                </td>
                <td className="p-3 text-right font-semibold">
                  {formatMoneyBRL(
                    resumo.itens.find((selecionado) => selecionado.produto_id === item.produto_id)
                      ?.valor_total || 0,
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!itens.length && (
        <p className="mt-3 text-sm text-slate-600">Nenhum produto disponível para devolução.</p>
      )}
      {resumo.erro && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {resumo.erro}
        </p>
      )}
    </div>
  );
}
