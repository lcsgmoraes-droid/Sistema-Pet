import { formatBRL, formatMoneyBRL } from "../../utils/formatters";

export default function FiscalCorrectionNoteContext({ nota, detalheNota, produtos }) {
  if (!nota) return null;
  const detalhe = detalheNota || {};
  const cliente = detalhe.cliente || nota.cliente || {};
  const itens = detalhe.itens || [];
  const afetados = new Set(produtos.map((produto) => Number(produto.itemNumero)).filter(Boolean));
  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/60">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-900 dark:text-slate-100">
            {Number(nota.modelo) === 55 || nota.tipo === "nfe" ? "NF-e" : "NFC-e"}{" "}
            {nota.numero || "sem número"} · Série {nota.serie || "—"}
          </p>
          <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">
            {cliente.nome || "Consumidor não identificado"}
          </p>
          {cliente.cpf_cnpj && (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{cliente.cpf_cnpj}</p>
          )}
        </div>
        <div className="text-sm text-slate-700 dark:text-slate-200">
          <p className="font-semibold">
            {formatMoneyBRL(detalhe.totais?.valor_total ?? nota.valor ?? 0)}
          </p>
          <p className="mt-1">{itens.length ? `${itens.length} itens` : "Itens indisponíveis"}</p>
        </div>
      </div>
      {itens.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm font-semibold text-slate-700 dark:text-slate-200">
            Conferir todos os itens da nota
            {afetados.size
              ? ` · ${afetados.size === 1 ? "item destacado" : "itens destacados"}: ${[...afetados].join(", ")}`
              : ""}
          </summary>
          <div className="mt-3 max-h-64 overflow-auto rounded-lg border border-slate-200 dark:border-slate-700">
            <table className="min-w-full text-xs">
              <thead className="bg-white text-left text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                <tr>
                  <th className="px-3 py-2">Item / Produto</th>
                  <th className="px-3 py-2">SKU</th>
                  <th className="px-3 py-2">NCM</th>
                  <th className="px-3 py-2 text-right">Qtd.</th>
                  <th className="px-3 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {itens.map((item, index) => {
                  const numero = Number(item.item_numero || index + 1);
                  const afetado = afetados.has(numero);
                  return (
                    <tr
                      key={item.item_id || numero}
                      className={
                        afetado
                          ? "bg-red-50 text-red-900 dark:bg-red-950/30 dark:text-red-200"
                          : "text-slate-700 dark:text-slate-200"
                      }
                    >
                      <td className="px-3 py-2">
                        {numero} · {item.descricao || "—"}
                        {afetado && <span className="ml-2 font-semibold">Revisar</span>}
                      </td>
                      <td className="px-3 py-2">{item.codigo || "—"}</td>
                      <td className="px-3 py-2">{item.ncm || "—"}</td>
                      <td className="px-3 py-2 text-right">{formatBRL(item.quantidade || 0)}</td>
                      <td className="px-3 py-2 text-right">
                        {formatMoneyBRL(item.valor_total ?? item.preco_total ?? 0)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </section>
  );
}
