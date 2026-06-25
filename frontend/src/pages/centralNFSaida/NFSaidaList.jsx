import { AlertCircle, Download, Eye, FileText, Printer, Trash2, XCircle, Zap } from "lucide-react";

import CustomerIdentity from "../../components/ui/CustomerIdentity";
import { formatMoneyBRL } from "../../utils/formatters";
import { formatarDataBR, getSituacaoCor, getSituacaoIcone } from "./centralNFSaidaUtils";

export default function NFSaidaList({
  erro,
  loading,
  notasFiltradas,
  busca,
  filtroSituacao,
  dataInicial,
  dataFinal,
  setModalCancelar,
  excluirNota,
  reconciliarFluxoNota,
  reconciliandoNotaId,
  baixarDanfe,
  baixarXml,
  abrirDetalhes,
}) {
  return (
    <>
      {erro && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-6 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {erro}
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto" />
          <p className="text-gray-600 mt-4">Carregando notas fiscais...</p>
        </div>
      ) : notasFiltradas.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Nenhuma nota encontrada</h3>
          <p className="text-gray-600">
            {busca || filtroSituacao || dataInicial || dataFinal
              ? "Tente ajustar os filtros"
              : "Emita sua primeira nota fiscal em uma venda"}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Número
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Data Emissão
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Cliente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Canal / Loja
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Situação
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Valor
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {notasFiltradas.map((nota) => (
                <tr key={nota.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{nota.numero}</div>
                    <div className="text-sm text-gray-500">Série {nota.serie}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatarDataBR(nota.data_emissao)}
                  </td>
                  <td className="px-6 py-4">
                    <CustomerIdentity
                      code={nota.cliente?.codigo || nota.cliente_id || nota.cliente?.id}
                      customer={nota.cliente}
                      nameClassName="font-medium text-gray-900"
                    />
                    <div className="text-sm text-gray-500">{nota.cliente?.cpf_cnpj || ""}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="space-y-1">
                      <div className="flex flex-wrap gap-2">
                        {nota.canal_label || nota.origem_loja_virtual || nota.origem_canal_venda ? (
                          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                            {nota.canal_label ||
                              nota.origem_loja_virtual ||
                              nota.origem_canal_venda}
                          </span>
                        ) : null}
                        {nota.loja?.nome ? (
                          <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                            {nota.loja.nome}
                          </span>
                        ) : null}
                      </div>
                      {nota.numero_pedido_loja ? (
                        <div className="text-xs text-gray-500">
                          Pedido loja: {nota.numero_pedido_loja}
                        </div>
                      ) : nota.origem_loja_virtual || nota.origem_canal_venda ? (
                        <div className="text-xs text-gray-500">
                          Origem: {nota.origem_loja_virtual || nota.origem_canal_venda}
                        </div>
                      ) : (
                        <div className="text-xs text-gray-400">Sem origem detalhada</div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getSituacaoCor(nota.status)}`}
                    >
                      {getSituacaoIcone(nota.status)}
                      {nota.status || "Pendente"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatMoneyBRL(nota.valor)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      {(nota.status?.toLowerCase() === "autorizada" ||
                        nota.status?.toLowerCase() === "emitida danfe") && (
                        <button
                          onClick={() => setModalCancelar(nota)}
                          className="text-red-600 hover:text-red-900 p-1 hover:bg-red-50 rounded"
                          title="Cancelar NF-e"
                        >
                          <XCircle className="w-5 h-5" />
                        </button>
                      )}
                      <button
                        onClick={() => excluirNota(nota.venda_id, nota.numero)}
                        className="text-gray-600 hover:text-gray-900 p-1 hover:bg-gray-50 rounded"
                        title="Excluir nota do sistema"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => reconciliarFluxoNota(nota)}
                        disabled={reconciliandoNotaId === String(nota.id)}
                        className="text-amber-600 hover:text-amber-900 p-1 hover:bg-amber-50 rounded disabled:opacity-50"
                        title="Forçar reconciliação desta NF"
                      >
                        <Zap className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => baixarDanfe(nota.id, nota.numero)}
                        className="text-blue-600 hover:text-blue-900 p-1 hover:bg-blue-50 rounded"
                        title="Baixar DANFE"
                      >
                        <Printer className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => baixarXml(nota.id, nota.numero)}
                        className="text-green-600 hover:text-green-900 p-1 hover:bg-green-50 rounded"
                        title="Baixar XML"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => abrirDetalhes(nota)}
                        className="text-gray-600 hover:text-gray-900 p-1 hover:bg-gray-50 rounded"
                        title="Ver Detalhes"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && notasFiltradas.length > 0 && (
        <div className="mt-4 text-sm text-gray-600 text-center">
          {notasFiltradas.length}{" "}
          {notasFiltradas.length === 1 ? "nota encontrada" : "notas encontradas"}
        </div>
      )}
    </>
  );
}
