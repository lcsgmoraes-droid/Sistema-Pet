import { CalendarDays, CheckCircle2, SlidersHorizontal, WalletCards, X } from "lucide-react";
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
const comissaoPodeSerSelecionada = (comissao) => ["pendente", "fechada"].includes(comissao.status);

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
                        comissoes.filter(comissaoPodeSerSelecionada).length
                    }
                    onChange={toggleSelecionarTodas}
                    disabled={comissoes.filter(comissaoPodeSerSelecionada).length === 0}
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
                      disabled={!comissaoPodeSerSelecionada(comissao)}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      title={
                        !comissaoPodeSerSelecionada(comissao)
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

      {/* Resumo compacto, mantido visível sem criar uma faixa colorida sobre a tabela */}
      {comissoes.length > 0 && (
        <div className="fixed bottom-[5.25rem] left-4 right-4 z-40 md:bottom-4 md:left-[17rem] md:right-6">
          <div className="mx-auto max-w-7xl rounded-2xl border border-slate-200/90 bg-white/95 shadow-[0_14px_38px_rgba(15,23,42,0.14)] backdrop-blur">
            <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
              <div className="flex min-w-0 flex-wrap items-center gap-x-6 gap-y-2">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
                    <CalendarDays className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      Período
                    </div>
                    <div className="text-sm font-semibold text-slate-700">
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
                </div>

                <div className="flex min-w-0 items-center gap-2.5">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                    <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      Filtros
                    </div>
                    <div className="flex max-w-full flex-wrap gap-1 text-xs font-medium text-slate-600">
                      {funcionarioSelecionado && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5">
                          {funcionarioSelecionado.nome}
                        </span>
                      )}
                      {produtoSelecionado && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5">
                          {produtoSelecionado.nome}
                        </span>
                      )}
                      {grupoSelecionado && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5">
                          {grupoSelecionado.nome}
                        </span>
                      )}
                      {filtros.status && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5">
                          {filtros.status}
                        </span>
                      )}
                      {!funcionarioSelecionado &&
                        !produtoSelecionado &&
                        !grupoSelecionado &&
                        !filtros.status && (
                          <span className="text-slate-500">Sem filtros adicionais</span>
                        )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-3 rounded-xl border border-emerald-100 bg-emerald-50/80 px-4 py-2">
                <WalletCards className="h-5 w-5 text-emerald-600" aria-hidden="true" />
                <div className="text-right">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                    Total pendente
                  </div>
                  <MoneyCell
                    className="text-lg font-bold leading-tight text-slate-900"
                    value={calcularTotalFiltrado()}
                  />
                </div>
                <div className="border-l border-emerald-200 pl-3 text-xs font-medium text-slate-500">
                  {comissoes.filter(comissaoPodeSerSelecionada).length} comissão(ões) pendente(s)
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Espaçamento para o resumo flutuante */}
      {comissoes.length > 0 && <div className="h-24 md:h-20"></div>}
    </>
  );
}
