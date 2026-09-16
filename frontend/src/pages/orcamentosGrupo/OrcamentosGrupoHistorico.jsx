import { useState } from "react";
import toast from "react-hot-toast";
import { Download, Eye, FileText } from "lucide-react";

import { baixarBlob, orcamentosGrupoApi } from "../../api/orcamentosGrupo";
import { formatMoneyBRL } from "../../utils/formatters";
import { nomeArquivoPdf } from "./orcamentosGrupoUtils";

function dataBr(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T12:00:00`));
}

export default function OrcamentosGrupoHistorico({ orcamentos }) {
  const [detalhe, setDetalhe] = useState(null);
  const [carregando, setCarregando] = useState(false);

  async function abrir(id) {
    setCarregando(true);
    try {
      const response = await orcamentosGrupoApi.detalharOrcamento(id);
      setDetalhe(response.data);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Não foi possível abrir o orçamento.");
    } finally {
      setCarregando(false);
    }
  }

  async function baixar(orcamento) {
    try {
      const response = await orcamentosGrupoApi.baixarPdf(orcamento.id);
      baixarBlob(response.data, nomeArquivoPdf(orcamento));
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Não foi possível baixar o PDF.");
    }
  }

  if (orcamentos.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-slate-950">
        <FileText className="mx-auto text-slate-300" size={38} />
        <p className="mt-3 font-medium text-slate-700 dark:text-slate-200">
          Nenhum orçamento emitido ainda.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">Orçamentos emitidos</h2>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {orcamentos.map((orcamento) => (
            <div
              key={orcamento.id}
              className="flex flex-wrap items-center justify-between gap-3 p-4"
            >
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {orcamento.numero}
                </p>
                <p className="text-xs text-slate-500">
                  {dataBr(orcamento.data_emissao)} · {orcamento.quantidade_cotacoes} documentos ·
                  Base {formatMoneyBRL(orcamento.total_base)}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => abrir(orcamento.id)}
                  disabled={carregando}
                  className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
                  aria-label="Ver orçamento"
                >
                  <Eye size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => baixar(orcamento)}
                  className="rounded-lg border border-blue-200 p-2 text-blue-700 hover:bg-blue-50 dark:border-blue-900 dark:text-blue-300"
                  aria-label="Baixar PDFs"
                >
                  <Download size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        {!detalhe ? (
          <div className="flex min-h-52 items-center justify-center text-center text-sm text-slate-500">
            Selecione um orçamento para conferir os valores salvos.
          </div>
        ) : (
          <div>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-bold text-slate-900 dark:text-slate-100">{detalhe.numero}</h2>
                <p className="text-xs text-slate-500">
                  {detalhe.destinatario || "Sem destinatário informado"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => baixar(detalhe)}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
              >
                <Download size={14} /> PDFs
              </button>
            </div>
            <div className="mt-4 space-y-2">
              {detalhe.cotacoes?.map((cotacao) => (
                <div
                  key={cotacao.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 p-3 dark:border-slate-800"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {cotacao.empresa?.nome}
                    </p>
                    <p className="text-xs text-slate-500">{cotacao.itens?.length || 0} item(ns)</p>
                  </div>
                  <p className="font-bold text-teal-700 dark:text-teal-300">
                    {formatMoneyBRL(cotacao.total)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
