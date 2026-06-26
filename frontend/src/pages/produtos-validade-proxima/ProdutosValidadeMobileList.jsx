import { formatarData, formatarMoeda } from "../../api/produtos";
import FornecedorIdentity from "../../components/ui/FornecedorIdentity";
import {
  formatarQuantidade,
  getDiasRestantesVisual,
  getFaixaCampanhaBadge,
  getStatusBadge,
} from "./produtosValidadeProximaFormatters";

export default function ProdutosValidadeMobileList({ controller }) {
  const { dados, loading } = controller;

  return (
    <div className="space-y-3 bg-gray-50 p-3 md:hidden">
      {loading ? (
        <div className="rounded-lg bg-white px-4 py-8 text-center text-sm text-gray-500">
          Atualizando dados...
        </div>
      ) : dados.items.length === 0 ? (
        <div className="rounded-lg bg-white px-4 py-8 text-center text-sm text-gray-500">
          Nenhum lote encontrado para os filtros aplicados.
        </div>
      ) : (
        dados.items.map((item) => (
          <ProdutoValidadeMobileCard key={item.lote_id} controller={controller} item={item} />
        ))
      )}
    </div>
  );
}

function ProdutoValidadeMobileCard({ controller, item }) {
  const statusBadge = getStatusBadge(item.status_validade);
  const faixaBadge = getFaixaCampanhaBadge(item.faixa_campanha);
  const diasRestantes = getDiasRestantesVisual(item.dias_para_vencer);
  const processandoCampanha = controller.acaoCampanhaLoteId === item.lote_id;

  return (
    <article className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="line-clamp-2 text-sm font-semibold text-gray-900">{item.nome}</h3>
          <p className="mt-1 text-xs text-gray-500">
            {item.codigo || item.sku || "Sem codigo"}
            {item.marca_nome ? ` - ${item.marca_nome}` : ""}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-medium ${statusBadge.className}`}
        >
          {statusBadge.label}
        </span>
      </div>

      <div className="mt-3 flex gap-2">
        <div className={`min-w-0 flex-1 rounded-lg border p-3 ${diasRestantes.surfaceClassName}`}>
          <p className={`text-xl font-bold leading-tight ${diasRestantes.className}`}>
            {diasRestantes.destaque}
          </p>
          <p className="text-[11px] font-semibold uppercase text-gray-600">{diasRestantes.apoio}</p>
          <p className="mt-1 text-xs font-medium text-gray-700">
            {formatarData(item.data_validade)}
          </p>
        </div>
        <div className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-gray-50 p-3">
          <p className="text-[11px] font-semibold uppercase text-gray-500">Quantidade</p>
          <p className="mt-1 text-lg font-bold text-gray-900">
            {formatarQuantidade(item.quantidade_disponivel)}
          </p>
          <p className="text-xs text-gray-500">Custo: {formatarMoeda(item.valor_custo_lote)}</p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-gray-900">Lote {item.nome_lote}</p>
            <p className="text-xs text-gray-500">{item.categoria_nome || "Sem categoria"}</p>
          </div>
          <CampanhaPill faixaBadge={faixaBadge} item={item} />
        </div>
        {item.fornecedor_nome && (
          <div className="mt-2 text-xs text-gray-500">
            <FornecedorIdentity
              fallback=""
              layout="inline"
              nameClassName="font-medium text-gray-600"
              record={item}
              showDocument={false}
              showLabel
            />
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <CampanhaAction
          item={item}
          processandoCampanha={processandoCampanha}
          onExcluir={controller.excluirDaCampanha}
          onReincluir={controller.reincluirNaCampanha}
        />
        <button
          type="button"
          onClick={() => controller.editarProduto(item)}
          className="flex-1 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700"
        >
          Editar
        </button>
      </div>
    </article>
  );
}

function CampanhaPill({ faixaBadge, item }) {
  if (item.campanha_validade_excluida) {
    return (
      <span className="rounded-full bg-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700">
        Fora da campanha
      </span>
    );
  }
  if (item.campanha_validade_ativa) {
    return (
      <span className="rounded-full bg-emerald-100 px-2 py-1 text-[11px] font-medium text-emerald-700">
        {item.percentual_desconto_validade || 0}% OFF
      </span>
    );
  }
  return (
    <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${faixaBadge.className}`}>
      {faixaBadge.label}
    </span>
  );
}

function CampanhaAction({ item, onExcluir, onReincluir, processandoCampanha }) {
  if (item.campanha_validade_excluida) {
    return (
      <button
        type="button"
        disabled={processandoCampanha}
        onClick={() => onReincluir(item)}
        className="flex-1 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {processandoCampanha ? "Reincluindo..." : "Reincluir"}
      </button>
    );
  }
  if (!item.faixa_campanha) return null;
  return (
    <button
      type="button"
      disabled={processandoCampanha}
      onClick={() => onExcluir(item)}
      className="flex-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {processandoCampanha ? "Removendo..." : "Tirar da campanha"}
    </button>
  );
}
