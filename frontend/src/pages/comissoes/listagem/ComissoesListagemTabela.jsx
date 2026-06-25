import { CheckCircle2, X } from "lucide-react";
import ActionButton from "../../../components/ui/ActionButton";
import CopyableCode from "../../../components/ui/CopyableCode";
import MoneyCell from "../../../components/ui/MoneyCell";
import NumberCell from "../../../components/ui/NumberCell";
import SaleReference from "../../../components/ui/SaleReference";
import StatusBadge from "../../../components/ui/StatusBadge";
import { formatarDataHoraComissao } from "../../../utils/comissoesDate";

function ComissaoTipoCalculoBadge({ tipo }) {
  const labels = {
    percentual: "Percentual",
    lucro: "Lucro",
  };

  return (
    <StatusBadge intent={tipo === "lucro" ? "purple" : "info"}>
      {labels[tipo] || tipo || "-"}
    </StatusBadge>
  );
}

const formatarData = (dataISO) => formatarDataHoraComissao(dataISO);

const renderizarStatus = (status) => <StatusBadge status={status} />;

const renderizarTipoCalculo = (tipo) => <ComissaoTipoCalculoBadge tipo={tipo} />;

export default function ComissoesListagemTabela({ controller }) {
  const {
    abrirDetalhe,
    abrirModalFechamento,
    calcularTotalFiltrado,
    comissoes,
    comissoesSelecionadas,
    filtros,
    funcionarioSelecionado,
    grupoSelecionado,
    loadingFechamento,
    produtoSelecionado,
    setComissoesSelecionadas,
    tipoFiltroData,
    toggleSelecaoComissao,
    toggleSelecionarTodas,
  } = controller;

  return (
    <>
      {/* Barra de Ações de Fechamento */}
      {comissoesSelecionadas.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-blue-600" aria-hidden="true" />
            <span className="text-blue-800 font-medium">
              {comissoesSelecionadas.length} comissão(ões) selecionada(s)
            </span>
          </div>
          <div className="flex gap-2">
            <ActionButton
              onClick={() => setComissoesSelecionadas([])}
              icon={X}
              intent="neutral"
              tone="soft"
            >
              Limpar Seleção
            </ActionButton>
            <ActionButton
              onClick={abrirModalFechamento}
              disabled={loadingFechamento}
              icon={CheckCircle2}
              intent="create"
              loading={loadingFechamento}
            >
              Fechar Comissões
            </ActionButton>
          </div>
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={
                      comissoesSelecionadas.length > 0 &&
                      comissoesSelecionadas.length ===
                        comissoes.filter((c) => c.status === "pendente").length
                    }
                    onChange={toggleSelecionarTodas}
                    disabled={comissoes.filter((c) => c.status === "pendente").length === 0}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                    title="Selecionar todas pendentes"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data da Venda
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Número da Venda
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Produto ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Parcela
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo de Cálculo
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Base de Cálculo
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  % Comissão
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Valor Comissão
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {comissoes.map((comissao) => (
                <tr key={comissao.id} className="hover:bg-blue-50 transition">
                  <td className="px-6 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={comissoesSelecionadas.includes(comissao.id)}
                      onChange={() => toggleSelecaoComissao(comissao.id, comissao.status)}
                      disabled={comissao.status !== "pendente"}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      title={
                        comissao.status !== "pendente"
                          ? `Comissão ${comissao.status}`
                          : "Selecionar para fechamento"
                      }
                    />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {formatarData(comissao.data_venda)}
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-medium cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                    title={`ID interno: #${comissao.venda_id}`}
                  >
                    <SaleReference
                      value={comissao.numero_venda || comissao.venda_id}
                      showPrefix={false}
                    />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <CopyableCode label="Produto" value={comissao.produto_id} />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {comissao.parcela_numero}
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {renderizarTipoCalculo(comissao.tipo_calculo)}
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-medium cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <MoneyCell value={comissao.valor_base_calculo} />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <NumberCell value={comissao.percentual_comissao} decimals={1} suffix="%" />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-bold cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <MoneyCell value={comissao.valor_comissao_gerada} />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {renderizarStatus(comissao.status)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rodapé informativo */}
      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>ℹ️ Informação:</strong> Os valores exibidos são snapshots imutáveis do momento da
          venda. Eles não são recalculados e refletem exatamente como a comissão foi gerada.
          <span className="ml-2 text-blue-600 font-medium">
            Clique em qualquer linha para ver mais detalhes.
          </span>
        </p>
      </div>

      {/* RODAPÉ FIXO COM RESUMO */}
      {comissoes.length > 0 && (
        <div className="fixed bottom-0 left-64 right-0 bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-600 text-white shadow-lg z-40 border-t border-indigo-300/30">
          <div className="max-w-7xl mx-auto px-8 py-3.5">
            <div className="flex items-center justify-between">
              {/* Período Selecionado */}
              <div className="flex items-center gap-8">
                <div>
                  <div className="text-[10px] font-semibold text-indigo-200 mb-0.5 tracking-wide uppercase">
                    📅 Período
                  </div>
                  <div className="text-sm font-bold text-white">
                    {tipoFiltroData === "ate_hoje" ? (
                      "Até hoje"
                    ) : (
                      <>
                        {filtros.data_inicio
                          ? new Date(filtros.data_inicio).toLocaleDateString("pt-BR")
                          : "Início"}
                        {" → "}
                        {filtros.data_fim
                          ? new Date(filtros.data_fim).toLocaleDateString("pt-BR")
                          : "Fim"}
                      </>
                    )}
                  </div>
                </div>

                {/* Filtros Ativos */}
                <div>
                  <div className="text-[10px] font-semibold text-indigo-200 mb-0.5 tracking-wide uppercase">
                    🔍 Filtros
                  </div>
                  <div className="text-sm font-bold text-white">
                    {funcionarioSelecionado && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        👤 {funcionarioSelecionado.nome}
                      </span>
                    )}
                    {produtoSelecionado && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        📦 {produtoSelecionado.nome}
                      </span>
                    )}
                    {grupoSelecionado && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        📂 {grupoSelecionado.nome}
                      </span>
                    )}
                    {filtros.status && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        ⚡ {filtros.status}
                      </span>
                    )}
                    {!funcionarioSelecionado &&
                      !produtoSelecionado &&
                      !grupoSelecionado &&
                      !filtros.status && <span className="text-indigo-200">Sem filtros</span>}
                  </div>
                </div>
              </div>

              {/* Total Calculado */}
              <div className="text-right">
                <div className="text-[10px] font-semibold text-indigo-200 mb-0.5 tracking-wide uppercase">
                  💰 Total Pendente (Filtrado)
                </div>
                <div className="text-3xl font-bold text-white drop-shadow-sm">
                  <MoneyCell value={calcularTotalFiltrado()} />
                </div>
                <div className="text-[11px] text-indigo-100 mt-0.5 font-medium">
                  {comissoes.filter((c) => c.status === "pendente").length} comissão(ões)
                  pendente(s)
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Espaçamento para o rodapé fixo */}
      {comissoes.length > 0 && <div className="h-24"></div>}
    </>
  );
}
