import { obterCodigoPessoaPublico } from "../../utils/codigosPublicos";
import {
  AlertCircle,
  Copy,
  Download,
  Eye,
  FileText,
  Printer,
  RotateCcw,
  Trash2,
  Unlock,
  XCircle,
  Zap,
  Share2,
} from "lucide-react";

import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoMenuAcoes from "../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import { formatMoneyBRL } from "../../utils/formatters";
import { rejeicaoResponsavelTecnico } from "../../utils/fiscalRejectionGuidance.mjs";
import { obterPendenciaCancelamentoFiscal } from "../../utils/pdvFiscalStatus";
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
  clonarNota,
  excluirNota,
  reconciliarFluxoNota,
  reconciliandoNotaId,
  corrigirEReemitir,
  corrigindoNotaId,
  abrirCorrecao,
  diagnosticandoNotaId,
  liberarVendaComRejeicao,
  liberandoVendaId,
  baixarDanfe,
  baixarXml,
  abrirDetalhes,
  filtroCanal,
  pagina,
  setPagina,
  totalNotas,
  compartilharNota,
  documentoEmCurso,
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
            {busca || filtroSituacao || filtroCanal || dataInicial || dataFinal
              ? "Tente ajustar os filtros"
              : "Emita sua primeira nota fiscal em uma venda"}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm overflow-x-auto">
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
              {notasFiltradas.map((nota) => {
                const pendenciaFiscal = obterPendenciaCancelamentoFiscal({
                  ...nota,
                  status: nota.venda_status,
                  nfe_status: nota.status,
                });
                return (
                  <tr key={`${nota.id}:${nota.modelo}`} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{nota.numero}</div>
                      <div className="text-sm text-gray-500">Série {nota.serie}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatarDataBR(nota.data_emissao)}
                    </td>
                    <td className="px-6 py-4">
                      <CustomerIdentity
                        code={obterCodigoPessoaPublico(nota)}
                        customer={nota.cliente}
                        nameClassName="font-medium text-gray-900"
                      />
                      <div className="text-sm text-gray-500">{nota.cliente?.cpf_cnpj || ""}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        <div className="flex flex-wrap gap-2">
                          {nota.canal_label ||
                          nota.origem_loja_virtual ||
                          nota.origem_canal_venda ? (
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
                      {nota.provedor === "intnfe" && nota.status?.toLowerCase() === "rejeitada" ? (
                        <BotaoInteracao
                          tamanho="pequeno"
                          onClick={() => abrirCorrecao(nota)}
                          disabled={diagnosticandoNotaId === String(nota.venda_id)}
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium underline disabled:opacity-50 ${getSituacaoCor(nota.status)}`}
                          title={
                            rejeicaoResponsavelTecnico({
                              codigo: nota.codigo_erro,
                              motivo: nota.motivo_rejeicao,
                            })
                              ? "Ver orientação de suporte"
                              : "Abrir a correção desta rejeição"
                          }
                        >
                          {getSituacaoIcone(nota.status)} {nota.status} ·{" "}
                          {rejeicaoResponsavelTecnico({
                            codigo: nota.codigo_erro,
                            motivo: nota.motivo_rejeicao,
                          })
                            ? "Falar com suporte"
                            : "Corrigir erro"}
                        </BotaoInteracao>
                      ) : (
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getSituacaoCor(nota.status)}`}
                        >
                          {getSituacaoIcone(nota.status)} {nota.status || "Pendente"}
                        </span>
                      )}
                      {pendenciaFiscal && (
                        <div className="mt-2 max-w-xs whitespace-normal text-xs text-amber-900 dark:text-amber-200">
                          <div className="font-semibold">{pendenciaFiscal.label}</div>
                          {pendenciaFiscal.detalhe && (
                            <div className="mt-1">{pendenciaFiscal.detalhe}</div>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatMoneyBRL(nota.valor)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex justify-end">
                        <BotaoMenuAcoes
                          rotulo={`Ações da nota ${nota.numero || "sem número"}`}
                          acoes={[
                            { icon: Copy, label: "Clonar nota", onClick: () => clonarNota(nota) },
                            ["autorizada", "emitida danfe"].includes(
                              nota.status?.toLowerCase(),
                            ) && {
                              icon: XCircle,
                              label: "Cancelar NF-e",
                              tom: "perigo",
                              onClick: () => setModalCancelar(nota),
                            },
                            nota.provedor !== "intnfe" && {
                              icon: Trash2,
                              label: "Excluir nota do sistema",
                              tom: "perigo",
                              onClick: () => excluirNota(nota.venda_id, nota.numero),
                            },
                            nota.provedor === "intnfe" &&
                              nota.status?.toLowerCase() === "rejeitada" &&
                              !rejeicaoResponsavelTecnico({
                                codigo: nota.codigo_erro,
                                motivo: nota.motivo_rejeicao,
                              }) && {
                                icon: Unlock,
                                label: "Escolher outro modelo de nota",
                                disabled: liberandoVendaId === String(nota.venda_id),
                                onClick: () => liberarVendaComRejeicao(nota),
                              },
                            nota.provedor === "intnfe" &&
                              nota.status?.toLowerCase() === "rejeitada" &&
                              !rejeicaoResponsavelTecnico({
                                codigo: nota.codigo_erro,
                                motivo: nota.motivo_rejeicao,
                              }) && {
                                icon: RotateCcw,
                                label: `Tentar novamente como ${Number(nota.modelo) === 55 ? "NF-e" : "NFC-e"}`,
                                disabled: corrigindoNotaId === String(nota.venda_id),
                                onClick: () => corrigirEReemitir(nota),
                              },
                            {
                              icon: Zap,
                              label: "Atualizar situação da NF",
                              disabled: reconciliandoNotaId === String(nota.id),
                              onClick: () => reconciliarFluxoNota(nota),
                            },
                            {
                              icon: Printer,
                              label: "Baixar DANFE",
                              disabled:
                                documentoEmCurso === String(nota.venda_id || nota.id) ||
                                (nota.provedor === "intnfe" &&
                                  nota.status?.toLowerCase() !== "autorizada"),
                              onClick: () => baixarDanfe(nota),
                            },
                            {
                              icon: Download,
                              label: "Baixar XML",
                              disabled:
                                documentoEmCurso === String(nota.venda_id || nota.id) ||
                                (nota.provedor === "intnfe" &&
                                  nota.status?.toLowerCase() !== "autorizada"),
                              onClick: () => baixarXml(nota),
                            },
                            nota.status?.toLowerCase() === "autorizada" && {
                              icon: Share2,
                              label: "Compartilhar nota",
                              onClick: () => compartilharNota(nota),
                            },
                            {
                              icon: Eye,
                              label: "Ver detalhes",
                              onClick: () => abrirDetalhes(nota),
                            },
                          ]}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!loading && totalNotas > 0 && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-gray-600">
          <span>
            {totalNotas} notas encontradas · Página {pagina} de{" "}
            {Math.max(1, Math.ceil(totalNotas / 50))}
          </span>
          <div className="flex gap-2">
            <BotaoInteracao
              tamanho="pequeno"
              disabled={pagina <= 1}
              onClick={() => setPagina(pagina - 1)}
              className="border rounded px-3 py-2 disabled:opacity-40"
            >
              Anterior
            </BotaoInteracao>
            <BotaoInteracao
              tamanho="pequeno"
              disabled={pagina * 50 >= totalNotas}
              onClick={() => setPagina(pagina + 1)}
              className="border rounded px-3 py-2 disabled:opacity-40"
            >
              Próxima
            </BotaoInteracao>
          </div>
        </div>
      )}
    </>
  );
}
