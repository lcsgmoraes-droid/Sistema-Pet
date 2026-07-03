import { UNIDADES_COMPRA_OPCOES } from "./pedidoCompraUtils";

export default function PedidosCompraSugestaoUnidadeCell({
  sugestao,
  obterEmbalagemSugestao,
  atualizarUnidadeCompraSugestao,
  atualizarQuantidadePorEmbalagemSugestao,
  marcarQuantidadePorEmbalagemDesconhecida,
  formatarQuantidadeCompraSugestao,
  montarTooltipQuantidadeCompraSugestao,
}) {
  const embalagem = obterEmbalagemSugestao(sugestao);
  const usaEmbalagem = embalagem.unidade_compra !== "UN";

  return (
    <div className="flex flex-col gap-2">
      <select
        value={embalagem.unidade_compra}
        onChange={(e) => atualizarUnidadeCompraSugestao(sugestao, e.target.value)}
        className="h-9 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm font-semibold text-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
        title="Unidade usada para pedir ao fornecedor"
      >
        {UNIDADES_COMPRA_OPCOES.map((opcao) => (
          <option key={opcao.value} value={opcao.value}>
            {opcao.label}
          </option>
        ))}
      </select>

      {usaEmbalagem && (
        <div className="flex items-center gap-1">
          <input
            type="number"
            min="1"
            step="1"
            value={embalagem.quantidade_por_embalagem ?? ""}
            onChange={(e) => atualizarQuantidadePorEmbalagemSugestao(sugestao, e.target.value)}
            className="h-9 min-w-0 flex-1 rounded-lg border border-slate-300 px-2 text-right text-sm focus:border-purple-500 focus:ring-2 focus:ring-purple-200"
            placeholder="unid."
            title={`Unidades vendaveis por ${embalagem.unidade_compra}`}
          />
          <button
            type="button"
            onClick={() => marcarQuantidadePorEmbalagemDesconhecida(sugestao)}
            className="h-9 rounded-lg border border-slate-200 px-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-100"
            title="Nao sei quantas unidades vem na embalagem agora"
          >
            Nao sei
          </button>
        </div>
      )}

      <div
        className="text-right text-xs font-semibold text-slate-600"
        title={montarTooltipQuantidadeCompraSugestao(sugestao)}
      >
        {formatarQuantidadeCompraSugestao(sugestao)}
      </div>
    </div>
  );
}
