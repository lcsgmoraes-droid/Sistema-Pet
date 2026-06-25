import { Search } from "lucide-react";

import { formatMoneyBRL } from "../../utils/formatters";
import { formatarDataHora } from "./centralNFSaidaUtils";

export default function SefazConsultasSessao({
  consultasSessao,
  listaConsultasRef,
  consultaExpandidaId,
  setConsultaExpandidaId,
}) {
  if (!consultasSessao.length) return null;

  return (
    <div ref={listaConsultasRef} className="mb-6">
      <h2 className="text-sm font-bold text-gray-700 mb-2 flex items-center gap-2">
        <Search className="w-4 h-4 text-purple-500" />
        Consultas da sessão ({consultasSessao.length})
      </h2>
      <div className="space-y-2">
        {consultasSessao.map((consulta) => {
          const expandida = consultaExpandidaId === consulta.id;
          const dados = consulta.dados;

          return (
            <div
              key={consulta.id}
              className="bg-white rounded-xl border border-purple-200 overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setConsultaExpandidaId(expandida ? null : consulta.id)}
                className="w-full text-left px-4 py-3 hover:bg-purple-50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-semibold text-gray-800">
                    NF {dados.numero_nf}/{dados.serie} — {dados.emitente_nome}
                  </div>
                  <div className="flex items-center gap-2">
                    {consulta.jaExiste && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                        ✓ Já está na listagem
                      </span>
                    )}
                    <span className="text-xs text-gray-500">
                      {formatarDataHora(consulta.criadoEm)}
                    </span>
                  </div>
                </div>
                <div className="mt-1 text-xs text-gray-500 flex gap-4">
                  <span>
                    Chave: <span className="font-mono">{dados.chave_acesso}</span>
                  </span>
                  <span>
                    Total:{" "}
                    <strong className="text-gray-800">
                      {formatMoneyBRL(dados.valor_total_nf)}
                    </strong>
                  </span>
                  <span className="text-purple-600">{expandida ? "Fechar" : "Expandir"}</span>
                </div>
              </button>
              {expandida && (
                <div className="border-t border-purple-100 p-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-500">Número/Série:</span>{" "}
                      <strong>
                        {dados.numero_nf}/{dados.serie}
                      </strong>
                    </div>
                    <div>
                      <span className="text-gray-500">Emissão:</span>{" "}
                      <strong>{dados.data_emissao}</strong>
                    </div>
                    <div>
                      <span className="text-gray-500">Emitente:</span>{" "}
                      <strong>{dados.emitente_nome}</strong>
                    </div>
                    <div>
                      <span className="text-gray-500">CNPJ Emitente:</span>{" "}
                      <strong>{dados.emitente_cnpj}</strong>
                    </div>
                    <div>
                      <span className="text-gray-500">Destinatário:</span>{" "}
                      <strong>{dados.destinatario_nome || "-"}</strong>
                    </div>
                    <div>
                      <span className="text-gray-500">Valor Total:</span>{" "}
                      <strong className="text-green-700">
                        {formatMoneyBRL(dados.valor_total_nf)}
                      </strong>
                    </div>
                  </div>
                  {dados.itens?.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="bg-gray-50 text-gray-600 uppercase">
                            <th className="text-left px-2 py-1">#</th>
                            <th className="text-left px-2 py-1">Descrição</th>
                            <th className="text-right px-2 py-1">Qtd</th>
                            <th className="text-right px-2 py-1">Unit.</th>
                            <th className="text-right px-2 py-1">Total</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {dados.itens.map((item) => (
                            <tr key={item.numero_item} className="hover:bg-gray-50">
                              <td className="px-2 py-1 text-gray-400">{item.numero_item}</td>
                              <td className="px-2 py-1">{item.descricao}</td>
                              <td className="px-2 py-1 text-right">{item.quantidade}</td>
                              <td className="px-2 py-1 text-right">
                                {formatMoneyBRL(item.valor_unitario)}
                              </td>
                              <td className="px-2 py-1 text-right font-semibold">
                                {formatMoneyBRL(item.valor_total)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
