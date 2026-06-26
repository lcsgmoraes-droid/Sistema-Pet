import { formatarData, formatarMoeda } from "../../api/produtos";
import FornecedorIdentity from "../../components/ui/FornecedorIdentity";
import {
  formatarQuantidade,
  getDiasRestantesVisual,
  getFaixaCampanhaBadge,
  getStatusBadge,
} from "./produtosValidadeProximaFormatters";

export default function ProdutosValidadeTable({ controller }) {
  const { dados, loading } = controller;

  return (
    <div className="hidden overflow-x-auto md:block">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {[
              "Produto",
              "Lote",
              "Prazo / validade",
              "Quantidade",
              "Valor em risco",
              "Campanha automatica",
              "Acoes",
            ].map((titulo, index) => (
              <th
                key={titulo}
                className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500 ${
                  [3, 4, 6].includes(index) ? "text-right" : "text-left"
                }`}
              >
                {titulo}
              </th>
            ))}
          </tr>
        </thead>

        <tbody className="divide-y divide-gray-100 bg-white">
          {!loading && dados.items.length === 0 && (
            <tr>
              <td colSpan={7} className="px-5 py-10 text-center text-sm text-gray-500">
                Nenhum lote encontrado para os filtros aplicados.
              </td>
            </tr>
          )}

          {dados.items.map((item) => (
            <ProdutosValidadeTableRow key={item.lote_id} controller={controller} item={item} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProdutosValidadeTableRow({ controller, item }) {
  const statusBadge = getStatusBadge(item.status_validade);
  const faixaBadge = getFaixaCampanhaBadge(item.faixa_campanha);
  const diasRestantes = getDiasRestantesVisual(item.dias_para_vencer);
  const processandoCampanha = controller.acaoCampanhaLoteId === item.lote_id;

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-5 py-4 align-top">
        <div className="space-y-1">
          <div className="text-sm font-semibold text-gray-900">{item.nome}</div>
          <div className="text-xs text-gray-500">
            {item.codigo || item.sku || "Sem codigo"}
            {item.marca_nome ? ` - ${item.marca_nome}` : ""}
            {item.categoria_nome ? ` - ${item.categoria_nome}` : ""}
          </div>
          {item.fornecedor_nome && (
            <div className="text-xs text-gray-500">
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
      </td>

      <td className="px-5 py-4 align-top">
        <LoteCell item={item} />
      </td>
      <td className="px-5 py-4 align-top">
        <PrazoCell diasRestantes={diasRestantes} item={item} statusBadge={statusBadge} />
      </td>
      <td className="px-5 py-4 text-right align-top">
        <div className="text-sm font-semibold text-gray-900">
          {formatarQuantidade(item.quantidade_disponivel)}
        </div>
        <div className="text-xs text-gray-500">
          Custo unit.: {formatarMoeda(item.custo_unitario)}
        </div>
      </td>
      <td className="px-5 py-4 text-right align-top">
        <div className="text-sm font-semibold text-gray-900">
          {formatarMoeda(item.valor_custo_lote)}
        </div>
        <div className="text-xs text-gray-500">Venda: {formatarMoeda(item.valor_venda_lote)}</div>
      </td>
      <td className="px-5 py-4 align-top">
        <CampanhaStatus faixaBadge={faixaBadge} item={item} />
      </td>
      <td className="px-5 py-4 align-top">
        <div className="flex justify-end gap-2">
          <CampanhaAction
            item={item}
            onExcluir={controller.excluirDaCampanha}
            onReincluir={controller.reincluirNaCampanha}
            processandoCampanha={processandoCampanha}
          />
          <button
            type="button"
            onClick={() => controller.editarProduto(item)}
            className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={controller.irParaCampanhas}
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100"
          >
            Campanhas
          </button>
        </div>
      </td>
    </tr>
  );
}

function LoteCell({ item }) {
  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-gray-900">{item.nome_lote}</div>
      <div className="text-xs text-gray-500">
        Setor: {item.departamento_nome || "Nao informado"}
      </div>
      {item.campanha_validade_excluida ? (
        <span className="inline-flex rounded-full bg-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700">
          Fora da campanha
        </span>
      ) : item.campanha_validade_ativa ? (
        <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
          Na campanha
        </span>
      ) : item.promocao_ativa ? (
        <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
          Promocao ativa
        </span>
      ) : null}
    </div>
  );
}

function PrazoCell({ diasRestantes, item, statusBadge }) {
  return (
    <div className="space-y-2">
      <div
        className={`inline-flex min-w-[120px] flex-col rounded-2xl border px-3 py-2 ${diasRestantes.surfaceClassName}`}
      >
        <span className={`text-xl font-bold leading-tight ${diasRestantes.className}`}>
          {diasRestantes.destaque}
        </span>
        <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-600">
          {diasRestantes.apoio}
        </span>
      </div>
      <span
        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${statusBadge.className}`}
      >
        {statusBadge.label}
      </span>
      <div className="text-xs font-medium text-gray-700">
        Validade: {formatarData(item.data_validade)}
      </div>
    </div>
  );
}

function CampanhaStatus({ faixaBadge, item }) {
  if (item.campanha_validade_excluida) {
    return (
      <div className="space-y-2">
        <span className="inline-flex rounded-full bg-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700">
          Removido manualmente
        </span>
        <p className="max-w-xs text-xs text-gray-500">
          Esse lote foi tirado da campanha automatica, mas pode ser reincluido a qualquer momento.
        </p>
      </div>
    );
  }
  if (!item.campanha_validade_ativa) {
    return (
      <div className="space-y-2">
        <span
          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${faixaBadge.className}`}
        >
          {faixaBadge.label}
        </span>
        <p className="max-w-xs text-xs text-gray-500">
          {item.faixa_campanha
            ? "Lote elegivel para a campanha automatica quando a regra estiver ativa."
            : "Ainda fora da janela automatica sugerida."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
        {item.percentual_desconto_validade || 0}% OFF
      </span>
      <div className="space-y-1 text-xs text-gray-600">
        <p>
          {item.mensagem_promocional ||
            `Ate ${formatarQuantidade(item.quantidade_promocional)} unidade(s) por esse preco.`}
        </p>
        {item.preco_promocional_validade_app !== null &&
          item.preco_promocional_validade_app !== undefined && (
            <p>App: {formatarMoeda(item.preco_promocional_validade_app)}</p>
          )}
        {item.preco_promocional_validade_ecommerce !== null &&
          item.preco_promocional_validade_ecommerce !== undefined && (
            <p>Site: {formatarMoeda(item.preco_promocional_validade_ecommerce)}</p>
          )}
      </div>
    </div>
  );
}

function CampanhaAction({ item, onExcluir, onReincluir, processandoCampanha }) {
  if (item.campanha_validade_excluida) {
    return (
      <button
        type="button"
        disabled={processandoCampanha}
        onClick={() => onReincluir(item)}
        className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
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
      className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {processandoCampanha ? "Removendo..." : "Tirar da campanha"}
    </button>
  );
}
